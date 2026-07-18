"""Shared LLM engine layer: Anthropic, OpenAI, Emergent, AskSage.

All keys are passed in by the caller (decrypted from org secrets at call time)
and are never logged or persisted in source.

Every generate call returns (text, model_used, usage) where usage is
{"inputTokens": int, "outputTokens": int} (zeros when a provider doesn't
report usage). Callers meter cost with price_for()/cost_usd().
"""
import json
import re
import asyncio

import httpx

# Newest first; we fall back until one is accepted by the caller's key.
CLAUDE_MODELS = ["claude-sonnet-5", "claude-sonnet-4-5", "claude-3-5-sonnet-latest"]
OPENAI_MODELS = ["gpt-5", "gpt-4.1", "gpt-4o"]
EMERGENT_MODELS = ["claude-sonnet-4-6", "gpt-5.4", "gpt-4o"]

# User-selectable catalogs per engine (shown in the model dropdown).
MODEL_CATALOG = {
    "claude": [
        {"id": "claude-sonnet-5", "label": "Claude Sonnet 5 (recommended)"},
        {"id": "claude-opus-4-8", "label": "Claude Opus 4.8 (deepest, priciest)"},
        {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (fastest, cheapest)"},
        {"id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5"},
    ],
    "openai": [
        {"id": "gpt-5", "label": "GPT-5 (recommended)"},
        {"id": "gpt-4.1", "label": "GPT-4.1"},
        {"id": "gpt-4o", "label": "GPT-4o"},
        {"id": "gpt-4o-mini", "label": "GPT-4o mini (cheapest)"},
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (recommended)"},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (most capable)"},
        {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash-Lite (cheapest)"},
    ],
    "emergent": [
        {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 via Emergent (recommended)"},
        {"id": "gpt-5.4", "label": "GPT-5.4 via Emergent"},
        {"id": "gpt-4o", "label": "GPT-4o via Emergent"},
        {"id": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro via Emergent"},
    ],
    "asksage": [
        {"id": "aws-bedrock-claude-45-sonnet", "label": "Claude Sonnet (GovCloud/Bedrock)"},
        {"id": "gpt-4o", "label": "GPT-4o via AskSage"},
        {"id": "google-gemini-pro", "label": "Gemini Pro via AskSage"},
    ],
}

# Effort → output-token budget multiplier (base budgets set per feature).
EFFORTS = {"low": 0.5, "standard": 1.0, "high": 1.6}

# $ per 1M tokens (input, output) — published API prices; matched by substring.
# AskSage bills subscription tokens, not per-call dollars → metered as 0 with a note.
PRICES = [
    ("claude-opus", 15.0, 75.0),
    ("claude-sonnet", 3.0, 15.0),
    ("claude-haiku", 1.0, 5.0),
    ("claude-3-5-sonnet", 3.0, 15.0),
    ("gpt-5", 1.25, 10.0),
    ("gpt-4.1", 2.0, 8.0),
    ("gpt-4o-mini", 0.15, 0.6),
    ("gpt-4o", 2.5, 10.0),
]

ENGINE_LABELS = {"claude": "Anthropic", "openai": "OpenAI",
                 "gemini": "Gemini", "emergent": "Emergent", "asksage": "AskSage"}

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


def price_for(model: str):
    m = (model or "").lower()
    for needle, pin, pout in PRICES:
        if needle in m:
            return pin, pout
    return 0.0, 0.0


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = price_for(model)
    return round((input_tokens or 0) * pin / 1e6 + (output_tokens or 0) * pout / 1e6, 6)


def scaled_tokens(base: int, effort: str) -> int:
    return min(16000, max(1000, int(base * EFFORTS.get(effort or "standard", 1.0))))


def _close_stack(prefix: str):
    """Closers needed to balance `prefix`, and whether it ends inside a string."""
    stack, in_str, esc = [], False, False
    for ch in prefix:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    return "".join(reversed(stack)), in_str


def repair_json(raw: str):
    """Best-effort parse of truncated model JSON: closes open strings/brackets,
    dropping trailing incomplete elements until the document parses."""
    end = len(raw)
    for _ in range(120):
        prefix = raw[:end].rstrip()
        closers, in_str = _close_stack(prefix)
        if in_str:
            prefix += '"'
        prefix = re.sub(r'[,\s]*("(?:[^"\\]|\\.)*"\s*:)?\s*$', "", prefix)
        closers, _ = _close_stack(prefix)
        try:
            return json.loads(prefix + closers)
        except Exception:
            pass
        cut = raw.rfind(",", 0, end - 1)
        if cut <= 0:
            return None
        end = cut
    return None


def extract_json(text: str):
    """Pull the first JSON object out of a model response. Handles code fences
    and salvages truncated/incomplete output via best-effort repair."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        start = text.find("{")
        if start == -1:
            return None
        end = text.rfind("}")
        raw = text[start:end + 1] if end > start else text[start:]
    try:
        return json.loads(raw)
    except Exception:
        return repair_json(raw)


def _usage(input_tokens, output_tokens):
    return {"inputTokens": int(input_tokens or 0), "outputTokens": int(output_tokens or 0)}


def _anthropic_call_sync(api_key, system, user, max_tokens=8000, web_search=False,
                         model="", max_uses=5, models=None):
    """Blocking Anthropic call. Continues paused web-search turns until the
    response is complete; usage includes stopReason/webSearches telemetry.
    Returns (text, model_used, usage)."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    tools = [dict(WEB_SEARCH_TOOL, max_uses=max_uses)] if web_search else []
    pool = models or CLAUDE_MODELS
    models_try = [model] + [m for m in pool if m != model] if model else pool
    last_err = None
    for m in models_try:
        try:
            messages = [{"role": "user", "content": user}]
            text, in_tok, out_tok, searches, stop = "", 0, 0, 0, None
            for _ in range(6):
                msg = client.messages.create(
                    model=m, max_tokens=max_tokens, system=system, tools=tools,
                    messages=messages,
                )
                text += "".join(getattr(b, "text", "") for b in msg.content
                                if getattr(b, "type", None) == "text")
                u = getattr(msg, "usage", None)
                in_tok += getattr(u, "input_tokens", 0) or 0
                out_tok += getattr(u, "output_tokens", 0) or 0
                st = getattr(u, "server_tool_use", None)
                searches += (getattr(st, "web_search_requests", 0) or 0) if st else 0
                stop = getattr(msg, "stop_reason", None)
                if stop != "pause_turn":
                    break
                messages = messages + [{"role": "assistant", "content": msg.content}]
            usage = _usage(in_tok, out_tok)
            usage["stopReason"] = stop
            usage["webSearches"] = searches
            return text, m, usage
        except (anthropic.NotFoundError, anthropic.BadRequestError) as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Anthropic call failed")


def anthropic_json_salvage_sync(api_key, prior_user, prior_text, max_tokens, models):
    """One no-tools follow-up asking the model to re-emit ONLY the JSON when its
    first answer buried or omitted the object."""
    user = (prior_user + "\n\nYOUR PREVIOUS RESPONSE:\n" + prior_text[:60000] +
            "\n\nOutput ONLY the single JSON object described above — no prose, "
            "no apologies, no markdown fences. If data is missing use \"TBD\".")
    return _anthropic_call_sync(api_key, "You return only valid JSON.", user,
                                max_tokens, False, "", 0, models)


async def claude_generate(api_key, system, user, max_tokens=8000, web_search=False, model=""):
    return await asyncio.to_thread(
        _anthropic_call_sync, api_key, system, user, max_tokens, web_search, model)


async def openai_generate(api_key, system, user, max_tokens=8000, model=""):
    """OpenAI chat completion via plain HTTPS. Returns (text, model_used, usage)."""
    models = [model] + [m for m in OPENAI_MODELS if m != model] if model else OPENAI_MODELS
    last_err = None
    async with httpx.AsyncClient(timeout=180) as client:
        for m in models:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": m, "max_completion_tokens": max_tokens,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}]},
            )
            if r.status_code == 401:
                raise PermissionError("OpenAI rejected the API key (401)")
            if r.status_code == 429:
                raise RuntimeError(
                    "OpenAI returned 429 (rate/quota limit) — the key is valid but the "
                    "OpenAI account is rate-limited or out of quota. Check "
                    "platform.openai.com → Billing / Usage limits.")
            if r.status_code in (400, 404):
                last_err = RuntimeError(f"OpenAI {m}: {r.text[:300]}")
                continue
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            u = data.get("usage") or {}
            return text, m, _usage(u.get("prompt_tokens"), u.get("completion_tokens"))
    raise last_err if last_err else RuntimeError("OpenAI call failed")


GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]


def _gemini_call_sync(api_key, system, user, max_tokens, model):
    """Sync Gemini call — google-genai's Client is synchronous. We run it in a
    thread from the async wrapper so the FastAPI event loop stays free."""
    from google import genai as g
    from google.genai import types, errors
    client = g.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(
            model=model or "gemini-2.5-flash",
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=0.2,
            ),
        )
    except errors.ClientError as e:
        code = getattr(e, "code", 0)
        if code in (401, 403):
            raise PermissionError(f"Gemini rejected the API key ({code})") from e
        if code == 429:
            raise RuntimeError("Gemini returned 429 (rate/quota limit). Check "
                               "ai.google.dev / your Google Cloud billing.") from e
        raise RuntimeError(f"Gemini client error: {getattr(e, 'message', str(e))[:300]}") from e
    except errors.ServerError as e:
        raise RuntimeError(f"Gemini server error: {getattr(e, 'message', str(e))[:300]}") from e
    text = resp.text or ""
    u = getattr(resp, "usage_metadata", None)
    prompt_tok = getattr(u, "prompt_token_count", None) if u else None
    out_tok = getattr(u, "candidates_token_count", None) if u else None
    used_model = getattr(resp, "model_version", model) or model or "gemini-2.5-flash"
    return text, used_model, _usage(prompt_tok, out_tok)


async def gemini_generate(api_key, system, user, max_tokens=8000, model=""):
    """Google Gemini text generation. Returns (text, model_used, usage)."""
    import asyncio
    return await asyncio.to_thread(
        _gemini_call_sync, api_key, system, user, max_tokens, model)


async def asksage_generate(api_key, system, user, max_tokens=8000, model=""):
    """AskSage query API (GovCon-focused platform). Returns (text, model, usage)."""
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            "https://api.asksage.ai/server/query",
            headers={"x-access-tokens": api_key},
            json={"message": user, "persona": "default", "system_prompt": system,
                  "model": model or "aws-bedrock-claude-45-sonnet", "temperature": 0.2,
                  "limit_references": 0},
        )
        if r.status_code in (401, 403):
            raise PermissionError("AskSage rejected the API key (401/403)")
        r.raise_for_status()
        data = r.json()
    text = data.get("message") or data.get("response") or ""
    if not text:
        raise RuntimeError(f"AskSage returned no content: {str(data)[:200]}")
    return text, f"asksage/{model or 'claude-sonnet'}", _usage(data.get("prompt_tokens"),
                                                               data.get("completion_tokens"))


async def emergent_generate(api_key, system, user, max_tokens=8000, model=""):
    """Emergent universal LLM key via the emergentintegrations proxy library."""
    import uuid
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    models = [model] + [m for m in EMERGENT_MODELS if m != model] if model else EMERGENT_MODELS
    last_err = None
    for m in models:
        provider = ("anthropic" if m.startswith("claude")
                    else "gemini" if m.startswith("gemini") else "openai")
        try:
            chat = LlmChat(api_key=api_key, session_id=f"captureagent-{uuid.uuid4()}",
                           system_message=system).with_model(provider, m)
            resp = await chat.send_message(UserMessage(text=user))
            text = str(resp or "")
            if not text.strip():
                raise RuntimeError("empty response")
            return text, f"emergent/{m}", _usage(0, 0)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            low = msg.lower()
            if "401" in msg or "unauthorized" in low or "authentication" in low \
                    or "invalid api key" in low:
                raise PermissionError(
                    "Emergent rejected the API key (401). Check the key in "
                    "Settings → API Keys and its remaining balance.")
            last_err = RuntimeError(f"Emergent {m}: {msg[:300]}")
    raise last_err if last_err else RuntimeError("Emergent call failed")


async def generate(engine, keys, system, user, max_tokens=8000, web_search=False,
                   model="", effort=""):
    """Route to the requested engine. `keys` = org_keys.get_keys() dict.
    Returns (text, model_used, usage)."""
    engine = engine if engine in ENGINE_LABELS else "claude"
    max_tokens = scaled_tokens(max_tokens, effort) if effort else max_tokens
    if engine != "claude":
        key = keys.get(engine, "")
        if not key:
            raise ValueError(f"No {ENGINE_LABELS[engine]} API key set. "
                             "Add it in Settings → API Keys.")
        if engine == "openai":
            return await openai_generate(key, system, user, max_tokens, model)
        if engine == "gemini":
            return await gemini_generate(key, system, user, max_tokens, model)
        if engine == "asksage":
            return await asksage_generate(key, system, user, max_tokens, model)
        return await emergent_generate(key, system, user, max_tokens, model)
    if not keys.get("anthropic"):
        raise ValueError("No Anthropic API key set. Add it in Settings → API Keys.")
    return await claude_generate(keys["anthropic"], system, user, max_tokens,
                                 web_search, model)
