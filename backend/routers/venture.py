"""Venture workspace: AI-drafted investor emails, pitch decks, business plans,
financial models, and accelerator applications — with Office exports."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

import database as db
from utils import now_utc, serialize, as_uuid
from rbac import require_role
from domain import write_audit
import venture_ai
import genai
import exports
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["venture"])

MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
ENGINES = {"claude": "anthropic", "openai": "openai",
           "emergent": "emergent", "asksage": "asksage"}


async def _get_doc(org_id, doc_id):
    did = as_uuid(doc_id)
    if did is None:
        return None
    return await db.fetchrow(
        "select * from venture_docs where id = $1 and organization_id = $2",
        did, org_id)


class DocIn(BaseModel):
    kind: str
    target: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=240)
    notes: str = Field(default="", max_length=2000)


@router.get("/{orgId}/venture-docs")
async def list_docs(kind: Optional[str] = None,
                    ctx: dict = Depends(require_role("viewer"))):
    if kind:
        rows = await db.fetch(
            """select * from venture_docs
               where organization_id = $1 and kind = $2 order by updated_at desc""",
            ctx["org_id"], kind)
    else:
        rows = await db.fetch(
            "select * from venture_docs where organization_id = $1 order by updated_at desc",
            ctx["org_id"])
    return [serialize(r) for r in rows]


@router.post("/{orgId}/venture-docs")
async def create_doc(body: DocIn, ctx: dict = Depends(require_role("editor"))):
    if body.kind not in venture_ai.KINDS:
        raise HTTPException(status_code=400, detail="Unknown document kind")
    meta = venture_ai.KINDS[body.kind]
    title = body.title.strip() or (
        f"{meta['title']}{' — ' + body.target.strip() if body.target.strip() else ''}")
    row = await db.fetchrow(
        """insert into venture_docs (organization_id, kind, target, title, created_by)
           values ($1, $2, $3, $4, $5) returning *""",
        ctx["org_id"], body.kind, body.target.strip(), title,
        as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "venture.create", title,
                      {"kind": body.kind})
    return serialize(row)


class DraftIn(BaseModel):
    engine: str = "claude"
    notes: str = Field(default="", max_length=2000)


async def _run_draft(doc_id, engine, keys, org, profile, kind, target, notes,
                     user, org_id):
    try:
        md, data, model = await venture_ai.draft(
            engine, keys, kind, org, profile, target, notes)
        await db.execute(
            """update venture_docs
               set content_md = $2, content_json = $3, draft_status = 'idle',
                   draft_error = '', model = $4, updated_at = $5
               where id = $1""",
            doc_id, md, data, model, now_utc())
        await write_audit(org_id, user, "venture.draft", kind,
                          {"engine": engine, "model": model})
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        await db.execute(
            """update venture_docs
               set draft_status = 'error', draft_error = $2, updated_at = $3
               where id = $1""",
            doc_id, msg[:900], now_utc())


@router.post("/{orgId}/venture-docs/{docId}/draft")
async def draft_doc(docId: str, body: DraftIn,
                    ctx: dict = Depends(require_role("editor"))):
    doc = await _get_doc(ctx["org_id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("draft_status") == "drafting":
        raise HTTPException(status_code=409, detail="Draft already in progress")
    engine = body.engine if body.engine in ENGINES else "claude"
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="venture.draft")
    if not keys.get(ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. "
                   "Add it in Settings → API Keys.")
    await db.execute(
        """update venture_docs set draft_status = 'drafting', draft_error = '',
           updated_at = $2 where id = $1""",
        doc["id"], now_utc())
    profile = await db.fetchrow(
        "select * from org_profiles where organization_id = $1", ctx["org_id"])
    asyncio.create_task(_run_draft(
        doc["id"], engine, keys, serialize(ctx["org"]), serialize(profile),
        doc["kind"], doc.get("target", ""), body.notes,
        ctx["user"], ctx["org_id"]))
    return {"ok": True, "status": "drafting"}


class DocUpdate(BaseModel):
    contentMd: Optional[str] = None
    contentJson: Optional[Dict[str, Any]] = None
    title: Optional[str] = None
    target: Optional[str] = None
    status: Optional[str] = None


@router.put("/{orgId}/venture-docs/{docId}")
async def update_doc(docId: str, body: DocUpdate,
                     ctx: dict = Depends(require_role("editor"))):
    doc = await _get_doc(ctx["org_id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    md = body.contentMd if body.contentMd is not None else doc["content_md"]
    cj = body.contentJson if body.contentJson is not None else doc["content_json"]
    title = body.title if body.title is not None else doc["title"]
    target = body.target if body.target is not None else doc["target"]
    status = body.status if body.status in ("draft", "final") else doc["status"]
    row = await db.fetchrow(
        """update venture_docs
           set content_md = $2, content_json = $3, title = $4, target = $5,
               status = $6, updated_at = $7
           where id = $1 returning *""",
        doc["id"], md, cj, title, target, status, now_utc())
    return serialize(row)


@router.delete("/{orgId}/venture-docs/{docId}")
async def delete_doc(docId: str, ctx: dict = Depends(require_role("editor"))):
    doc = await _get_doc(ctx["org_id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.execute("delete from venture_docs where id = $1", doc["id"])
    await write_audit(ctx["org_id"], ctx["user"], "venture.delete", doc.get("title"))
    return {"ok": True}


@router.get("/{orgId}/venture-docs/{docId}/download")
async def download_doc(docId: str, ctx: dict = Depends(require_role("viewer"))):
    doc = await _get_doc(ctx["org_id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not (doc.get("content_md") or (doc.get("content_json") or {})):
        raise HTTPException(status_code=400, detail="Nothing drafted yet")
    fmt = venture_ai.KINDS[doc["kind"]]["fmt"]
    stub_opp = {"title": doc.get("target") or doc.get("title"), "solNumber": ""}
    org_name = ctx["org"]["name"]
    if fmt == "docx":
        data = exports.narrative_docx(doc["title"], doc.get("content_md") or "", stub_opp)
    elif fmt == "xlsx":
        data = exports.cost_volume_xlsx(doc.get("content_json") or {}, stub_opp, org_name)
    else:
        data = exports.briefing_pptx(doc.get("content_json") or {}, stub_opp, org_name)
    filename = exports.safe_filename(doc["title"], fmt)
    await write_audit(ctx["org_id"], ctx["user"], "venture.download", doc.get("title"))
    return Response(content=data, media_type=MEDIA_TYPES[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
