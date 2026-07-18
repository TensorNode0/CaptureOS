"""Competitive analysis: OSINT + USASpending competitor reports with AI BLUF."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

import database as db
from utils import now_utc, serialize, as_uuid
from rbac import require_role
from domain import write_audit
import genai
import competitive
import ai_jobs
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["competitive"])


class AnalyzeIn(BaseModel):
    engine: str = "claude"
    competitor: str = Field(min_length=2, max_length=200)
    naics: str = Field(default="", max_length=10)
    model: str = ""
    effort: str = "standard"


AI_ENGINES = {"claude": "anthropic", "openai": "openai",
              "emergent": "emergent", "asksage": "asksage"}


async def _run(report_id, engine, keys, competitor, naics, org_name, org_naics,
               user, org_id, model="", effort="", job_id=None):
    try:
        usasp, analysis, used_model = await competitive.run_analysis(
            engine, keys, competitor, naics, org_name, org_naics,
            model=model, effort=effort, job_id=job_id)
        note = "" if keys.get(AI_ENGINES[engine]) else \
            "USASpending data only — add an AI key in Settings for the AI BLUF."
        await db.execute(
            """update competitive_reports
               set status = 'done', usaspending = $2, analysis = $3, model = $4,
                   error = $5, finished_at = $6 where id = $1""",
            report_id, usasp, analysis, used_model, note, now_utc())
        if job_id:
            await ai_jobs.finish(job_id, "Report ready")
        await write_audit(org_id, user, "competitive.analyze", competitor,
                          {"awards": usasp.get("awardCount"), "model": used_model})
    except ai_jobs.JobCancelled:
        await db.execute(
            """update competitive_reports
               set status = 'error', error = 'Cancelled by user', finished_at = $2
               where id = $1""", report_id, now_utc())
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        if job_id:
            await ai_jobs.fail(job_id, msg)
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
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "competitive.analyze",
                                  ref_id=str(report["id"]),
                                  engine=body.engine if body.engine in AI_ENGINES else "claude",
                                  model=body.model, effort=body.effort)
    asyncio.create_task(_run(
        report["id"], body.engine if body.engine in AI_ENGINES else "claude",
        keys, competitor, naics,
        ctx["org"]["name"], ctx["org"].get("naics") or [],
        ctx["user"], ctx["org_id"], model=body.model, effort=body.effort,
        job_id=job_id))
    return {"ok": True, "reportId": str(report["id"]), "status": "running",
            "jobId": str(job_id)}


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


@router.get("/{orgId}/competitive/market/naics")
async def market_default(ctx: dict = Depends(require_role("viewer"))):
    """Top primes and subs in the org's own NAICS codes (keyless, verified)."""
    naics = ctx["org"].get("naics") or []
    try:
        return await competitive.fetch_market(naics)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502,
            detail=f"USASpending market lookup failed: {str(e)[:200]}")


class ShortlistIn(BaseModel):
    engine: str = "claude"
    model: str = ""
    effort: str = "standard"


@router.post("/{orgId}/competitive/market/shortlist")
async def shortlist_direct_competitors(body: ShortlistIn = None,
                                       ctx: dict = Depends(require_role("editor"))):
    """AI-shortlist likely direct competitors from the org's NAICS pool.
    Unlike the raw market list (top recipients by dollars), this filters to
    companies with substantive capability overlap with the org's profile."""
    body = body or ShortlistIn()
    engine = body.engine if body.engine in AI_ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"],
                                   purpose="competitive.shortlist")
    if not keys.get(AI_ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    prof = await db.fetchrow(
        "select capabilities, tech_focus from org_profiles where organization_id = $1",
        ctx["org_id"])
    capabilities = (prof or {}).get("capabilities", "") if prof else ""
    tech_focus = (prof or {}).get("tech_focus", "") if prof else ""
    try:
        result = await competitive.shortlist_competitors(
            engine, keys, ctx["org"]["name"], ctx["org"].get("naics") or [],
            capabilities, tech_focus, model=body.model, effort=body.effort)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower():
            raise HTTPException(status_code=400,
                detail="The AI provider rejected the API key. Update it in Settings → API Keys.")
        raise HTTPException(status_code=502,
            detail=f"Competitor shortlist failed: {msg[:300]}")
    await write_audit(ctx["org_id"], ctx["user"], "competitive.shortlist",
                      "market", {"picks": len(result.get("shortlist", []))})
    return result
