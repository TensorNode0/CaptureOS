"""AI plumbing endpoints: engine/model/effort options, job polling, cancel."""
from fastapi import APIRouter, Depends, HTTPException

import database as db
from utils import serialize, as_uuid
from rbac import require_role
import ai_jobs
import genai
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["ai"])


@router.get("/{orgId}/ai/options")
async def ai_options(ctx: dict = Depends(require_role("viewer"))):
    """What the AI buttons can offer this org: configured engines, model
    catalogs, efforts, and month-to-date metered spend."""
    row = await db.fetchrow(
        "select * from org_secrets where organization_id = $1", ctx["org_id"])
    configured = []
    if row:
        for name, col in org_keys.KEY_COLUMNS.items():
            if name != "sam" and row.get(col):
                configured.append(name)
    engine_key = {"claude": "anthropic"}
    return {
        "engines": [{"id": e, "label": genai.ENGINE_LABELS[e],
                     "configured": engine_key.get(e, e) in configured,
                     "models": genai.MODEL_CATALOG.get(e, [])}
                    for e in ("claude", "openai", "emergent", "asksage")],
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
