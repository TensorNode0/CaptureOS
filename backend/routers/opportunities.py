from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

import database as db
from utils import now_utc, serialize, as_uuid, iso
from rbac import require_role
from domain import (write_audit, default_fit, default_compliance,
                    default_budget, default_criteria)
import integrations
import org_keys
import genai
import scoring

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
    scopeSummary: Optional[str] = None
    tags: Optional[List[str]] = None
    oppType: Optional[str] = None
    acqStage: Optional[str] = None
    recompete: Optional[str] = None
    dueTime: Optional[str] = None
    psc: Optional[str] = None
    naicsTitle: Optional[str] = None
    sizeStandard: Optional[str] = None
    valueType: Optional[str] = None
    valueConfidence: Optional[str] = None
    addressableValue: Optional[float] = None
    contractType: Optional[str] = None
    awardsCount: Optional[str] = None
    vehicleAccess: Optional[str] = None
    pursuitRole: Optional[str] = None
    incumbent: Optional[str] = None
    competition: Optional[Dict[str, Any]] = None
    capture: Optional[Dict[str, Any]] = None
    watch: Optional[bool] = None
    amendments: Optional[List[Dict[str, Any]]] = None


# camelCase API field -> table column (whitelist for partial updates)
UPDATE_COLUMNS = {
    "title": "title", "solNumber": "sol_number", "agency": "agency",
    "office": "office", "vehicle": "vehicle", "setAside": "set_aside",
    "naics": "naics", "ceiling": "ceiling", "pop": "pop", "dueDate": "due_date",
    "stage": "stage", "url": "url", "winThemes": "win_themes", "fit": "fit",
    "pwin": "pwin", "proposalStrength": "proposal_strength",
    "compliance": "compliance", "budget": "budget", "criteria": "criteria",
    "decision": "decision", "links": "links",
    "scopeSummary": "scope_summary", "tags": "tags", "oppType": "opp_type",
    "acqStage": "acq_stage", "recompete": "recompete", "dueTime": "due_time",
    "psc": "psc", "naicsTitle": "naics_title", "sizeStandard": "size_standard",
    "valueType": "value_type", "valueConfidence": "value_confidence",
    "addressableValue": "addressable_value", "contractType": "contract_type",
    "awardsCount": "awards_count", "vehicleAccess": "vehicle_access",
    "pursuitRole": "pursuit_role", "incumbent": "incumbent",
    "competition": "competition", "capture": "capture", "watch": "watch",
    "amendments": "amendments",
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
    # Seed ai_enrichment with anything the source already gave us (PoCs +
    # source description) so it's queryable/displayable before AI runs.
    seed_enrichment = {}
    if rec.get("pocs"):
        seed_enrichment["pocs"] = rec["pocs"]
    if rec.get("description"):
        seed_enrichment["sourceDescription"] = rec["description"][:4000]
    return await db.fetchrow(
        """insert into opportunities
               (organization_id, title, sol_number, agency, office, vehicle, set_aside,
                naics, ceiling, pop, due_date, stage, url, win_themes, source,
                last_verified, verify_report, links, fit, pwin, proposal_strength,
                compliance, budget, criteria, decision, created_by, notice_status,
                scope_summary, psc, due_time, acq_stage, opp_type, value_type,
                ai_enrichment)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'Identified', $12, '',
                   $13, $14, null, $15, $16, 0, 0, $17, $18, $19,
                   '{"call": "TBD", "rationale": ""}'::jsonb, $20, $21,
                   $22, $23, $24, $25, $26, $27, $28)
           returning *""",
        ctx["org_id"], rec.get("title", ""), sol, rec.get("agency", ""),
        rec.get("office", ""), rec.get("vehicle", "RFP"), rec.get("setAside") or "None",
        rec.get("naics", "") or "", ceiling, rec.get("pop", "") or "",
        rec.get("dueDate") or None, url, source, now_utc(), links, default_fit(),
        default_compliance(), default_budget(ceiling), default_criteria(),
        as_uuid(ctx["user"]["id"]), rec.get("noticeStatus") or "open",
        rec.get("scopeSummary", "") or "", rec.get("psc", "") or "",
        rec.get("dueTime", "") or "", rec.get("acqStage", "") or "",
        rec.get("oppType", "") or "", rec.get("valueType", "") or "",
        seed_enrichment or None)


def _decorate(opp_row, profile, org=None):
    """Serialize + attach all derived qualification views (eligibility gates,
    fit score, PWin band, financials, priority, red flags)."""
    return scoring.decorate(serialize(opp_row), profile, org)


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
    return [_decorate(o, profile, ctx["org"]) for o in opps]


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
    return _decorate(opp, profile, ctx["org"])


@router.get("/{orgId}/opportunities/{oppId}")
async def get_opportunity(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    profile = await _profile(ctx["org_id"])
    return _decorate(opp, profile, ctx["org"])


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
    return _decorate(fresh, profile, ctx["org"])


@router.delete("/{orgId}/opportunities/{oppId}")
async def delete_opportunity(oppId: str, ctx: dict = Depends(require_role("editor"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await db.execute("delete from opportunities where id = $1", opp["id"])
    await write_audit(ctx["org_id"], ctx["user"], "opportunity.delete", opp.get("title"))
    return {"ok": True}


# ---------------- AI Verify & Refresh (LIVE) ----------------
AI_ENGINES = {"claude": "anthropic", "openai": "openai", "gemini": "gemini",
              "emergent": "emergent", "asksage": "asksage"}


class VerifyIn(BaseModel):
    engine: str = "claude"  # claude runs live web search; others review saved data
    model: str = ""
    effort: str = "standard"


VERIFY_SYSTEM = (
    "You are a U.S. federal contracting (GovCon) pipeline reviewer WITHOUT live "
    "web access. Review ONLY the saved opportunity data provided: flag due dates "
    "already in the past (set opportunityStatus='archived' when clearly closed), "
    "obviously malformed URLs, and internal inconsistencies. NEVER invent new "
    "opportunities or claim live verification. Respond with a SINGLE JSON object ONLY."
)


def _verify_prompt(today, listing):
    import json as _json
    return (
        f"TODAY: {today}\n\nSAVED OPPORTUNITIES:\n{_json.dumps(listing, default=str)[:14000]}\n\n"
        "Return JSON exactly in this shape:\n"
        '{ "verifications": [ { "id": "<id>", "linkStatus": "unknown", '
        '"dueDateChanged": false, "currentDueDate": null, '
        '"opportunityStatus": "active|archived|unknown", '
        '"confidence": "low|medium|high", "notes": "1 sentence", "sourceUrls": [] } ], '
        '"discovered": [] }\n'
        'One verifications entry per opportunity id. linkStatus must be "unknown" '
        "(no live check was possible)."
    )


async def _verify_via_genai(engine, keys, model, effort, listing):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text, used_model, _ = await genai.generate(
        engine, keys, VERIFY_SYSTEM, _verify_prompt(today, listing),
        max_tokens=6000, model=model, effort=effort)
    data = genai.extract_json(text)
    if data is None or "verifications" not in data:
        raise ValueError("The AI returned an unparseable verification. Try again.")
    data["_model"] = used_model
    data["discovered"] = []
    return data


@router.post("/{orgId}/opportunities/verify")
async def verify_refresh(body: VerifyIn = None,
                         ctx: dict = Depends(require_role("editor"))):
    """Verify stored opportunities. Anthropic verifies against live web sources
    and discovers new matches; other engines review the saved data offline."""
    body = body or VerifyIn()
    engine = body.engine if body.engine in AI_ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="ai.verify_refresh")
    if not keys.get(AI_ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
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
        if engine == "claude":
            data = await integrations.anthropic_verify(keys["anthropic"], naics,
                                                       keywords, payload, capabilities)
        else:
            data = await _verify_via_genai(engine, keys, body.model, body.effort, payload)
    except Exception as e:
        await db.execute(
            "update refresh_jobs set status = 'error', finished_at = $2, summary = $3 where id = $1",
            job["id"], now_utc(), str(e))
        msg = str(e)
        label = genai.ENGINE_LABELS[engine]
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            raise HTTPException(status_code=400,
                detail=f"{label} rejected the API key. Update it in Settings → API Keys.")
        raise HTTPException(status_code=502, detail=f"{label} verification failed: {msg}")

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
            "summary": v.get("notes") or (
                "Verified against live web sources via Anthropic." if engine == "claude"
                else f"Reviewed by {genai.ENGINE_LABELS[engine]} without live web search."),
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


# ---------------- AI Qualify / Enrich (per opportunity) ----------------
ENRICH_SYSTEM = (
    "You are a senior federal capture analyst qualifying ONE saved opportunity. "
    "NEVER invent facts: if a field cannot be verified from the provided data or "
    "(when available) live web sources, return \"Unknown\" (or [] for lists). "
    "Cite a source URL for every fact found online. "
    "Respond with a SINGLE JSON object ONLY — no prose, no markdown fences."
)


def _enrich_prompt(today, opp, profile, live):
    import json as _json
    prof = {}
    if profile:
        prof = {k: profile.get(k) for k in
                ("capabilities", "techFocus", "pastPerformance", "clearances",
                 "cmmcLevel", "targetAgencies", "vehicles", "isSmall", "certs")}
    return (
        f"TODAY: {today}\n"
        f"LIVE WEB SEARCH: {'yes — verify against the official notice/source pages' if live else 'no — analyze the saved data only'}\n\n"
        f"SAVED OPPORTUNITY:\n{_json.dumps(opp, default=str)[:8000]}\n\n"
        f"ORG CAPABILITY PROFILE (for requirement matching):\n{_json.dumps(prof, default=str)[:3000]}\n\n"
        "Return JSON exactly in this shape (use \"Unknown\" when unverifiable):\n"
        '{ "fields": {\n'
        '  "scopeSummary": "one sentence: what the government is buying",\n'
        '  "tags": ["capability tags e.g. autonomy, software, cybersecurity; also compliance flags like CMMC L2, ITAR/EAR, SECRET"],\n'
        '  "oppType": "Contract|Grant|SBIR|STTR|BAA|CSO|OTA|Subcontract|Unknown",\n'
        '  "acqStage": "Forecast|RFI|Sources Sought|Draft RFP|Pre-Solicitation|Active RFP/RFQ|Amendment|Awarded|Cancelled|Closed|Unknown",\n'
        '  "recompete": "New requirement|Recompete|Follow-on|Bridge|Unknown",\n'
        '  "psc": "", "naicsTitle": "", "sizeStandard": "e.g. $34M or 1,250 employees",\n'
        '  "valueType": "Ceiling|Estimated|Max individual award|Task order|Guaranteed minimum|Program funding|Historical|Unknown",\n'
        '  "contractType": "FFP|CPFF|CPAF|T&M|Labor-hour|IDIQ|OTA|Grant|Cooperative agreement|Unknown",\n'
        '  "awardsCount": "Single|Multiple (~N)|Unknown", "incumbent": "",\n'
        '  "pursuitRole": "Prime|Sub|JV|Either|Unknown", "dueTime": "e.g. 17:00 ET",\n'
        '  "competition": {"intensity": "Low|Moderate|High|Unknown", "likelyBidders": "", "awardNumber": ""} },\n'
        '  "requirementMatches": [ {"requirement": "shall-statement or key requirement", "mandatory": true, '
        '"score": 0, "evidence": "org capability/past-performance evidence, or the gap", "source": "solicitation section/page or URL"} ],\n'
        '  "gaps": ["material capability, compliance or teaming gaps"],\n'
        '  "sources": ["urls actually consulted"], "confidence": "low|medium|high" }\n\n'
        "Score each requirement: 100 = direct capability with strong evidence; 75 = direct but "
        "limited proof/scale; 50 = adjacent capability or credible partner dependency; "
        "25 = material gap needing development/teaming; 0 = cannot meet. "
        "Weight mandatory ('shall') requirements above general similarity."
    )


# AI may only FILL these columns when they are currently empty — user edits win.
ENRICH_FILLABLE = {
    "scopeSummary": "scope_summary", "oppType": "opp_type", "acqStage": "acq_stage",
    "recompete": "recompete", "psc": "psc", "naicsTitle": "naics_title",
    "sizeStandard": "size_standard", "valueType": "value_type",
    "contractType": "contract_type", "awardsCount": "awards_count",
    "incumbent": "incumbent", "pursuitRole": "pursuit_role", "dueTime": "due_time",
}


@router.post("/{orgId}/opportunities/{oppId}/enrich")
async def enrich_opportunity(oppId: str, body: VerifyIn = None,
                             ctx: dict = Depends(require_role("editor"))):
    """AI qualification of one opportunity: scope, classification, evidence-backed
    requirement matches, gaps and sources. Only fills EMPTY fields — user-entered
    data is never overwritten. Unknowns stay unknown."""
    body = body or VerifyIn()
    engine = body.engine if body.engine in AI_ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="ai.enrich")
    if not keys.get(AI_ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    profile = await _profile(ctx["org_id"])
    saved = serialize(opp)
    slim = {k: saved.get(k) for k in
            ("title", "solNumber", "agency", "office", "vehicle", "setAside", "naics",
             "psc", "ceiling", "dueDate", "url", "scopeSummary", "oppType", "acqStage",
             "contractType", "incumbent", "pop")}
    live = engine == "claude"
    today = now_utc().strftime("%Y-%m-%d")
    try:
        text, model, _ = await genai.generate(
            engine, keys, ENRICH_SYSTEM, _enrich_prompt(today, slim, profile, live),
            max_tokens=8000, web_search=live, model=body.model, effort=body.effort)
    except Exception as e:
        msg = str(e)
        label = genai.ENGINE_LABELS[engine]
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            raise HTTPException(status_code=400,
                detail=f"{label} rejected the API key. Update it in Settings → API Keys.")
        raise HTTPException(status_code=502, detail=f"{label} enrichment failed: {msg}")
    data = genai.extract_json(text)
    if data is None:
        raise HTTPException(status_code=502,
            detail="The AI response could not be parsed. Try again.")

    fields = data.get("fields") or {}
    applied = []
    sets, args = ["updated_at = $1"], [now_utc()]

    def _known(v):
        s = str(v or "").strip()
        return bool(s) and not s.lower().startswith("unknown")

    for k, col in ENRICH_FILLABLE.items():
        v = fields.get(k)
        if not _known(v) or (opp.get(col) or "").strip():
            continue
        args.append(str(v).strip())
        sets.append(f"{col} = ${len(args)}")
        applied.append(k)
    tags = [str(t) for t in (fields.get("tags") or []) if _known(t)]
    if tags:
        merged = list(dict.fromkeys([*(opp.get("tags") or []), *tags]))[:12]
        args.append(merged)
        sets.append(f"tags = ${len(args)}")
        applied.append("tags")
    comp_new = {k: v for k, v in (fields.get("competition") or {}).items() if _known(v)}
    if comp_new:
        merged = {**comp_new, **{k: v for k, v in (opp.get("competition") or {}).items() if v}}
        args.append(merged)
        sets.append(f"competition = ${len(args)}")
        applied.append("competition")

    enrichment = {
        "generatedAt": iso(now_utc()), "engine": engine, "model": model,
        "confidence": data.get("confidence", "medium"),
        "requirementMatches": (data.get("requirementMatches") or [])[:25],
        "gaps": (data.get("gaps") or [])[:10],
        "sources": (data.get("sources") or [])[:10],
        "fields": fields,
    }
    args.append(enrichment)
    sets.append(f"ai_enrichment = ${len(args)}")
    args.append(opp["id"])
    fresh = await db.fetchrow(
        f"update opportunities set {', '.join(sets)} where id = ${len(args)} returning *",
        *args)
    await write_audit(ctx["org_id"], ctx["user"], "ai.enrich", opp.get("title"),
                      {"applied": applied, "model": model})
    out = _decorate(fresh, profile, ctx["org"])
    out["_appliedFields"] = applied
    return out


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
                       notice_status = $13,
                       psc = coalesce(nullif($14, ''), psc),
                       due_time = coalesce(nullif($15, ''), due_time),
                       acq_stage = coalesce(nullif($16, ''), acq_stage),
                       opp_type = coalesce(nullif($17, ''), opp_type)
                   where id = $1""",
                existing["id"], rec.get("title", ""), rec.get("agency", ""),
                rec.get("office", ""), rec.get("vehicle", "RFP"),
                rec.get("setAside") or "None", rec.get("naics", ""),
                float(rec.get("ceiling") or 0), rec.get("dueDate"),
                rec.get("url") or "", rec.get("source", "sam"), now_utc(),
                rec.get("noticeStatus") or "open", rec.get("psc", "") or "",
                rec.get("dueTime", "") or "", rec.get("acqStage", "") or "",
                rec.get("oppType", "") or "")
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



# ---------------- AI Opportunity Summary + PoC extraction ----------------
SUMMARY_SYSTEM = (
    "You are a senior U.S. federal capture analyst. Read the saved opportunity data "
    "(including any source description) and produce a compact, human-readable brief "
    "for a busy business developer. NEVER fabricate: if a field is not present in the "
    "provided data, say so. Respond with a SINGLE JSON object ONLY."
)


def _summary_prompt(opp: dict, source_desc: str) -> str:
    import json as _json
    slim = {k: opp.get(k) for k in (
        "title", "solNumber", "agency", "office", "vehicle", "setAside", "naics",
        "psc", "ceiling", "dueDate", "url", "scopeSummary", "oppType", "acqStage",
        "contractType", "incumbent", "pop")}
    return (
        f"OPPORTUNITY:\n{_json.dumps(slim, default=str)[:4000]}\n\n"
        f"SOURCE DESCRIPTION (may be truncated):\n{(source_desc or '')[:6000]}\n\n"
        "Return JSON exactly in this shape:\n"
        '{ "summary": "3-5 tight paragraphs covering: what the government is buying, '
        'who it is for, the mission/context, key requirements, dates & value, '
        'and the top 2-3 questions a bidder must answer",\n'
        '  "pocs": [ { "name": "", "role": "PoC|TPoC", "title": "", '
        '"email": "", "phone": "" } ],\n'
        '  "confidence": "low|medium|high" }\n'
        "Extract any names/emails/phones present in the source description as PoCs. "
        "Classify contracting/procurement contacts as PoC and technical/program contacts as TPoC."
    )


class SummaryIn(BaseModel):
    engine: str = "claude"
    model: str = ""
    effort: str = "standard"


@router.post("/{orgId}/opportunities/{oppId}/summary")
async def opportunity_summary(oppId: str, body: SummaryIn = None,
                              ctx: dict = Depends(require_role("editor"))):
    """Generate a human-readable summary + extract PoCs/TPoCs for one opportunity.
    Merges any AI-discovered contacts with those already parsed from SAM.gov.
    Persists both in the `ai_enrichment` jsonb column."""
    body = body or SummaryIn()
    engine = body.engine if body.engine in AI_ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"],
                                   purpose="ai.opportunity_summary")
    if not keys.get(AI_ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    saved = serialize(opp)
    enr_before = opp.get("ai_enrichment") or {}
    source_desc = enr_before.get("sourceDescription", "")
    try:
        text, model, _ = await genai.generate(
            engine, keys, SUMMARY_SYSTEM, _summary_prompt(saved, source_desc),
            max_tokens=4000, model=body.model, effort=body.effort)
    except Exception as e:
        msg = str(e)
        label = genai.ENGINE_LABELS[engine]
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            raise HTTPException(status_code=400,
                detail=f"{label} rejected the API key. Update it in Settings → API Keys.")
        raise HTTPException(status_code=502, detail=f"{label} summary failed: {msg}")
    data = genai.extract_json(text) or {}
    summary_text = (data.get("summary") or "").strip()
    ai_pocs = [p for p in (data.get("pocs") or []) if (p.get("name") or p.get("email"))]
    # Merge AI-extracted PoCs with any already parsed from SAM.gov, dedupe by
    # (name, email) so we don't show duplicates when SAM already provided them.
    seen = set()
    merged_pocs = []
    for p in [*(enr_before.get("pocs") or []), *ai_pocs]:
        key = ((p.get("name") or "").lower().strip(),
               (p.get("email") or "").lower().strip())
        if key in seen or key == ("", ""):
            continue
        seen.add(key)
        merged_pocs.append(p)
    new_enrichment = {**enr_before,
                      "summary": summary_text,
                      "summaryGeneratedAt": iso(now_utc()),
                      "summaryModel": model,
                      "pocs": merged_pocs,
                      "summaryConfidence": data.get("confidence", "medium")}
    fresh = await db.fetchrow(
        """update opportunities set ai_enrichment = $2, updated_at = $3
           where id = $1 returning *""",
        opp["id"], new_enrichment, now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "ai.opportunity_summary",
                      opp.get("title"), {"model": model})
    profile = await _profile(ctx["org_id"])
    return _decorate(fresh, profile, ctx["org"])
