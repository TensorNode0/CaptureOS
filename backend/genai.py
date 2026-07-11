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
EMERGENT_MODELS = ["claude-sonnet-5", "gpt-5", "gpt-4o"]

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
    "emergent": [
        {"id": "claude-sonnet-5", "label": "Claude Sonnet 5 via Emergent"},
        {"id": "gpt-5", "label": "GPT-5 via Emergent"},
        {"id": "gpt-4o", "label": "GPT-4o via Emergent"},
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
                 "emergent": "Emergent", "asksage": "AskSage"}

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


def extract_json(text: str):
    """Pull the first JSON object out of a model response (handles code fences)."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = text[start:end + 1]
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _usage(input_tokens, output_tokens):
    return {"inputTokens": int(input_tokens or 0), "outputTokens": int(output_tokens or 0)}


def _anthropic_call_sync(api_key, system, user, max_tokens=8000, web_search=False, model=""):
    """Blocking Anthropic call. Returns (text, model_used, usage)."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    tools = [WEB_SEARCH_TOOL] if web_search else []
    models = [model] + [m for m in CLAUDE_MODELS if m != model] if model else CLAUDE_MODELS
    last_err = None
    for m in models:
        try:
            msg = client.messages.create(
                model=m, max_tokens=max_tokens, system=system, tools=tools,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(getattr(b, "text", "") for b in msg.content
                           if getattr(b, "type", None) == "text")
            u = getattr(msg, "usage", None)
            return text, m, _usage(getattr(u, "input_tokens", 0),
                                   getattr(u, "output_tokens", 0))
        except (anthropic.NotFoundError, anthropic.BadRequestError) as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Anthropic call failed")


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
            if r.status_code in (400, 404):
                last_err = RuntimeError(f"OpenAI {m}: {r.text[:300]}")
                continue
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            u = data.get("usage") or {}
            return text, m, _usage(u.get("prompt_tokens"), u.get("completion_tokens"))
    raise last_err if last_err else RuntimeError("OpenAI call failed")


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
    """Emergent universal LLM key (OpenAI-compatible endpoint)."""
    models = [model] + [m for m in EMERGENT_MODELS if m != model] if model else EMERGENT_MODELS
    last_err = None
    async with httpx.AsyncClient(timeout=180) as client:
        for m in models:
            r = await client.post(
                "https://llm.emergentagent.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": m, "max_tokens": max_tokens,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}]},
            )
            if r.status_code == 401:
                raise PermissionError("Emergent rejected the API key (401)")
            if r.status_code in (400, 404, 422):
                last_err = RuntimeError(f"Emergent {m}: {r.text[:300]}")
                continue
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            u = data.get("usage") or {}
            return text, f"emergent/{m}", _usage(u.get("prompt_tokens"),
                                                 u.get("completion_tokens"))
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
        if engine == "asksage":
            return await asksage_generate(key, system, user, max_tokens, model)
        return await emergent_generate(key, system, user, max_tokens, model)
    if not keys.get("anthropic"):
        raise ValueError("No Anthropic API key set. Add it in Settings → API Keys.")
    return await claude_generate(keys["anthropic"], system, user, max_tokens,
                                 web_search, model)
