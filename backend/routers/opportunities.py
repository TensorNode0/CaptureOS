import random
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from bson import ObjectId

from database import db
from utils import now_utc, serialize, oid, iso
from rbac import require_role
from domain import (write_audit, compute_eligibility, default_fit, default_compliance,
                    default_budget, default_criteria)

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


# ---------------- AI Verify & Refresh (MOCKED) ----------------
@router.post("/{orgId}/opportunities/verify")
async def verify_refresh(ctx: dict = Depends(require_role("editor"))):
    """MOCK of the Anthropic web-search/web-fetch verification.
    Produces a structured verifyReport with accept/dismiss diffs per opportunity.
    Real Anthropic Messages API wiring is Phase 5."""
    job = await db.refreshJobs.insert_one({
        "organizationId": ctx["org_oid"], "type": "ai", "status": "running",
        "startedBy": ObjectId(ctx["user"]["id"]), "startedAt": now_utc(),
    })
    opps = await db.opportunities.find({"organizationId": ctx["org_oid"]}).to_list(1000)
    flagged = 0
    link_flags = 0
    for opp in opps:
        diffs = []
        link_statuses = []
        # simulate link freshness check
        for ln in (opp.get("links") or [{"label": "Solicitation", "url": opp.get("url", "")}]):
            status = random.choice(["live", "live", "live", "stale", "moved"])
            if status != "live":
                link_flags += 1
            link_statuses.append({"label": ln.get("label", "Link"), "url": ln.get("url", ""),
                                  "status": status, "checkedAt": iso(now_utc())})
        # simulate a due-date drift suggestion ~40% of the time
        if opp.get("dueDate") and random.random() < 0.4:
            diffs.append({
                "field": "dueDate", "current": opp.get("dueDate"),
                "suggested": opp.get("dueDate"),
                "confidence": "medium",
                "note": "Source page shows the same close date — confirmed current.",
                "source": opp.get("url", ""),
            })
        if random.random() < 0.3:
            diffs.append({
                "field": "stage", "current": opp.get("stage"),
                "suggested": "Qualifying",
                "confidence": "low",
                "note": "AI heuristic suggestion — review before applying.",
                "source": opp.get("url", ""),
            })
            flagged += 1
        report = {
            "generatedAt": iso(now_utc()),
            "model": "claude-haiku (mock)",
            "summary": "Assistive verification (mock). Always confirm against the official source link.",
            "diffs": diffs,
            "linkStatuses": link_statuses,
            "confidence": random.choice(["high", "medium"]),
        }
        await db.opportunities.update_one(
            {"_id": opp["_id"]},
            {"$set": {"verifyReport": report, "lastVerified": now_utc(),
                      "links": link_statuses, "updatedAt": now_utc()}})
    summary = f"{len(opps)} verified, {flagged} field suggestions, {link_flags} links flagged"
    await db.refreshJobs.update_one({"_id": job.inserted_id},
                                    {"$set": {"status": "done", "finishedAt": now_utc(),
                                              "summary": summary}})
    await write_audit(ctx["org_oid"], ctx["user"], "ai.verify_refresh", "pipeline",
                      {"summary": summary})
    return {"ok": True, "summary": summary, "verified": len(opps),
            "fieldSuggestions": flagged, "linksFlagged": link_flags, "mock": True}


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


# ---------------- Pull from SAM / Grants (MOCKED) ----------------
MOCK_SAM = [
    {"title": "Advanced Tactical UAS Propulsion R&D", "solNumber": "FA8650-26-R-0142",
     "agency": "Department of the Air Force", "office": "AFRL", "vehicle": "RFP",
     "setAside": "Total Small Business", "naics": "336412", "ceiling": 4800000,
     "source": "sam"},
    {"title": "Hypersonic Thermal Protection Materials", "solNumber": "N00024-26-R-3310",
     "agency": "Department of the Navy", "office": "NAVSEA", "vehicle": "BAA",
     "setAside": "None", "naics": "541715", "ceiling": 12500000, "source": "sam"},
    {"title": "Cyber Resiliency Assessment Services", "solNumber": "W519TC-26-R-0021",
     "agency": "Department of the Army", "office": "ACC-APG", "vehicle": "RFP",
     "setAside": "8(a)", "naics": "541512", "ceiling": 3200000, "source": "sam"},
    {"title": "SDVOSB Logistics Modernization Support", "solNumber": "SP4701-26-R-0099",
     "agency": "Defense Logistics Agency", "office": "DLA", "vehicle": "RFP",
     "setAside": "SDVOSB", "naics": "541611", "ceiling": 2100000, "source": "sam"},
]
MOCK_GRANTS = [
    {"title": "SBIR Phase II: Autonomous ISR Edge Compute", "solNumber": "DOD-SBIR-26.1-A2",
     "agency": "Department of Defense", "office": "DSIP", "vehicle": "SBIR",
     "setAside": "Total Small Business", "naics": "541715", "ceiling": 1800000,
     "source": "grants"},
    {"title": "STTR: Quantum Sensing for Navigation", "solNumber": "AF-STTR-26-X12",
     "agency": "Department of the Air Force", "office": "AFWERX", "vehicle": "STTR",
     "setAside": "Total Small Business", "naics": "541714", "ceiling": 1950000,
     "source": "grants"},
]


@router.post("/{orgId}/opportunities/pull")
async def pull_sam_grants(ctx: dict = Depends(require_role("editor"))):
    """MOCK of SAM.gov + Grants.gov pull. Dedupe/merge by solNumber; preserves
    user-owned fit/compliance/budget/scoring. Real pull (govcon_pull.py) is Phase 5."""
    job = await db.refreshJobs.insert_one({
        "organizationId": ctx["org_oid"], "type": "sam", "status": "running",
        "startedBy": ObjectId(ctx["user"]["id"]), "startedAt": now_utc(),
    })
    added, updated = 0, 0
    from datetime import timedelta
    for idx, rec in enumerate(MOCK_SAM + MOCK_GRANTS):
        due = (now_utc() + timedelta(days=random.choice([5, 12, 25, 45, 70]))).date().isoformat()
        existing = await db.opportunities.find_one(
            {"organizationId": ctx["org_oid"], "solNumber": rec["solNumber"]})
        if existing:
            # merge metadata only, keep user assessment data
            await db.opportunities.update_one(
                {"_id": existing["_id"]},
                {"$set": {"title": rec["title"], "agency": rec["agency"],
                          "office": rec["office"], "vehicle": rec["vehicle"],
                          "setAside": rec["setAside"], "naics": rec["naics"],
                          "ceiling": rec["ceiling"], "source": rec["source"],
                          "lastVerified": now_utc(), "updatedAt": now_utc()}})
            updated += 1
        else:
            doc = {
                "organizationId": ctx["org_oid"],
                "title": rec["title"], "solNumber": rec["solNumber"],
                "agency": rec["agency"], "office": rec["office"],
                "vehicle": rec["vehicle"], "setAside": rec["setAside"],
                "naics": rec["naics"], "ceiling": rec["ceiling"],
                "pop": "12 months base", "dueDate": due, "stage": "Identified",
                "url": f"https://sam.gov/opp/{rec['solNumber']}",
                "winThemes": "", "source": rec["source"],
                "lastVerified": now_utc(), "verifyReport": None,
                "links": [{"label": "Solicitation", "url": f"https://sam.gov/opp/{rec['solNumber']}",
                           "status": "live", "checkedAt": iso(now_utc())}],
                "fit": default_fit(), "pwin": 0, "proposalStrength": 0,
                "compliance": default_compliance(), "budget": default_budget(rec["ceiling"]),
                "criteria": default_criteria(), "decision": {"call": "TBD", "rationale": ""},
                "createdBy": ObjectId(ctx["user"]["id"]),
                "createdAt": now_utc(), "updatedAt": now_utc(),
            }
            await db.opportunities.insert_one(doc)
            added += 1
    summary = f"{added} added, {updated} updated (SAM + Grants, mock)"
    await db.refreshJobs.update_one({"_id": job.inserted_id},
                                    {"$set": {"status": "done", "finishedAt": now_utc(),
                                              "summary": summary}})
    await write_audit(ctx["org_oid"], ctx["user"], "pull.sam_grants", "pipeline",
                      {"summary": summary})
    return {"ok": True, "summary": summary, "added": added, "updated": updated, "mock": True}
