"""Competitive analysis: OSINT + USASpending competitor reports with AI BLUF."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

import database as db
from utils import now_utc, serialize, as_uuid
from rbac import require_role
from domain import write_audit
import competitive
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["competitive"])


class AnalyzeIn(BaseModel):
    competitor: str = Field(min_length=2, max_length=200)
    naics: str = Field(default="", max_length=10)


async def _run(report_id, anthropic_key, competitor, naics, org_name, org_naics,
               user, org_id):
    try:
        usasp, analysis, model = await competitive.run_analysis(
            anthropic_key, competitor, naics, org_name, org_naics)
        note = "" if anthropic_key else \
            "USASpending data only — add an Anthropic API key in Settings for the AI BLUF."
        await db.execute(
            """update competitive_reports
               set status = 'done', usaspending = $2, analysis = $3, model = $4,
                   error = $5, finished_at = $6 where id = $1""",
            report_id, usasp, analysis, model, note, now_utc())
        await write_audit(org_id, user, "competitive.analyze", competitor,
                          {"awards": usasp.get("awardCount"), "model": model})
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        await db.execute(
            """update competitive_reports
               set status = 'error', error = $2, finished_at = $3 where id = $1""",
            report_id, msg[:900], now_utc())


@router.post("/{orgId}/competitive")
async def start_analysis(body: AnalyzeIn, ctx: dict = Depends(require_role("editor"))):
    competitor = body.competitor.strip()
    naics = body.naics.strip()
    if naics and not naics.isdigit():
        raise HTTPException(status_code=400, detail="NAICS must be numeric")
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="competitive.analyze")
    report = await db.fetchrow(
        """insert into competitive_reports (organization_id, competitor, naics,
                                            status, created_by)
           values ($1, $2, $3, 'running', $4) returning *""",
        ctx["org_id"], competitor, naics, as_uuid(ctx["user"]["id"]))
    asyncio.create_task(_run(
        report["id"], keys.get("anthropic", ""), competitor, naics,
        ctx["org"]["name"], ctx["org"].get("naics") or [],
        ctx["user"], ctx["org_id"]))
    return {"ok": True, "reportId": str(report["id"]), "status": "running"}


@router.get("/{orgId}/competitive")
async def list_reports(ctx: dict = Depends(require_role("viewer"))):
    rows = await db.fetch(
        """select id, competitor, naics, status, error, model, created_at, finished_at,
                  (usaspending->>'totalObligated') as total_obligated,
                  (usaspending->>'awardCount') as award_count
           from competitive_reports where organization_id = $1
           order by created_at desc limit 50""",
        ctx["org_id"])
    return [serialize(r) for r in rows]


@router.get("/{orgId}/competitive/{reportId}")
async def get_report(reportId: str, ctx: dict = Depends(require_role("viewer"))):
    rid = as_uuid(reportId)
    r = await db.fetchrow(
        "select * from competitive_reports where id = $1 and organization_id = $2",
        rid, ctx["org_id"]) if rid else None
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize(r)


@router.delete("/{orgId}/competitive/{reportId}")
async def delete_report(reportId: str, ctx: dict = Depends(require_role("editor"))):
    rid = as_uuid(reportId)
    r = await db.fetchrow(
        "select id, competitor from competitive_reports where id = $1 and organization_id = $2",
        rid, ctx["org_id"]) if rid else None
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.execute("delete from competitive_reports where id = $1", r["id"])
    await write_audit(ctx["org_id"], ctx["user"], "competitive.delete", r["competitor"])
    return {"ok": True}
