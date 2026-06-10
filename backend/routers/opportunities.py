from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from bson import ObjectId

from database import db
from utils import now_utc, serialize, oid, iso
from rbac import require_role
from domain import (write_audit, compute_eligibility, default_fit, default_compliance,
                    default_budget, default_criteria, decrypt_secret)
import integrations

router = APIRouter(prefix="/api/orgs", tags=["opportunities"])

STAGES = ["Identified", "Qualifying", "Building", "Submitted", "Won", "Lost", "No-Bid"]


class OpportunityIn(BaseModel):
    title: str = Field(min_length=1)
    solNumber: str = ""
    agency: str = ""
    office: str = ""
    vehicle: str = "RFP"
    setAside: str = "None"
    naics: str = ""
    ceiling: float = 0
    pop: str = ""
    dueDate: Optional[str] = None
    stage: str = "Identified"
    url: str = ""
    winThemes: str = ""


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    solNumber: Optional[str] = None
    agency: Optional[str] = None
    office: Optional[str] = None
    vehicle: Optional[str] = None
    setAside: Optional[str] = None
    naics: Optional[str] = None
    ceiling: Optional[float] = None
    pop: Optional[str] = None
    dueDate: Optional[str] = None
    stage: Optional[str] = None
    url: Optional[str] = None
    winThemes: Optional[str] = None
    fit: Optional[Dict[str, Any]] = None
    pwin: Optional[int] = None
    proposalStrength: Optional[float] = None
    compliance: Optional[List[Dict[str, Any]]] = None
    budget: Optional[Dict[str, Any]] = None
    criteria: Optional[List[Dict[str, Any]]] = None
    decision: Optional[Dict[str, Any]] = None
    links: Optional[List[Dict[str, Any]]] = None


async def _profile(org_oid):
    return await db.orgProfile.find_one({"organizationId": org_oid})


async def _org_keys(org_oid):
    """Decrypt the org's stored Anthropic + SAM keys at call time (server-only)."""
    rec = await db.secrets.find_one({"organizationId": org_oid}) or {}
    return (decrypt_secret(rec.get("anthropicKey", "")),
            decrypt_secret(rec.get("samKey", "")))


def _new_opp_doc(ctx, rec, source):
    """Build a fresh opportunity document from a normalized integration record."""
    ceiling = float(rec.get("ceiling") or 0)
    sol = (rec.get("solNumber") or "").strip()
    url = rec.get("url") or (f"https://sam.gov/opp/{sol}" if sol else "")
    return {
        "organizationId": ctx["org_oid"],
        "title": rec.get("title", ""), "solNumber": sol,
        "agency": rec.get("agency", ""), "office": rec.get("office", ""),
        "vehicle": rec.get("vehicle", "RFP"), "setAside": rec.get("setAside") or "None",
        "naics": rec.get("naics", "") or "", "ceiling": ceiling,
        "pop": rec.get("pop", "") or "", "dueDate": rec.get("dueDate") or None,
        "stage": "Identified", "url": url, "winThemes": "", "source": source,
        "lastVerified": now_utc(), "verifyReport": None,
        "links": [{"label": "Solicitation", "url": url, "status": "live",
                   "checkedAt": iso(now_utc())}],
        "fit": default_fit(), "pwin": 0, "proposalStrength": 0,
        "compliance": default_compliance(), "budget": default_budget(ceiling),
        "criteria": default_criteria(), "decision": {"call": "TBD", "rationale": ""},
        "createdBy": ObjectId(ctx["user"]["id"]),
        "createdAt": now_utc(), "updatedAt": now_utc(),
    }


async def _decorate(opp, profile):
    o = serialize(opp)
    verdict, reason = compute_eligibility(o.get("setAside", ""), profile)
    o["eligibility"] = {"verdict": verdict, "reason": reason}
    return o


@router.get("/{orgId}/opportunities")
async def list_opportunities(ctx: dict = Depends(require_role("viewer"))):
    profile = await _profile(ctx["org_oid"])
    opps = await db.opportunities.find({"organizationId": ctx["org_oid"]}) \
        .sort("updatedAt", -1).to_list(1000)
    return [await _decorate(o, profile) for o in opps]


@router.post("/{orgId}/opportunities")
async def create_opportunity(body: OpportunityIn, ctx: dict = Depends(require_role("editor"))):
    doc = body.model_dump()
    doc.update({
        "organizationId": ctx["org_oid"],
        "source": "manual",
        "lastVerified": None,
        "verifyReport": None,
        "links": [],
        "fit": default_fit(),
        "pwin": 0,
        "proposalStrength": 0,
        "compliance": default_compliance(),
        "budget": default_budget(doc.get("ceiling", 0)),
        "criteria": default_criteria(),
        "decision": {"call": "TBD", "rationale": ""},
        "createdBy": ObjectId(ctx["user"]["id"]),
        "createdAt": now_utc(),
        "updatedAt": now_utc(),
    })
    res = await db.opportunities.insert_one(doc)
    doc["_id"] = res.inserted_id
    await write_audit(ctx["org_oid"], ctx["user"], "opportunity.create", body.title)
    profile = await _profile(ctx["org_oid"])
    return await _decorate(doc, profile)


@router.get("/{orgId}/opportunities/{oppId}")
async def get_opportunity(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await db.opportunities.find_one({"_id": oid(oppId), "organizationId": ctx["org_oid"]})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    profile = await _profile(ctx["org_oid"])
    return await _decorate(opp, profile)


@router.put("/{orgId}/opportunities/{oppId}")
async def update_opportunity(oppId: str, body: OpportunityUpdate,
                             ctx: dict = Depends(require_role("editor"))):
    opp = await db.opportunities.find_one({"_id": oid(oppId), "organizationId": ctx["org_oid"]})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    update["updatedAt"] = now_utc()
    await db.opportunities.update_one({"_id": opp["_id"]}, {"$set": update})
    await write_audit(ctx["org_oid"], ctx["user"], "opportunity.update", opp.get("title"))
    fresh = await db.opportunities.find_one({"_id": opp["_id"]})
    profile = await _profile(ctx["org_oid"])
    return await _decorate(fresh, profile)


@router.delete("/{orgId}/opportunities/{oppId}")
async def delete_opportunity(oppId: str, ctx: dict = Depends(require_role("editor"))):
    opp = await db.opportunities.find_one({"_id": oid(oppId), "organizationId": ctx["org_oid"]})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await db.opportunities.delete_one({"_id": opp["_id"]})
    await write_audit(ctx["org_oid"], ctx["user"], "opportunity.delete", opp.get("title"))
    return {"ok": True}


# ---------------- AI Verify & Refresh (LIVE — Anthropic) ----------------
@router.post("/{orgId}/opportunities/verify")
async def verify_refresh(ctx: dict = Depends(require_role("editor"))):
    """LIVE Anthropic verification: claude-3-5-haiku + web search (capped to keep
    cost well under 10 credits). Confirms each stored opportunity against live web
    sources and discovers up to 3 new matches for the org's NAICS/keywords."""
    anthropic_key, _ = await _org_keys(ctx["org_oid"])
    if not anthropic_key:
        raise HTTPException(status_code=400,
            detail="No Anthropic API key set. Add it in Settings → API Keys.")
    profile = await _profile(ctx["org_oid"]) or {}
    naics = profile.get("naics", [])
    keywords = profile.get("keywords", [])
    # Cap the batch to control web-search + token cost.
    opps = await db.opportunities.find({"organizationId": ctx["org_oid"]}) \
        .sort("updatedAt", -1).to_list(25)
    job = await db.refreshJobs.insert_one({
        "organizationId": ctx["org_oid"], "type": "ai", "status": "running",
        "startedBy": ObjectId(ctx["user"]["id"]), "startedAt": now_utc(),
    })
    payload = [serialize(o) for o in opps]
    try:
        data = await integrations.anthropic_verify(anthropic_key, naics, keywords, payload)
    except Exception as e:
        await db.refreshJobs.update_one({"_id": job.inserted_id},
            {"$set": {"status": "error", "finishedAt": now_utc(), "summary": str(e)}})
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            raise HTTPException(status_code=400,
                detail="Anthropic rejected the API key. Update it in Settings → API Keys.")
        raise HTTPException(status_code=502, detail=f"Anthropic verification failed: {msg}")

    model = data.get("_model", "claude-3-5-haiku")
    vmap = {str(v.get("id")): v for v in (data.get("verifications") or [])}
    flagged = 0
    link_flags = 0
    for opp in opps:
        v = vmap.get(str(opp["_id"]), {})
        link_status = v.get("linkStatus", "unknown")
        if link_status not in ("live", "unknown"):
            link_flags += 1
        link_statuses = [{"label": "Solicitation", "url": opp.get("url", ""),
                          "status": link_status, "checkedAt": iso(now_utc())}]
        sources = v.get("sourceUrls") or ([opp.get("url", "")] if opp.get("url") else [])
        src = sources[0] if sources else ""
        diffs = []
        cur_due = v.get("currentDueDate")
        if v.get("dueDateChanged") and cur_due and cur_due != "unknown" \
                and cur_due != opp.get("dueDate"):
            diffs.append({"field": "dueDate", "current": opp.get("dueDate"),
                          "suggested": cur_due, "confidence": v.get("confidence", "medium"),
                          "note": v.get("notes") or "Source page shows a different close date.",
                          "source": src})
            flagged += 1
        opp_status = v.get("opportunityStatus")
        if opp_status in ("archived", "cancelled"):
            diffs.append({"field": "stage", "current": opp.get("stage"),
                          "suggested": "No-Bid", "confidence": v.get("confidence", "medium"),
                          "note": f"Source indicates this opportunity is {opp_status}.",
                          "source": src})
            flagged += 1
        report = {
            "generatedAt": iso(now_utc()), "model": model,
            "summary": v.get("notes") or "Verified against live web sources via Anthropic.",
            "diffs": diffs, "linkStatuses": link_statuses,
            "confidence": v.get("confidence", "medium"), "sourceUrls": sources,
        }
        await db.opportunities.update_one(
            {"_id": opp["_id"]},
            {"$set": {"verifyReport": report, "lastVerified": now_utc(),
                      "links": link_statuses, "updatedAt": now_utc()}})

    added = 0
    for rec in (data.get("discovered") or [])[:3]:
        title = (rec.get("title") or "").strip()
        if not title:
            continue
        sol = (rec.get("solNumber") or "").strip()
        if sol and await db.opportunities.find_one(
                {"organizationId": ctx["org_oid"], "solNumber": sol}):
            continue
        await db.opportunities.insert_one(_new_opp_doc(ctx, rec, "ai"))
        added += 1

    summary = (f"{len(opps)} verified, {flagged} field suggestions, "
               f"{link_flags} links flagged, {added} discovered")
    await db.refreshJobs.update_one({"_id": job.inserted_id},
                                    {"$set": {"status": "done", "finishedAt": now_utc(),
                                              "summary": summary}})
    await write_audit(ctx["org_oid"], ctx["user"], "ai.verify_refresh", "pipeline",
                      {"summary": summary, "model": model})
    return {"ok": True, "summary": summary, "verified": len(opps),
            "fieldSuggestions": flagged, "linksFlagged": link_flags,
            "discovered": added, "model": model, "mock": False}


class AcceptIn(BaseModel):
    field: str
    value: Any


@router.post("/{orgId}/opportunities/{oppId}/verify/accept")
async def accept_diff(oppId: str, body: AcceptIn, ctx: dict = Depends(require_role("editor"))):
    opp = await db.opportunities.find_one({"_id": oid(oppId), "organizationId": ctx["org_oid"]})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await db.opportunities.update_one(
        {"_id": opp["_id"]},
        {"$set": {body.field: body.value, "updatedAt": now_utc()}})
    # remove the accepted diff from the report
    report = opp.get("verifyReport") or {}
    report["diffs"] = [d for d in report.get("diffs", []) if d.get("field") != body.field]
    await db.opportunities.update_one({"_id": opp["_id"]}, {"$set": {"verifyReport": report}})
    await write_audit(ctx["org_oid"], ctx["user"], "ai.accept_diff", opp.get("title"),
                      {"field": body.field})
    return {"ok": True}


@router.post("/{orgId}/opportunities/{oppId}/verify/dismiss")
async def dismiss_diff(oppId: str, body: AcceptIn, ctx: dict = Depends(require_role("editor"))):
    opp = await db.opportunities.find_one({"_id": oid(oppId), "organizationId": ctx["org_oid"]})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    report = opp.get("verifyReport") or {}
    report["diffs"] = [d for d in report.get("diffs", []) if d.get("field") != body.field]
    await db.opportunities.update_one({"_id": opp["_id"]}, {"$set": {"verifyReport": report}})
    return {"ok": True}


# ---------------- Pull from SAM / Grants (LIVE) ----------------
@router.post("/{orgId}/opportunities/pull")
async def pull_sam_grants(ctx: dict = Depends(require_role("editor"))):
    """LIVE pull from SAM.gov v2 + Grants.gov search2. Dedupe/merge by sol#;
    preserves user-owned fit/compliance/budget/scoring data on existing records."""
    _, sam_key = await _org_keys(ctx["org_oid"])
    if not sam_key:
        raise HTTPException(status_code=400,
            detail="No SAM.gov API key set. Add it in Settings → API Keys.")
    profile = await _profile(ctx["org_oid"]) or {}
    naics = profile.get("naics", [])
    keywords = profile.get("keywords", [])
    job = await db.refreshJobs.insert_one({
        "organizationId": ctx["org_oid"], "type": "sam", "status": "running",
        "startedBy": ObjectId(ctx["user"]["id"]), "startedAt": now_utc(),
    })
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    try:
        records += await integrations.fetch_sam(sam_key, naics, keywords, limit=40)
    except PermissionError:
        await db.refreshJobs.update_one({"_id": job.inserted_id},
            {"$set": {"status": "error", "finishedAt": now_utc(),
                      "summary": "SAM.gov rejected the API key"}})
        raise HTTPException(status_code=400,
            detail="SAM.gov rejected the API key (401/403). Check it in Settings → API Keys.")
    except Exception as e:
        errors.append(f"SAM.gov: {e}")
    try:
        records += await integrations.fetch_grants(keywords)
    except Exception as e:
        errors.append(f"Grants.gov: {e}")

    added, updated = 0, 0
    for rec in records:
        sol = (rec.get("solNumber") or "").strip()
        existing = await db.opportunities.find_one(
            {"organizationId": ctx["org_oid"], "solNumber": sol}) if sol else None
        if existing:
            await db.opportunities.update_one(
                {"_id": existing["_id"]},
                {"$set": {"title": rec.get("title", ""), "agency": rec.get("agency", ""),
                          "office": rec.get("office", ""), "vehicle": rec.get("vehicle", "RFP"),
                          "setAside": rec.get("setAside") or "None", "naics": rec.get("naics", ""),
                          "ceiling": float(rec.get("ceiling") or 0),
                          "dueDate": rec.get("dueDate") or existing.get("dueDate"),
                          "url": rec.get("url") or existing.get("url", ""),
                          "source": rec.get("source", "sam"),
                          "lastVerified": now_utc(), "updatedAt": now_utc()}})
            updated += 1
        else:
            await db.opportunities.insert_one(
                _new_opp_doc(ctx, rec, rec.get("source", "sam")))
            added += 1

    summary = f"{added} added, {updated} updated"
    if errors:
        summary += " — " + "; ".join(errors)
    status = "done" if not (errors and not records) else "error"
    await db.refreshJobs.update_one({"_id": job.inserted_id},
                                    {"$set": {"status": status, "finishedAt": now_utc(),
                                              "summary": summary}})
    await write_audit(ctx["org_oid"], ctx["user"], "pull.sam_grants", "pipeline",
                      {"summary": summary})
    return {"ok": True, "summary": summary, "added": added, "updated": updated,
            "errors": errors, "mock": False}
