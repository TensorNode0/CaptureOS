from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

import database as db
from utils import now_utc, serialize, as_uuid, iso
from rbac import require_role
from domain import (write_audit, compute_eligibility, default_fit, default_compliance,
                    default_budget, default_criteria)
import integrations
import org_keys

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


# camelCase API field -> table column (whitelist for partial updates)
UPDATE_COLUMNS = {
    "title": "title", "solNumber": "sol_number", "agency": "agency",
    "office": "office", "vehicle": "vehicle", "setAside": "set_aside",
    "naics": "naics", "ceiling": "ceiling", "pop": "pop", "dueDate": "due_date",
    "stage": "stage", "url": "url", "winThemes": "win_themes", "fit": "fit",
    "pwin": "pwin", "proposalStrength": "proposal_strength",
    "compliance": "compliance", "budget": "budget", "criteria": "criteria",
    "decision": "decision", "links": "links",
}


async def _profile(org_id):
    prof = await db.fetchrow("select * from org_profiles where organization_id = $1", org_id)
    return serialize(prof) if prof else None


async def _insert_opp(ctx, rec, source):
    """Insert a fresh opportunity from a normalized integration record."""
    ceiling = float(rec.get("ceiling") or 0)
    sol = (rec.get("solNumber") or "").strip()
    url = rec.get("url") or (f"https://sam.gov/opp/{sol}" if sol else "")
    links = [{"label": "Solicitation", "url": url, "status": "live",
              "checkedAt": iso(now_utc())}]
    return await db.fetchrow(
        """insert into opportunities
               (organization_id, title, sol_number, agency, office, vehicle, set_aside,
                naics, ceiling, pop, due_date, stage, url, win_themes, source,
                last_verified, verify_report, links, fit, pwin, proposal_strength,
                compliance, budget, criteria, decision, created_by, notice_status)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'Identified', $12, '',
                   $13, $14, null, $15, $16, 0, 0, $17, $18, $19,
                   '{"call": "TBD", "rationale": ""}'::jsonb, $20, $21)
           returning *""",
        ctx["org_id"], rec.get("title", ""), sol, rec.get("agency", ""),
        rec.get("office", ""), rec.get("vehicle", "RFP"), rec.get("setAside") or "None",
        rec.get("naics", "") or "", ceiling, rec.get("pop", "") or "",
        rec.get("dueDate") or None, url, source, now_utc(), links, default_fit(),
        default_compliance(), default_budget(ceiling), default_criteria(),
        as_uuid(ctx["user"]["id"]), rec.get("noticeStatus") or "open")


def _decorate(opp_row, profile):
    o = serialize(opp_row)
    verdict, reason = compute_eligibility(o.get("setAside", ""), profile)
    o["eligibility"] = {"verdict": verdict, "reason": reason}
    return o


async def _get_opp(org_id, opp_id):
    oid_ = as_uuid(opp_id)
    if oid_ is None:
        return None
    return await db.fetchrow(
        "select * from opportunities where id = $1 and organization_id = $2",
        oid_, org_id)


@router.get("/{orgId}/opportunities")
async def list_opportunities(ctx: dict = Depends(require_role("viewer"))):
    profile = await _profile(ctx["org_id"])
    opps = await db.fetch(
        """select * from opportunities where organization_id = $1
           order by updated_at desc limit 1000""",
        ctx["org_id"])
    return [_decorate(o, profile) for o in opps]


@router.post("/{orgId}/opportunities")
async def create_opportunity(body: OpportunityIn, ctx: dict = Depends(require_role("editor"))):
    opp = await db.fetchrow(
        """insert into opportunities
               (organization_id, title, sol_number, agency, office, vehicle, set_aside,
                naics, ceiling, pop, due_date, stage, url, win_themes, source,
                links, fit, compliance, budget, criteria, created_by)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                   'manual', '[]'::jsonb, $15, $16, $17, $18, $19)
           returning *""",
        ctx["org_id"], body.title, body.solNumber, body.agency, body.office,
        body.vehicle, body.setAside, body.naics, body.ceiling, body.pop,
        body.dueDate, body.stage, body.url, body.winThemes, default_fit(),
        default_compliance(), default_budget(body.ceiling), default_criteria(),
        as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "opportunity.create", body.title)
    profile = await _profile(ctx["org_id"])
    return _decorate(opp, profile)


@router.get("/{orgId}/opportunities/{oppId}")
async def get_opportunity(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    profile = await _profile(ctx["org_id"])
    return _decorate(opp, profile)


@router.put("/{orgId}/opportunities/{oppId}")
async def update_opportunity(oppId: str, body: OpportunityUpdate,
                             ctx: dict = Depends(require_role("editor"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    sets, args = ["updated_at = $1"], [now_utc()]
    for field, value in updates.items():
        col = UPDATE_COLUMNS.get(field)
        if not col:
            continue
        args.append(value)
        sets.append(f"{col} = ${len(args)}")
    args.append(opp["id"])
    fresh = await db.fetchrow(
        f"update opportunities set {', '.join(sets)} where id = ${len(args)} returning *",
        *args)
    await write_audit(ctx["org_id"], ctx["user"], "opportunity.update", opp.get("title"))
    profile = await _profile(ctx["org_id"])
    return _decorate(fresh, profile)


@router.delete("/{orgId}/opportunities/{oppId}")
async def delete_opportunity(oppId: str, ctx: dict = Depends(require_role("editor"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await db.execute("delete from opportunities where id = $1", opp["id"])
    await write_audit(ctx["org_id"], ctx["user"], "opportunity.delete", opp.get("title"))
    return {"ok": True}


# ---------------- AI Verify & Refresh (LIVE — Anthropic) ----------------
@router.post("/{orgId}/opportunities/verify")
async def verify_refresh(ctx: dict = Depends(require_role("editor"))):
    """LIVE Anthropic verification: confirms each stored opportunity against live
    web sources and discovers up to 3 new matches for the org's NAICS/keywords."""
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="ai.verify_refresh")
    anthropic_key = keys["anthropic"]
    if not anthropic_key:
        raise HTTPException(status_code=400,
            detail="No Anthropic API key set. Add it in Settings → API Keys.")
    org = ctx["org"]
    naics = org.get("naics") or []
    keywords = org.get("keywords") or []
    prof = await _profile(ctx["org_id"]) or {}
    capabilities = (prof.get("capabilities") or "")[:600]
    # Cap the batch to control web-search + token cost.
    opps = await db.fetch(
        """select * from opportunities where organization_id = $1
           order by updated_at desc limit 25""",
        ctx["org_id"])
    job = await db.fetchrow(
        """insert into refresh_jobs (organization_id, type, status, started_by)
           values ($1, 'ai', 'running', $2) returning id""",
        ctx["org_id"], as_uuid(ctx["user"]["id"]))
    payload = [serialize(o) for o in opps]
    try:
        data = await integrations.anthropic_verify(anthropic_key, naics, keywords,
                                                   payload, capabilities)
    except Exception as e:
        await db.execute(
            "update refresh_jobs set status = 'error', finished_at = $2, summary = $3 where id = $1",
            job["id"], now_utc(), str(e))
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            raise HTTPException(status_code=400,
                detail="Anthropic rejected the API key. Update it in Settings → API Keys.")
        raise HTTPException(status_code=502, detail=f"Anthropic verification failed: {msg}")

    model = data.get("_model", "claude-haiku")
    vmap = {str(v.get("id")): v for v in (data.get("verifications") or [])}
    flagged = 0
    link_flags = 0
    for opp in opps:
        v = vmap.get(str(opp["id"]), {})
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
                and cur_due != opp.get("due_date"):
            diffs.append({"field": "dueDate", "current": opp.get("due_date"),
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
        await db.execute(
            """update opportunities
               set verify_report = $2, last_verified = $3, links = $4, updated_at = $3
               where id = $1""",
            opp["id"], report, now_utc(), link_statuses)

    added = 0
    for rec in (data.get("discovered") or [])[:3]:
        title = (rec.get("title") or "").strip()
        if not title:
            continue
        sol = (rec.get("solNumber") or "").strip()
        if sol and await db.fetchrow(
                "select id from opportunities where organization_id = $1 and sol_number = $2",
                ctx["org_id"], sol):
            continue
        await _insert_opp(ctx, rec, "ai")
        added += 1

    summary = (f"{len(opps)} verified, {flagged} field suggestions, "
               f"{link_flags} links flagged, {added} discovered")
    await db.execute(
        "update refresh_jobs set status = 'done', finished_at = $2, summary = $3 where id = $1",
        job["id"], now_utc(), summary)
    await write_audit(ctx["org_id"], ctx["user"], "ai.verify_refresh", "pipeline",
                      {"summary": summary, "model": model})
    return {"ok": True, "summary": summary, "verified": len(opps),
            "fieldSuggestions": flagged, "linksFlagged": link_flags,
            "discovered": added, "model": model, "mock": False}


class AcceptIn(BaseModel):
    field: str
    value: Any


# Diff acceptance may only touch these simple fields.
ACCEPT_FIELDS = {"dueDate": "due_date", "stage": "stage", "url": "url",
                 "title": "title", "ceiling": "ceiling"}


@router.post("/{orgId}/opportunities/{oppId}/verify/accept")
async def accept_diff(oppId: str, body: AcceptIn, ctx: dict = Depends(require_role("editor"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    col = ACCEPT_FIELDS.get(body.field)
    if not col:
        raise HTTPException(status_code=400, detail="This field cannot be auto-accepted")
    value = body.value
    if body.field == "ceiling":
        try:
            value = float(value or 0)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid ceiling value")
    await db.execute(
        f"update opportunities set {col} = $2, updated_at = $3 where id = $1",
        opp["id"], value, now_utc())
    # remove the accepted diff from the report
    report = opp.get("verify_report") or {}
    report["diffs"] = [d for d in report.get("diffs", []) if d.get("field") != body.field]
    await db.execute("update opportunities set verify_report = $2 where id = $1",
                     opp["id"], report)
    await write_audit(ctx["org_id"], ctx["user"], "ai.accept_diff", opp.get("title"),
                      {"field": body.field})
    return {"ok": True}


@router.post("/{orgId}/opportunities/{oppId}/verify/dismiss")
async def dismiss_diff(oppId: str, body: AcceptIn, ctx: dict = Depends(require_role("editor"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    report = opp.get("verify_report") or {}
    report["diffs"] = [d for d in report.get("diffs", []) if d.get("field") != body.field]
    await db.execute("update opportunities set verify_report = $2 where id = $1",
                     opp["id"], report)
    return {"ok": True}


# ---------------- Pull from SAM / Grants (LIVE) ----------------
@router.post("/{orgId}/opportunities/pull")
async def pull_sam_grants(ctx: dict = Depends(require_role("editor"))):
    """LIVE pull from SAM.gov v2 + Grants.gov search2. Dedupe/merge by sol#;
    preserves user-owned fit/compliance/budget/scoring data on existing records."""
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="pull.sam_grants")
    sam_key = keys["sam"]
    if not sam_key:
        raise HTTPException(status_code=400,
            detail="No SAM.gov API key set. Add it in Settings → API Keys.")
    org = ctx["org"]
    naics = org.get("naics") or []
    keywords = org.get("keywords") or []
    prof = serialize(await _profile(ctx["org_id"])) or {}
    job = await db.fetchrow(
        """insert into refresh_jobs (organization_id, type, status, started_by)
           values ($1, 'sam', 'running', $2) returning id""",
        ctx["org_id"], as_uuid(ctx["user"]["id"]))
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    try:
        records += await integrations.fetch_sam(sam_key, naics, keywords, limit=40,
                                                psc=(prof.get("pscCodes") or []))
    except PermissionError:
        await db.execute(
            "update refresh_jobs set status = 'error', finished_at = $2, summary = $3 where id = $1",
            job["id"], now_utc(), "SAM.gov rejected the API key")
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
        existing = await db.fetchrow(
            "select * from opportunities where organization_id = $1 and sol_number = $2",
            ctx["org_id"], sol) if sol else None
        if existing:
            await db.execute(
                """update opportunities
                   set title = $2, agency = $3, office = $4, vehicle = $5,
                       set_aside = $6, naics = $7,
                       ceiling = greatest(ceiling, $8),
                       due_date = coalesce($9, due_date),
                       url = coalesce(nullif($10, ''), url),
                       source = $11, last_verified = $12, updated_at = $12,
                       notice_status = $13
                   where id = $1""",
                existing["id"], rec.get("title", ""), rec.get("agency", ""),
                rec.get("office", ""), rec.get("vehicle", "RFP"),
                rec.get("setAside") or "None", rec.get("naics", ""),
                float(rec.get("ceiling") or 0), rec.get("dueDate"),
                rec.get("url") or "", rec.get("source", "sam"), now_utc(),
                rec.get("noticeStatus") or "open")
            updated += 1
        else:
            await _insert_opp(ctx, rec, rec.get("source", "sam"))
            added += 1

    summary = f"{added} added, {updated} updated"
    if errors:
        summary += " — " + "; ".join(errors)
    status = "done" if not (errors and not records) else "error"
    await db.execute(
        "update refresh_jobs set status = $2, finished_at = $3, summary = $4 where id = $1",
        job["id"], status, now_utc(), summary)
    await write_audit(ctx["org_id"], ctx["user"], "pull.sam_grants", "pipeline",
                      {"summary": summary})
    return {"ok": True, "summary": summary, "added": added, "updated": updated,
            "errors": errors, "mock": False}
