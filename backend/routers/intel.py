"""AI Opportunity Intelligence — scan jobs, saved reports, push-to-pipeline."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from bson import ObjectId

from database import db
from utils import now_utc, serialize, oid, iso
from rbac import require_role
from domain import (write_audit, decrypt_secret, default_fit, default_compliance,
                    default_budget, default_criteria)
import intel

router = APIRouter(prefix="/api/orgs", tags=["intelligence"])


class ScanIn(BaseModel):
    tier: str = "standard"


async def _build_ctx(org_oid):
    org = await db.organizations.find_one({"_id": org_oid}) or {}
    prof = await db.orgProfile.find_one({"organizationId": org_oid}) or {}
    return {
        "orgName": org.get("name", ""),
        "naics": org.get("naics", []),
        "keywords": org.get("keywords", []),
        "capabilities": prof.get("capabilities", ""),
        "pastPerformance": prof.get("pastPerformance", ""),
        "techFocus": prof.get("techFocus", []),
        "differentiators": prof.get("differentiators", ""),
        "commercialization": prof.get("commercialization", ""),
        "clearances": prof.get("clearances", ""),
        "cmmcLevel": prof.get("cmmcLevel", ""),
        "isSmall": prof.get("isSmall", True),
        "certs": prof.get("certs", {}),
    }


async def _execute_scan(job_id, org_oid, api_key, ctx, tier, user):
    await db.intelJobs.update_one({"_id": job_id},
                                  {"$set": {"status": "running"}})
    try:
        report = await intel.run_scan(api_key, ctx, tier)
        rdoc = {
            "organizationId": org_oid,
            "createdBy": ObjectId(user["id"]),
            "createdAt": now_utc(),
            "tier": tier,
            "model": report.get("_model", ""),
            "usage": report.get("_usage", {}),
            "report": report,
        }
        res = await db.intelReports.insert_one(rdoc)
        total = len((report.get("opportunities") or []))
        await db.intelJobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "done", "finishedAt": now_utc(),
                      "reportId": res.inserted_id,
                      "summary": f"{total} opportunities found",
                      "model": report.get("_model", "")}})
        await write_audit(org_oid, user, "intel.scan", "weekly report",
                          {"total": total, "model": report.get("_model", ""),
                           "usage": report.get("_usage", {})})
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            msg = "Anthropic rejected the API key. Update it in Settings → API Keys."
        await db.intelJobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "error", "finishedAt": now_utc(), "error": msg}})


@router.post("/{orgId}/intel/scan")
async def start_scan(body: ScanIn, ctx: dict = Depends(require_role("editor"))):
    rec = await db.secrets.find_one({"organizationId": ctx["org_oid"]}) or {}
    api_key = decrypt_secret(rec.get("anthropicKey", ""))
    if not api_key:
        raise HTTPException(status_code=400,
            detail="No Anthropic API key set. Add it in Settings → API Keys.")
    tier = body.tier if body.tier in intel.TIERS else "standard"
    scan_ctx = await _build_ctx(ctx["org_oid"])
    job = await db.intelJobs.insert_one({
        "organizationId": ctx["org_oid"], "status": "queued", "tier": tier,
        "startedBy": ObjectId(ctx["user"]["id"]), "startedAt": now_utc(),
    })
    asyncio.create_task(
        _execute_scan(job.inserted_id, ctx["org_oid"], api_key, scan_ctx, tier, ctx["user"]))
    return {"ok": True, "jobId": str(job.inserted_id), "status": "queued", "tier": tier}


@router.get("/{orgId}/intel/jobs/{jobId}")
async def job_status(jobId: str, ctx: dict = Depends(require_role("viewer"))):
    j = await db.intelJobs.find_one({"_id": oid(jobId), "organizationId": ctx["org_oid"]})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize(j)


@router.get("/{orgId}/intel/reports")
async def list_reports(ctx: dict = Depends(require_role("viewer"))):
    reports = await db.intelReports.find({"organizationId": ctx["org_oid"]}) \
        .sort("createdAt", -1).limit(50).to_list(50)
    out = []
    for r in reports:
        rep = r.get("report", {})
        out.append({
            "id": str(r["_id"]),
            "createdAt": iso(r.get("createdAt")),
            "tier": r.get("tier"),
            "model": r.get("model"),
            "total": len(rep.get("opportunities") or []),
            "reportDate": rep.get("reportDate"),
        })
    return out


@router.get("/{orgId}/intel/reports/{reportId}")
async def get_report(reportId: str, ctx: dict = Depends(require_role("viewer"))):
    r = await db.intelReports.find_one({"_id": oid(reportId), "organizationId": ctx["org_oid"]})
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize(r)


@router.delete("/{orgId}/intel/reports/{reportId}")
async def delete_report(reportId: str, ctx: dict = Depends(require_role("editor"))):
    r = await db.intelReports.find_one({"_id": oid(reportId), "organizationId": ctx["org_oid"]})
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.intelReports.delete_one({"_id": r["_id"]})
    return {"ok": True}


@router.post("/{orgId}/intel/reports/{reportId}/add/{idx}")
async def add_to_pipeline(reportId: str, idx: int, ctx: dict = Depends(require_role("editor"))):
    r = await db.intelReports.find_one({"_id": oid(reportId), "organizationId": ctx["org_oid"]})
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    opps = (r.get("report", {}).get("opportunities") or [])
    if idx < 0 or idx >= len(opps):
        raise HTTPException(status_code=404, detail="Opportunity not found in report")
    o = opps[idx]
    sol = (o.get("solNumber") or "").strip()
    if sol and sol != "TBD":
        dup = await db.opportunities.find_one(
            {"organizationId": ctx["org_oid"], "solNumber": sol})
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
    doc = {
        "organizationId": ctx["org_oid"],
        "title": o.get("title", ""), "solNumber": sol if sol != "TBD" else "",
        "agency": o.get("agency", ""), "office": o.get("office", ""),
        "vehicle": o.get("vehicle", "RFP") or "RFP",
        "setAside": o.get("setAside") or "None", "naics": "",
        "ceiling": ceiling, "pop": "", "dueDate": due, "stage": "Identified",
        "url": url, "winThemes": "", "source": "intel",
        "lastVerified": now_utc(), "verifyReport": None,
        "links": [{"label": "Solicitation", "url": url, "status": "live",
                   "checkedAt": iso(now_utc())}],
        "fit": default_fit(), "pwin": 0, "proposalStrength": 0,
        "compliance": default_compliance(), "budget": default_budget(ceiling),
        "criteria": default_criteria(), "decision": {"call": "TBD", "rationale": ""},
        "createdBy": ObjectId(ctx["user"]["id"]),
        "createdAt": now_utc(), "updatedAt": now_utc(),
    }
    res = await db.opportunities.insert_one(doc)
    await write_audit(ctx["org_oid"], ctx["user"], "intel.add_to_pipeline", o.get("title"))
    return {"ok": True, "id": str(res.inserted_id)}
