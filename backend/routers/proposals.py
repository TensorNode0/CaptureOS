"""Proposal package: per-volume AI drafting (Claude or ChatGPT), human edit,
finalize, and export — single documents (.docx/.xlsx/.pptx) or the whole
package as a .zip."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Any, Dict, Optional

import database as db
from utils import now_utc, serialize, as_uuid
from rbac import require_role, require_perm
from billing import assert_full_tier
from domain import write_audit
import proposal_ai
import ai_jobs
import genai
import exports
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["proposals"])

MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


async def _get_opp(org_id, opp_id):
    oid_ = as_uuid(opp_id)
    if oid_ is None:
        return None
    return await db.fetchrow(
        "select * from opportunities where id = $1 and organization_id = $2",
        oid_, org_id)


async def _get_proposal(org_id, opp_id):
    oid_ = as_uuid(opp_id)
    if oid_ is None:
        return None
    return await db.fetchrow(
        "select * from proposals where opportunity_id = $1 and organization_id = $2",
        oid_, org_id)


async def _get_doc(proposal_id, doc_id):
    did = as_uuid(doc_id)
    if did is None:
        return None
    return await db.fetchrow(
        "select * from proposal_documents where id = $1 and proposal_id = $2",
        did, proposal_id)


async def _docs(proposal_id):
    return await db.fetch(
        """select * from proposal_documents where proposal_id = $1
           order by sort_order, created_at""",
        proposal_id)


async def _payload(proposal):
    out = serialize(proposal)
    out["documents"] = [serialize(d) for d in await _docs(proposal["id"])]
    return out


async def _cap_content(org_id, opp_id):
    cap = await db.fetchrow(
        "select content from capabilities where opportunity_id = $1 and organization_id = $2",
        opp_id, org_id)
    return (cap or {}).get("content") or None


@router.get("/{orgId}/opportunities/{oppId}/proposal")
async def get_proposal(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not proposal:
        return None
    return await _payload(proposal)


@router.post("/{orgId}/opportunities/{oppId}/proposal")
async def create_proposal(oppId: str, ctx: dict = Depends(require_perm("proposal.create"))):
    await assert_full_tier(ctx["user"])
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if proposal:
        return await _payload(proposal)
    proposal = await db.fetchrow(
        """insert into proposals (organization_id, opportunity_id, created_by)
           values ($1, $2, $3) returning *""",
        ctx["org_id"], opp["id"], as_uuid(ctx["user"]["id"]))
    for doc_type in proposal_ai.volume_set_for(opp.get("vehicle")):
        d = proposal_ai.DOC_TYPES[doc_type]
        await db.execute(
            """insert into proposal_documents
                   (proposal_id, doc_type, title, fmt, sort_order)
               values ($1, $2, $3, $4, $5)""",
            proposal["id"], doc_type, d["title"], d["fmt"], d["sort"])
    await write_audit(ctx["org_id"], ctx["user"], "proposal.create", opp.get("title"),
                      {"vehicle": opp.get("vehicle")})
    return await _payload(proposal)


class DraftIn(BaseModel):
    engine: str = "claude"  # claude | openai | emergent | asksage
    model: str = ""
    effort: str = "standard"


async def _run_draft(doc_id, engine, keys,
                     org, profile, opp, cap_content, user, org_id,
                     model="", effort="", job_id=None):
    try:
        doc = await db.fetchrow("select * from proposal_documents where id = $1", doc_id)
        md, data, used_model = await proposal_ai.draft_document(
            engine, keys, doc["doc_type"],
            org, profile, opp, cap_content,
            model=model, effort=effort, job_id=job_id)
        if job_id:
            await ai_jobs.stage(job_id, "Saving the draft…", 95)
        await db.execute(
            """update proposal_documents
               set content_md = $2, content_json = $3, status = 'drafted',
                   draft_status = 'idle', draft_error = '', model = $4, updated_at = $5
               where id = $1""",
            doc_id, md, data, used_model, now_utc())
        if job_id:
            await ai_jobs.finish(job_id, "Draft ready")
        await write_audit(org_id, user, "proposal.draft", doc["title"],
                          {"engine": engine, "model": used_model})
    except ai_jobs.JobCancelled:
        await db.execute(
            """update proposal_documents
               set draft_status = 'idle', draft_error = '', updated_at = $2
               where id = $1""", doc_id, now_utc())
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower() or "invalid x-api-key" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        if job_id:
            await ai_jobs.fail(job_id, msg)
        await db.execute(
            """update proposal_documents
               set draft_status = 'error', draft_error = $2, updated_at = $3
               where id = $1""",
            doc_id, msg[:900], now_utc())


@router.post("/{orgId}/opportunities/{oppId}/proposal/documents/{docId}/draft")
async def draft_document(oppId: str, docId: str, body: DraftIn,
                         ctx: dict = Depends(require_role("editor"))):
    await assert_full_tier(ctx["user"])
    opp = await _get_opp(ctx["org_id"], oppId)
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not opp or not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    doc = await _get_doc(proposal["id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("draft_status") == "drafting":
        raise HTTPException(status_code=409, detail="Draft already in progress")
    ENGINES = {"claude": "anthropic", "openai": "openai",
               "emergent": "emergent", "asksage": "asksage"}
    engine = body.engine if body.engine in ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="proposal.draft")
    if not keys.get(ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    await db.execute(
        """update proposal_documents
           set draft_status = 'drafting', draft_error = '', updated_at = $2
           where id = $1""",
        doc["id"], now_utc())
    profile = await db.fetchrow(
        "select * from org_profiles where organization_id = $1", ctx["org_id"])
    cap_content = await _cap_content(ctx["org_id"], opp["id"])
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "proposal.draft",
                                  ref_id=str(doc["id"]), engine=engine,
                                  model=body.model, effort=body.effort)
    asyncio.create_task(_run_draft(
        doc["id"], engine, keys, serialize(ctx["org"]),
        serialize(profile), serialize(opp), cap_content, ctx["user"], ctx["org_id"],
        model=body.model, effort=body.effort, job_id=job_id))
    return {"ok": True, "status": "drafting", "documentId": str(doc["id"]),
            "jobId": str(job_id)}


class DocUpdate(BaseModel):
    contentMd: Optional[str] = None
    contentJson: Optional[Dict[str, Any]] = None
    title: Optional[str] = None


@router.put("/{orgId}/opportunities/{oppId}/proposal/documents/{docId}")
async def update_document(oppId: str, docId: str, body: DocUpdate,
                          ctx: dict = Depends(require_role("editor"))):
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    doc = await _get_doc(proposal["id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("draft_status") == "drafting":
        raise HTTPException(status_code=409, detail="Draft in progress — wait for it to finish")
    fresh = await db.fetchrow(
        """update proposal_documents
           set content_md = coalesce($2, content_md),
               content_json = coalesce($3, content_json),
               title = coalesce($4, title),
               status = 'edited', updated_by = $5, updated_at = $6
           where id = $1 returning *""",
        doc["id"], body.contentMd, body.contentJson, body.title,
        as_uuid(ctx["user"]["id"]), now_utc())
    await db.execute("update proposals set updated_at = $2 where id = $1",
                     proposal["id"], now_utc())
    return serialize(fresh)


@router.post("/{orgId}/opportunities/{oppId}/proposal/documents/{docId}/finalize")
async def finalize_document(oppId: str, docId: str,
                            ctx: dict = Depends(require_role("editor"))):
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    doc = await _get_doc(proposal["id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") == "empty":
        raise HTTPException(status_code=400, detail="Draft the document before finalizing")
    fresh = await db.fetchrow(
        """update proposal_documents set status = 'final', updated_by = $2, updated_at = $3
           where id = $1 returning *""",
        doc["id"], as_uuid(ctx["user"]["id"]), now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "proposal.finalize_doc", doc["title"])
    return serialize(fresh)


def _doc_bytes(doc, opp, org_name):
    fmt = doc.get("fmt")
    if fmt == "docx":
        return exports.narrative_docx(doc["title"], doc.get("content_md") or "", opp)
    if fmt == "xlsx":
        return exports.cost_volume_xlsx(doc.get("content_json") or {}, opp, org_name)
    if fmt == "pptx":
        return exports.briefing_pptx(doc.get("content_json") or {}, opp, org_name)
    raise ValueError(f"Unknown format: {fmt}")


@router.get("/{orgId}/opportunities/{oppId}/proposal/documents/{docId}/download")
async def download_document(oppId: str, docId: str,
                            ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not opp or not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    doc = await _get_doc(proposal["id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") == "empty":
        raise HTTPException(status_code=400, detail="Nothing to download — draft it first")
    opp_s = serialize(opp)
    data = _doc_bytes(doc, opp_s, ctx["org"]["name"])
    filename = exports.safe_filename(
        f"{doc['sort_order']:02d}_{doc['title']}_{opp_s.get('solNumber') or ''}",
        doc["fmt"])
    return Response(content=data, media_type=MEDIA_TYPES[doc["fmt"]],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{orgId}/opportunities/{oppId}/proposal/download-zip")
async def download_package(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not opp or not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    opp_s = serialize(opp)
    files = []

    cap = await db.fetchrow(
        """select content, rendering_png from capabilities
           where opportunity_id = $1 and organization_id = $2""",
        opp["id"], ctx["org_id"])
    if cap and (cap.get("content") or {}).get("title"):
        png = bytes(cap["rendering_png"]) if cap.get("rendering_png") else None
        files.append((
            exports.safe_filename("00_Proposed_Capability", "docx"),
            exports.capability_docx(cap["content"], opp_s, ctx["org"]["name"], png)))

    for doc in await _docs(proposal["id"]):
        if doc.get("status") == "empty":
            continue
        files.append((
            exports.safe_filename(f"{doc['sort_order']:02d}_{doc['title']}", doc["fmt"]),
            _doc_bytes(doc, opp_s, ctx["org"]["name"])))

    if not files:
        raise HTTPException(status_code=400,
            detail="No drafted documents yet — draft at least one volume first")
    data = exports.package_zip(files)
    filename = exports.safe_filename(
        f"Proposal_Package_{opp_s.get('solNumber') or opp_s.get('title', '')}", "zip")
    await write_audit(ctx["org_id"], ctx["user"], "proposal.download_zip",
                      opp_s.get("title"), {"files": len(files)})
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/{orgId}/opportunities/{oppId}/proposal/submit")
async def submit_proposal(oppId: str, ctx: dict = Depends(require_perm("proposal.submit"))):
    """Admin-only: mark the proposal package as submitted to the government."""
    opp = await _get_opp(ctx["org_id"], oppId)
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not opp or not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.get("status") == "submitted":
        raise HTTPException(status_code=400, detail="This proposal is already marked submitted")
    await db.execute(
        """update proposals set status = 'submitted', submitted_at = $2, submitted_by = $3
           where id = $1""",
        proposal["id"], now_utc(), as_uuid(ctx["user"]["id"]))
    await db.execute(
        "update opportunities set stage = 'Submitted', updated_at = $2 where id = $1",
        opp["id"], now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "proposal.submit",
                      serialize(opp).get("title"))
    fresh = await _get_proposal(ctx["org_id"], oppId)
    return await _payload(fresh)


@router.get("/{orgId}/proposals")
async def list_proposals(ctx: dict = Depends(require_role("viewer"))):
    """Org-wide proposal hub: every package with its opportunity context."""
    rows = await db.fetch(
        """select p.id, p.status, p.submitted_at, p.evaluated_at, p.evaluation,
                  p.created_at, p.updated_at, p.opportunity_id,
                  o.title as opp_title, o.sol_number, o.agency, o.due_date, o.stage,
                  (select count(*) from proposal_documents d
                    where d.proposal_id = p.id and d.status <> 'empty') as drafted,
                  (select count(*) from proposal_documents d
                    where d.proposal_id = p.id) as total_docs
           from proposals p join opportunities o on o.id = p.opportunity_id
           where p.organization_id = $1
           order by p.updated_at desc""",
        ctx["org_id"])
    out = []
    for r in rows:
        e = serialize(r)
        ev = e.pop("evaluation", None) or {}
        e["overallScore"] = ev.get("overallScore")
        e["colorReview"] = ev.get("colorReview")
        out.append(e)
    return out


@router.post("/{orgId}/opportunities/{oppId}/proposal/evaluate")
async def evaluate_proposal(oppId: str, body: DraftIn,
                            ctx: dict = Depends(require_role("editor"))):
    """AI color-team evaluation — runs once EVERY volume is drafted (the AI
    evaluates the package; the user never grades their own proposal)."""
    await assert_full_tier(ctx["user"])
    opp = await _get_opp(ctx["org_id"], oppId)
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not opp or not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    all_docs = await _docs(proposal["id"])
    empty = [d["title"] for d in all_docs if d.get("status") == "empty"]
    if empty:
        raise HTTPException(status_code=400,
            detail="Finish every volume before evaluating — still empty: "
                   + ", ".join(empty))
    docs = list(all_docs)
    ENGINES = {"claude": "anthropic", "openai": "openai",
               "emergent": "emergent", "asksage": "asksage"}
    engine = body.engine if body.engine in ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="proposal.evaluate")
    if not keys.get(ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    profile = await db.fetchrow(
        "select * from org_profiles where organization_id = $1", ctx["org_id"])
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "proposal.evaluate",
                                  ref_id=str(proposal["id"]), engine=engine,
                                  model=body.model, effort=body.effort)

    async def _run_eval():
        try:
            evaluation = await proposal_ai.evaluate_package(
                engine, keys, serialize(ctx["org"]), serialize(profile),
                serialize(opp), docs, model=body.model, effort=body.effort,
                job_id=job_id)
            await db.execute(
                "update proposals set evaluation = $2, evaluated_at = $3 where id = $1",
                proposal["id"], evaluation, now_utc())
            await ai_jobs.finish(job_id, "Evaluation ready")
            await write_audit(ctx["org_id"], ctx["user"], "proposal.evaluate",
                              serialize(opp).get("title"),
                              {"score": evaluation.get("overallScore"),
                               "color": evaluation.get("colorReview")})
        except ai_jobs.JobCancelled:
            pass
        except Exception as e:  # noqa: BLE001
            await ai_jobs.fail(job_id, str(e))

    asyncio.create_task(_run_eval())
    return {"ok": True, "status": "evaluating", "jobId": str(job_id)}


class CustomerIn(BaseModel):
    commercialMarket: str = ""
    sector: str = ""            # Civil | Defense | Intelligence Community
    branch: str = ""            # service branch / agency group (defense & IC)
    agency: str = ""            # civil or IC agency
    peo: str = ""               # program executive office
    tpoc: str = ""              # technical point of contact
    contractingOfficer: str = ""


@router.put("/{orgId}/opportunities/{oppId}/proposal/customer")
async def set_customer(oppId: str, body: CustomerIn,
                       ctx: dict = Depends(require_role("editor"))):
    """Who this proposal serves: the commercial market and the government
    customer down to the PEO, TPOC, and contracting officer."""
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    for f in ("commercialMarket", "sector", "branch", "agency", "peo",
              "tpoc", "contractingOfficer"):
        if len(getattr(body, f)) > 300:
            raise HTTPException(status_code=400, detail=f"{f} is too long")
    existing = proposal.get("customer") or {}
    customer = {**existing, **body.model_dump()}
    # editing the target invalidates a previous currency check
    if any(existing.get(k) != customer.get(k) for k in ("sector", "branch", "peo")):
        customer.pop("aiCheck", None)
    await db.execute("update proposals set customer = $2 where id = $1",
                     proposal["id"], customer)
    await write_audit(ctx["org_id"], ctx["user"], "proposal.customer",
                      customer.get("peo") or customer.get("agency") or "",
                      {"sector": customer.get("sector")})
    return await _payload(await _get_proposal(ctx["org_id"], oppId))


PEO_CHECK_SYSTEM = (
    "You verify US government acquisition-organization facts against CURRENT "
    "public sources using web_search: the service's own acquisition pages, "
    "the Stanford Gordian Knot Center PEO Directory "
    "(gordianknot.fsi.stanford.edu), and the LookLeft DoW/DoD PEO tracker "
    "(sites.google.com/lookleft.com/index/home) which publishes rolling "
    "updates faster than the annual directories. Never guess — verify. "
    "Respond with a SINGLE JSON object ONLY."
)


@router.post("/{orgId}/opportunities/{oppId}/proposal/customer/suggest")
async def suggest_customer(oppId: str, body: DraftIn,
                           ctx: dict = Depends(require_role("editor"))):
    """AI reads the solicitation text and suggests the customer fields
    (sector, branch, PEO, agency, TPOC, contracting officer). For DoW
    solicitations the model also cross-references the Stanford Gordian Knot
    2026 PEO Directory + the LookLeft rolling tracker so PEO renames /
    reorganizations don't leak into a stale suggestion. Returns the
    suggestion synchronously — the frontend uses it to pre-fill the form.
    The human still reviews + edits + hits Save; nothing is persisted
    server-side here."""
    await assert_full_tier(ctx["user"])
    opp = await _get_opp(ctx["org_id"], oppId)
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"],
                                   purpose="proposal.customer_suggest")
    ENGINES = {"claude": "anthropic", "openai": "openai",
               "emergent": "emergent", "asksage": "asksage"}
    engine = body.engine if body.engine in ENGINES else "claude"
    if not keys.get(ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    solicitation = (
        f"TITLE: {opp.get('title') or ''}\n"
        f"AGENCY: {opp.get('agency') or ''}\n"
        f"SOL NUMBER: {opp.get('solNumber') or ''}\n"
        f"NAICS: {opp.get('naics') or ''}\n"
        f"SET-ASIDE: {opp.get('setAside') or ''}\n"
        f"SOURCE URL: {opp.get('sourceUrl') or ''}\n\n"
        f"DESCRIPTION:\n{(opp.get('description') or '')[:6000]}\n\n"
        f"POINTS OF CONTACT (if any parsed):\n{opp.get('pocs') or []}"
    )
    prompt = (
        "Read the solicitation below and identify the government customer.\n"
        "1) sector: one of 'Defense', 'Intelligence Community', 'Civil'\n"
        "2) branch (Defense only): one of 'Army', 'Navy', 'Marine Corps', "
        "'Air Force', 'Space Force', 'DoD 4th Estate' (OSD, DARPA, DIU, MDA, "
        "DLA, DTRA, etc.)\n"
        "3) peo (Defense only): the specific Program Executive Office name — "
        "cross-check against the Stanford Gordian Knot 2026 PEO Directory + "
        "LookLeft's rolling tracker so renames/reorgs are current\n"
        "4) agency (IC/Civil only): the specific agency name\n"
        "5) tpoc: technical point of contact 'Name · office · email' as best "
        "inferred from the solicitation; leave blank if not stated\n"
        "6) contractingOfficer: 'Name · office · email' from the solicitation; "
        "leave blank if not stated\n"
        "7) confidence: 'high' | 'medium' | 'low' — how confident the inference is\n"
        "8) rationale: 1-2 sentences on how you concluded this\n\n"
        f"SOLICITATION:\n{solicitation}\n\n"
        "Respond with a SINGLE JSON object with those exact keys and nothing else."
    )
    text, used_model, _usage = await genai.generate(
        engine, keys, PEO_CHECK_SYSTEM, prompt,
        max_tokens=1500, web_search=True, model=body.model)
    data = genai.extract_json(text)
    if not isinstance(data, dict):
        raise HTTPException(status_code=502,
            detail="The AI returned an unparseable suggestion. Try again.")
    allowed = {"sector", "branch", "peo", "agency", "tpoc",
               "contractingOfficer", "confidence", "rationale"}
    suggestion = {k: (str(data.get(k) or "")[:400]) for k in allowed}
    suggestion["directorySource"] = (
        "Cross-checked against Stanford Gordian Knot 2026 PEO Directory + "
        "LookLeft DoW/DoD PEO tracker (sites.google.com/lookleft.com/index/home)")
    suggestion["suggestedAt"] = now_utc().isoformat()
    suggestion["model"] = used_model
    return suggestion


@router.post("/{orgId}/opportunities/{oppId}/proposal/customer/check")
async def check_customer(oppId: str, body: DraftIn,
                         ctx: dict = Depends(require_role("editor"))):
    """AI currency check: does the selected PEO still exist under this branch
    per the latest directory and service pages? Stores customer.aiCheck."""
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    customer = proposal.get("customer") or {}
    target = customer.get("peo") or customer.get("agency")
    if not target:
        raise HTTPException(status_code=400,
            detail="Pick the government customer (PEO or agency) first.")
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="proposal.peo_check")
    ENGINES = {"claude": "anthropic", "openai": "openai",
               "emergent": "emergent", "asksage": "asksage"}
    engine = body.engine if body.engine in ENGINES else "claude"
    if not keys.get(ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "peo.check",
                                  ref_id=str(proposal["id"]), engine=engine,
                                  model=body.model, effort=body.effort)
    prompt = (
        f"ORGANIZATION TO VERIFY: {target}\n"
        f"CLAIMED PARENT: {customer.get('branch') or customer.get('sector') or 'n/a'}\n\n"
        "Use web_search to verify whether this organization currently exists "
        "under that parent as named. Check three sources in order of freshness: "
        "(1) LookLeft's rolling DoW/DoD PEO tracker at "
        "sites.google.com/lookleft.com/index/home (updates faster than annual "
        "directories), (2) the Stanford Gordian Knot 2026 PEO Directory, "
        "(3) the service's own acquisition pages. Consider renames, mergers, "
        "and reorganizations. Return JSON:\n"
        '{ "upToDate": true|false, "note": "1-2 sentences: current status, and '
        'the current name/successor if it changed", '
        '"source": "url you verified against" }'
    )

    async def _run_check():
        try:
            await ai_jobs.stage(job_id, "Checking the PEO directory and service pages…", 30)
            text, used_model, usage = await genai.generate(
                engine, keys, PEO_CHECK_SYSTEM, prompt,
                max_tokens=1500, web_search=True, model=body.model)
            await ai_jobs.add_usage(job_id, used_model, usage)
            data = genai.extract_json(text)
            if data is None or "upToDate" not in data:
                raise ValueError("The AI returned an unparseable check. Try again.")
            check = {"upToDate": bool(data.get("upToDate")),
                     "note": str(data.get("note") or "")[:600],
                     "source": str(data.get("source") or "")[:300],
                     "checkedAt": now_utc().isoformat(), "model": used_model}
            fresh = await _get_proposal(ctx["org_id"], oppId)
            cust = (fresh.get("customer") or {})
            cust["aiCheck"] = check
            await db.execute("update proposals set customer = $2 where id = $1",
                             fresh["id"], cust)
            await ai_jobs.finish(
                job_id, "Directory entry is current" if check["upToDate"]
                else "Directory entry looks outdated")
        except ai_jobs.JobCancelled:
            pass
        except Exception as e:  # noqa: BLE001
            await ai_jobs.fail(job_id, str(e))

    asyncio.create_task(_run_check())
    return {"ok": True, "status": "checking", "jobId": str(job_id)}



# ---------------- Overleaf integration (see backend/overleaf.py) -----------------

import overleaf  # noqa: E402  (kept local to this router)


async def _get_proposal_by_id(org_id, proposal_id):
    """Fetch a proposal by its own id (not by opportunity id), still scoped
    to the caller's org so nothing cross-org leaks."""
    row = await db.fetchrow(
        "select * from proposals where id = $1 and organization_id = $2",
        as_uuid(proposal_id), org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return row


class OverleafLinkIn(BaseModel):
    projectIdOrUrl: str  # accepts full URL or bare project id


@router.post("/{orgId}/proposals/{proposalId}/overleaf/link")
async def overleaf_link(proposalId: str, body: OverleafLinkIn,
                        ctx: dict = Depends(require_role("editor"))):
    """Attach this proposal to an Overleaf project. Doesn't push anything yet.
    Accepts either the bare project id or the full URL from the user's
    browser address bar on overleaf.com."""
    await _get_proposal_by_id(ctx["org_id"], proposalId)
    try:
        project_id = await overleaf.link_proposal(
            proposal_id=proposalId, project_id_or_url=body.projectIdOrUrl)
    except overleaf.OverleafError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await write_audit(ctx["org_id"], ctx["user"], "proposal.overleaf.link",
                      proposalId, {"projectId": project_id})
    return {"ok": True, "overleafProjectId": project_id}


@router.post("/{orgId}/proposals/{proposalId}/overleaf/unlink")
async def overleaf_unlink(proposalId: str,
                          ctx: dict = Depends(require_role("editor"))):
    await _get_proposal_by_id(ctx["org_id"], proposalId)
    await overleaf.unlink_proposal(proposal_id=proposalId)
    await write_audit(ctx["org_id"], ctx["user"], "proposal.overleaf.unlink", proposalId)
    return {"ok": True}


async def _overleaf_ready(ctx, proposalId: str):
    """Look up the org's Overleaf token and the proposal's linked project id.
    Returns (token, project_id) or raises the appropriate 400."""
    prop = await _get_proposal_by_id(ctx["org_id"], proposalId)
    project_id = (prop.get("overleaf_project_id") or "").strip()
    if not project_id:
        raise HTTPException(status_code=400, detail=(
            "This proposal isn't linked to an Overleaf project yet. Paste the "
            "Overleaf project URL or id in the Overleaf panel and save first."))
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"],
                                   purpose="proposal.overleaf.sync")
    token = keys.get("overleaf") or ""
    if not token:
        raise HTTPException(status_code=400, detail=(
            "No Overleaf auth token set for this org. Generate one at "
            "overleaf.com → Account → Git Integration and save it in Settings → "
            "API Keys → Overleaf."))
    return token, project_id, prop


@router.post("/{orgId}/proposals/{proposalId}/overleaf/push")
async def overleaf_push(proposalId: str,
                        ctx: dict = Depends(require_role("editor"))):
    """Push every proposal volume to the linked Overleaf project as one .md file
    per volume plus a `main.tex` wrapper. Idempotent: if nothing changed since
    the last push we still return 200 and note noChanges=true."""
    token, project_id, _prop = await _overleaf_ready(ctx, proposalId)
    try:
        result = await overleaf.push_proposal(
            org_id=ctx["org_id"], proposal_id=proposalId,
            token=token, project_id=project_id)
    except overleaf.OverleafError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if not result.get("noChanges"):
        await overleaf.mark_synced(proposal_id=proposalId)
    await write_audit(ctx["org_id"], ctx["user"], "proposal.overleaf.push",
                      proposalId, {"files": result.get("filesWritten", 0)})
    return {"ok": True, **result}


@router.post("/{orgId}/proposals/{proposalId}/overleaf/pull")
async def overleaf_pull(proposalId: str,
                        ctx: dict = Depends(require_role("editor"))):
    """Pull the latest Overleaf revision back into every matching volume."""
    token, project_id, _prop = await _overleaf_ready(ctx, proposalId)
    try:
        result = await overleaf.pull_proposal(
            org_id=ctx["org_id"], proposal_id=proposalId,
            token=token, project_id=project_id)
    except overleaf.OverleafError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if result.get("updated"):
        await overleaf.mark_synced(proposal_id=proposalId)
    await write_audit(ctx["org_id"], ctx["user"], "proposal.overleaf.pull",
                      proposalId, {"updated": len(result.get("updated", []))})
    return {"ok": True, **result}
