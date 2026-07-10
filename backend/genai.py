"""Shared LLM engine layer: Anthropic (primary) + OpenAI (optional).

All keys are passed in by the caller (decrypted from org secrets at call time)
and are never logged or persisted in source.
"""
import json
import re
import asyncio

import httpx

# Newest first; the SDK passes strings through, so we fall back until one is
# accepted by the caller's key.
CLAUDE_MODELS = [
    "claude-sonnet-5",
    "claude-sonnet-4-5",
    "claude-3-5-sonnet-latest",
]
OPENAI_MODELS = ["gpt-5", "gpt-4.1", "gpt-4o"]

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


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


def _anthropic_call_sync(api_key, system, user, max_tokens=8000, web_search=False):
    """Blocking Anthropic call. Returns (text, model_used)."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    tools = [WEB_SEARCH_TOOL] if web_search else []
    last_err = None
    for model in CLAUDE_MODELS:
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=tools,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(
                getattr(b, "text", "") for b in msg.content
                if getattr(b, "type", None) == "text"
            )
            return text, model
        except (anthropic.NotFoundError, anthropic.BadRequestError) as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Anthropic call failed")


async def claude_generate(api_key, system, user, max_tokens=8000, web_search=False):
    return await asyncio.to_thread(
        _anthropic_call_sync, api_key, system, user, max_tokens, web_search)


async def openai_generate(api_key, system, user, max_tokens=8000):
    """OpenAI chat completion via plain HTTPS. Returns (text, model_used)."""
    last_err = None
    async with httpx.AsyncClient(timeout=180) as client:
        for model in OPENAI_MODELS:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "max_completion_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            if r.status_code == 401:
                raise PermissionError("OpenAI rejected the API key (401)")
            if r.status_code in (400, 404):
                last_err = RuntimeError(f"OpenAI {model}: {r.text[:300]}")
                continue
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return text, model
    raise last_err if last_err else RuntimeError("OpenAI call failed")


async def asksage_generate(api_key, system, user, max_tokens=8000):
    """AskSage query API (GovCon-focused platform). Returns (text, model_used)."""
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            "https://api.asksage.ai/server/query",
            headers={"x-access-tokens": api_key},
            json={"message": user, "persona": "default", "system_prompt": system,
                  "model": "aws-bedrock-claude-45-sonnet", "temperature": 0.2,
                  "limit_references": 0},
        )
        if r.status_code in (401, 403):
            raise PermissionError("AskSage rejected the API key (401/403)")
        r.raise_for_status()
        data = r.json()
    text = data.get("message") or data.get("response") or ""
    if not text:
        raise RuntimeError(f"AskSage returned no content: {str(data)[:200]}")
    return text, "asksage"


EMERGENT_MODELS = ["claude-sonnet-5", "gpt-5", "gpt-4o"]


async def emergent_generate(api_key, system, user, max_tokens=8000):
    """Emergent universal LLM key (OpenAI-compatible endpoint). Returns (text, model)."""
    last_err = None
    async with httpx.AsyncClient(timeout=180) as client:
        for model in EMERGENT_MODELS:
            r = await client.post(
                "https://llm.emergentagent.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            if r.status_code == 401:
                raise PermissionError("Emergent rejected the API key (401)")
            if r.status_code in (400, 404, 422):
                last_err = RuntimeError(f"Emergent {model}: {r.text[:300]}")
                continue
            r.raise_for_status()
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return text, f"emergent/{model}"
    raise last_err if last_err else RuntimeError("Emergent call failed")


ENGINE_LABELS = {"claude": "Anthropic", "openai": "OpenAI",
                 "emergent": "Emergent", "asksage": "AskSage"}


async def generate(engine, keys, system, user, max_tokens=8000, web_search=False):
    """Route to the requested engine. `keys` is the org_keys.get_keys() dict."""
    engine = engine if engine in ENGINE_LABELS else "claude"
    if engine != "claude":
        key = keys.get(engine, "")
        if not key:
            raise ValueError(f"No {ENGINE_LABELS[engine]} API key set. "
                             "Add it in Settings → API Keys.")
        if engine == "openai":
            return await openai_generate(key, system, user, max_tokens)
        if engine == "asksage":
            return await asksage_generate(key, system, user, max_tokens)
        return await emergent_generate(key, system, user, max_tokens)
    if not keys.get("anthropic"):
        raise ValueError("No Anthropic API key set. Add it in Settings → API Keys.")
    return await claude_generate(keys["anthropic"], system, user, max_tokens, web_search)
