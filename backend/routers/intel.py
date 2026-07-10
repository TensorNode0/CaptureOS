"""AI Opportunity Intelligence — scan jobs, saved reports, push-to-pipeline."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database as db
from utils import now_utc, serialize, as_uuid, iso
from rbac import require_role
from domain import (write_audit, default_fit, default_compliance,
                    default_budget, default_criteria)
import intel
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["intelligence"])


class ScanIn(BaseModel):
    tier: str = "standard"


async def _build_ctx(org_id):
    org = await db.fetchrow("select * from organizations where id = $1", org_id) or {}
    prof = await db.fetchrow("select * from org_profiles where organization_id = $1",
                             org_id) or {}
    return {
        "orgName": org.get("name", ""),
        "naics": org.get("naics") or [],
        "keywords": org.get("keywords") or [],
        "capabilities": prof.get("capabilities", ""),
        "pastPerformance": prof.get("past_performance", ""),
        "techFocus": prof.get("tech_focus") or [],
        "differentiators": prof.get("differentiators", ""),
        "commercialization": prof.get("commercialization", ""),
        "clearances": prof.get("clearances", ""),
        "targetAgencies": prof.get("target_agencies") or [],
        "cmmcLevel": prof.get("cmmc_level", ""),
        "isSmall": prof.get("is_small", True),
        "certs": prof.get("certs") or {},
    }


async def _execute_scan(job_id, org_id, api_key, ctx, tier, user):
    await db.execute("update intel_jobs set status = 'running' where id = $1", job_id)
    try:
        report = await intel.run_scan(api_key, ctx, tier)
        rep = await db.fetchrow(
            """insert into intel_reports
                   (organization_id, created_by, tier, model, usage, report)
               values ($1, $2, $3, $4, $5, $6) returning id""",
            org_id, as_uuid(user["id"]), tier, report.get("_model", ""),
            report.get("_usage", {}) or {}, report)
        total = len((report.get("opportunities") or []))
        await db.execute(
            """update intel_jobs
               set status = 'done', finished_at = $2, report_id = $3,
                   summary = $4, model = $5
               where id = $1""",
            job_id, now_utc(), rep["id"], f"{total} opportunities found",
            report.get("_model", ""))
        await write_audit(org_id, user, "intel.scan", "weekly report",
                          {"total": total, "model": report.get("_model", ""),
                           "usage": report.get("_usage", {})})
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            msg = "Anthropic rejected the API key. Update it in Settings → API Keys."
        await db.execute(
            "update intel_jobs set status = 'error', finished_at = $2, error = $3 where id = $1",
            job_id, now_utc(), msg)


@router.post("/{orgId}/intel/scan")
async def start_scan(body: ScanIn, ctx: dict = Depends(require_role("editor"))):
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="intel.scan")
    api_key = keys["anthropic"]
    if not api_key:
        raise HTTPException(status_code=400,
            detail="No Anthropic API key set. Add it in Settings → API Keys.")
    tier = body.tier if body.tier in intel.TIERS else "standard"
    scan_ctx = await _build_ctx(ctx["org_id"])
    job = await db.fetchrow(
        """insert into intel_jobs (organization_id, status, tier, started_by)
           values ($1, 'queued', $2, $3) returning id""",
        ctx["org_id"], tier, as_uuid(ctx["user"]["id"]))
    asyncio.create_task(
        _execute_scan(job["id"], ctx["org_id"], api_key, scan_ctx, tier, ctx["user"]))
    return {"ok": True, "jobId": str(job["id"]), "status": "queued", "tier": tier}


@router.get("/{orgId}/intel/jobs/{jobId}")
async def job_status(jobId: str, ctx: dict = Depends(require_role("viewer"))):
    jid = as_uuid(jobId)
    j = await db.fetchrow(
        "select * from intel_jobs where id = $1 and organization_id = $2",
        jid, ctx["org_id"]) if jid else None
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize(j)


@router.get("/{orgId}/intel/reports")
async def list_reports(ctx: dict = Depends(require_role("viewer"))):
    reports = await db.fetch(
        """select * from intel_reports where organization_id = $1
           order by created_at desc limit 50""",
        ctx["org_id"])
    out = []
    for r in reports:
        rep = r.get("report") or {}
        out.append({
            "id": str(r["id"]),
            "createdAt": iso(r.get("created_at")),
            "tier": r.get("tier"),
            "model": r.get("model"),
            "total": len(rep.get("opportunities") or []),
            "reportDate": rep.get("reportDate"),
        })
    return out


@router.get("/{orgId}/intel/reports/{reportId}")
async def get_report(reportId: str, ctx: dict = Depends(require_role("viewer"))):
    rid = as_uuid(reportId)
    r = await db.fetchrow(
        "select * from intel_reports where id = $1 and organization_id = $2",
        rid, ctx["org_id"]) if rid else None
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize(r)


@router.delete("/{orgId}/intel/reports/{reportId}")
async def delete_report(reportId: str, ctx: dict = Depends(require_role("editor"))):
    rid = as_uuid(reportId)
    r = await db.fetchrow(
        "select id from intel_reports where id = $1 and organization_id = $2",
        rid, ctx["org_id"]) if rid else None
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.execute("delete from intel_reports where id = $1", r["id"])
    return {"ok": True}


@router.post("/{orgId}/intel/reports/{reportId}/add/{idx}")
async def add_to_pipeline(reportId: str, idx: int, ctx: dict = Depends(require_role("editor"))):
    rid = as_uuid(reportId)
    r = await db.fetchrow(
        "select * from intel_reports where id = $1 and organization_id = $2",
        rid, ctx["org_id"]) if rid else None
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    opps = ((r.get("report") or {}).get("opportunities") or [])
    if idx < 0 or idx >= len(opps):
        raise HTTPException(status_code=404, detail="Opportunity not found in report")
    o = opps[idx]
    sol = (o.get("solNumber") or "").strip()
    if sol and sol != "TBD":
        dup = await db.fetchrow(
            "select id from opportunities where organization_id = $1 and sol_number = $2",
            ctx["org_id"], sol)
        if dup:
            raise HTTPException(status_code=400, detail="Already in your pipeline")
    ceiling = o.get("awardAmount")
    try:
        ceiling = float(ceiling) if ceiling not in (None, "", "TBD") else 0
    except (ValueError, TypeError):
        ceiling = 0
    url = o.get("solUrl") or o.get("topicUrl") or ""
    due = o.get("dueDate")
    due = due if (due and due != "TBD") else None
    links = [{"label": "Solicitation", "url": url, "status": "live",
              "checkedAt": iso(now_utc())}]
    opp = await db.fetchrow(
        """insert into opportunities
               (organization_id, title, sol_number, agency, office, vehicle, set_aside,
                naics, ceiling, pop, due_date, stage, url, win_themes, source,
                last_verified, links, fit, compliance, budget, criteria, created_by)
           values ($1, $2, $3, $4, $5, $6, $7, '', $8, '', $9, 'Identified', $10, '',
                   'intel', $11, $12, $13, $14, $15, $16, $17)
           returning id""",
        ctx["org_id"], o.get("title", ""), sol if sol != "TBD" else "",
        o.get("agency", ""), o.get("office", ""), o.get("vehicle", "RFP") or "RFP",
        o.get("setAside") or "None", ceiling, due, url, now_utc(), links,
        default_fit(), default_compliance(), default_budget(ceiling),
        default_criteria(), as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "intel.add_to_pipeline", o.get("title"))
    return {"ok": True, "id": str(opp["id"])}
