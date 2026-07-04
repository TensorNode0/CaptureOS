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


async def generate(engine, anthropic_key, openai_key, system, user,
                   max_tokens=8000, web_search=False):
    """Route to the requested engine ('claude' default, or 'openai')."""
    if engine == "openai":
        if not openai_key:
            raise ValueError("No OpenAI API key set. Add it in Settings → API Keys.")
        return await openai_generate(openai_key, system, user, max_tokens)
    if not anthropic_key:
        raise ValueError("No Anthropic API key set. Add it in Settings → API Keys.")
    return await claude_generate(anthropic_key, system, user, max_tokens, web_search)
