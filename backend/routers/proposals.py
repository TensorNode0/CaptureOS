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
from domain import write_audit
import proposal_ai
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


async def _run_draft(doc_id, engine, keys,
                     org, profile, opp, cap_content, user, org_id):
    try:
        doc = await db.fetchrow("select * from proposal_documents where id = $1", doc_id)
        md, data, model = await proposal_ai.draft_document(
            engine, keys, doc["doc_type"],
            org, profile, opp, cap_content)
        await db.execute(
            """update proposal_documents
               set content_md = $2, content_json = $3, status = 'drafted',
                   draft_status = 'idle', draft_error = '', model = $4, updated_at = $5
               where id = $1""",
            doc_id, md, data, model, now_utc())
        await write_audit(org_id, user, "proposal.draft", doc["title"],
                          {"engine": engine, "model": model})
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower() or "invalid x-api-key" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        await db.execute(
            """update proposal_documents
               set draft_status = 'error', draft_error = $2, updated_at = $3
               where id = $1""",
            doc_id, msg[:900], now_utc())


@router.post("/{orgId}/opportunities/{oppId}/proposal/documents/{docId}/draft")
async def draft_document(oppId: str, docId: str, body: DraftIn,
                         ctx: dict = Depends(require_role("editor"))):
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
    asyncio.create_task(_run_draft(
        doc["id"], engine, keys, serialize(ctx["org"]),
        serialize(profile), serialize(opp), cap_content, ctx["user"], ctx["org_id"]))
    return {"ok": True, "status": "drafting", "documentId": str(doc["id"])}


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
    """AI color-team evaluation of the drafted package (SSEB-style)."""
    opp = await _get_opp(ctx["org_id"], oppId)
    proposal = await _get_proposal(ctx["org_id"], oppId)
    if not opp or not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    docs = [d for d in await _docs(proposal["id"]) if d.get("status") != "empty"]
    if not docs:
        raise HTTPException(status_code=400,
            detail="Nothing to evaluate yet — draft at least one volume first")
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
    try:
        evaluation = await proposal_ai.evaluate_package(
            engine, keys, serialize(ctx["org"]), serialize(profile),
            serialize(opp), docs)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    await db.execute(
        "update proposals set evaluation = $2, evaluated_at = $3 where id = $1",
        proposal["id"], evaluation, now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "proposal.evaluate",
                      serialize(opp).get("title"),
                      {"score": evaluation.get("overallScore"),
                       "color": evaluation.get("colorReview")})
    return evaluation
