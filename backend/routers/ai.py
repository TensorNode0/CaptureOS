"""AI plumbing endpoints: engine/model/effort options, job polling, cancel, chat."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal

import database as db
from utils import serialize, as_uuid
from rbac import require_role
from domain import write_audit
import ai_jobs
import genai
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["ai"])

# Only these secrets represent AI engines the /ai/options endpoint should
# advertise — SAM (federal data pull) and Overleaf (git sync) are integrations,
# not chat engines, so they never appear in the AI button dropdowns.
_NON_ENGINE_KEYS = {"sam", "overleaf"}


@router.get("/{orgId}/ai/options")
async def ai_options(ctx: dict = Depends(require_role("viewer"))):
    """What the AI buttons can offer this org: configured engines, model
    catalogs, efforts, and month-to-date metered spend."""
    row = await db.fetchrow(
        "select * from org_secrets where organization_id = $1", ctx["org_id"])
    configured = []
    if row:
        for name, col in org_keys.KEY_COLUMNS.items():
            if name not in _NON_ENGINE_KEYS and row.get(col):
                configured.append(name)
    engine_key = {"claude": "anthropic"}
    return {
        "engines": [{"id": e, "label": genai.ENGINE_LABELS[e],
                     "configured": engine_key.get(e, e) in configured,
                     "models": genai.MODEL_CATALOG.get(e, [])}
                    for e in ("claude", "openai", "gemini", "emergent", "asksage")],
        "efforts": [{"id": "low", "label": "Low — fast & cheap"},
                    {"id": "standard", "label": "Standard"},
                    {"id": "high", "label": "High — deepest"}],
        "monthSpendUsd": await ai_jobs.month_spend(ctx["org_id"]),
        "spendNote": ("Metered from real token usage at provider list prices. "
                      "Providers don't expose account balances via API; AskSage and "
                      "the Emergent proxy don't report per-call usage (shown as $0)."),
    }


@router.get("/{orgId}/ai/jobs/{jobId}")
async def get_job(jobId: str, ctx: dict = Depends(require_role("viewer"))):
    jid = as_uuid(jobId)
    j = await db.fetchrow(
        "select * from ai_jobs where id = $1 and organization_id = $2",
        jid, ctx["org_id"]) if jid else None
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    out = serialize(j)
    out["costUsd"] = float(j["cost_usd"] or 0)
    out["monthSpendUsd"] = await ai_jobs.month_spend(ctx["org_id"])
    return out


@router.post("/{orgId}/ai/jobs/{jobId}/cancel")
async def cancel_job(jobId: str, ctx: dict = Depends(require_role("editor"))):
    jid = as_uuid(jobId)
    j = await db.fetchrow(
        "select id, status from ai_jobs where id = $1 and organization_id = $2",
        jid, ctx["org_id"]) if jid else None
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["status"] not in ("queued", "running"):
        return {"ok": True, "status": j["status"]}
    await db.execute("update ai_jobs set cancel_requested = true where id = $1", jid)
    return {"ok": True, "status": "cancelling"}



# ---------------- Chat drawer: AI assist over any workspace document ----------------
AI_ENGINES = {"claude": "anthropic", "openai": "openai", "gemini": "gemini",
              "emergent": "emergent", "asksage": "asksage"}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=32000)


class ChatIn(BaseModel):
    """Request body for a single turn in the workspace chat drawer.

    The client keeps message history in memory and re-sends the full
    conversation each turn — server is stateless. `contextText` is the
    document snapshot the chat is about (proposal volume, opportunity brief,
    accelerator application, etc.) so the model can reason over what the user
    sees, not just what they type."""
    engine: Literal["claude", "openai", "gemini", "emergent", "asksage"] = "claude"
    model: str = ""
    contextTitle: str = Field(default="", max_length=200)
    contextText: str = Field(default="", max_length=60000)
    messages: List[ChatMessage] = Field(default_factory=list, max_length=40)


CHAT_SYSTEM = (
    "You are the CaptureAgent in-app assistant helping a U.S. GovCon/venture "
    "capture professional review, redraft, and improve a document they are "
    "currently viewing. The document (if any) is shown after the CONTEXT: "
    "header. Ground every answer in that document; if the user asks for a "
    "rewrite, produce the rewritten passage in a fenced markdown block. Never "
    "fabricate agency names, PoCs, dollar figures, dates, or contract vehicles."
)


@router.post("/{orgId}/ai/chat")
async def ai_chat(body: ChatIn, ctx: dict = Depends(require_role("viewer"))):
    """Single-turn chat. Client re-sends full history each call (stateless).
    Uses the org's configured API key for the chosen engine — no Emergent
    fallback so metering stays honest per org."""
    if not body.messages or body.messages[-1].role != "user":
        raise HTTPException(status_code=400,
            detail="messages must end with a user turn.")
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="ai.chat")
    engine_key = AI_ENGINES.get(body.engine, "anthropic")
    if not keys.get(engine_key):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[body.engine]} API key set. "
                   "Add it in Settings → API Keys.")
    # Merge context + history into a single user prompt so we don't need
    # engine-specific multi-turn adapters. This keeps behavior consistent
    # across Anthropic/OpenAI/Gemini/Emergent/AskSage.
    ctx_block = ""
    if body.contextText.strip():
        title = body.contextTitle.strip() or "the current document"
        ctx_block = (f"CONTEXT — {title}:\n\"\"\"\n{body.contextText.strip()[:60000]}\n\"\"\"\n\n")
    convo = "\n\n".join(
        f"USER: {m.content}" if m.role == "user" else f"ASSISTANT: {m.content}"
        for m in body.messages)
    user_prompt = f"{ctx_block}CONVERSATION:\n{convo}\n\nASSISTANT:"
    try:
        text, used_model, _usage = await genai.generate(
            body.engine, keys, CHAT_SYSTEM, user_prompt,
            max_tokens=4000, model=body.model)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        label = genai.ENGINE_LABELS[body.engine]
        if "authentication" in msg.lower() or "401" in msg or "invalid" in msg.lower():
            raise HTTPException(status_code=400,
                detail=f"{label} rejected the API key. Update it in Settings.")
        raise HTTPException(status_code=502, detail=f"{label} chat failed: {msg[:300]}")
    await write_audit(ctx["org_id"], ctx["user"], "ai.chat",
                      body.contextTitle or "chat",
                      {"engine": body.engine, "model": used_model,
                       "turns": len(body.messages)})
    return {"reply": text, "model": used_model}
