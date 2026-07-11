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
import ai_jobs
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
    model: str = ""
    effort: str = "standard"


async def _run_draft(doc_id, engine, keys, org, profile, kind, target, notes,
                     user, org_id, model="", effort="", job_id=None):
    try:
        md, data, used_model = await venture_ai.draft(
            engine, keys, kind, org, profile, target, notes,
            model=model, effort=effort, job_id=job_id)
        if job_id:
            await ai_jobs.stage(job_id, "Saving the draft…", 95)
        await db.execute(
            """update venture_docs
               set content_md = $2, content_json = $3, draft_status = 'idle',
                   draft_error = '', model = $4, updated_at = $5
               where id = $1""",
            doc_id, md, data, used_model, now_utc())
        if job_id:
            await ai_jobs.finish(job_id, "Draft ready")
        await write_audit(org_id, user, "venture.draft", kind,
                          {"engine": engine, "model": used_model})
    except ai_jobs.JobCancelled:
        await db.execute(
            """update venture_docs set draft_status = 'idle', draft_error = '',
               updated_at = $2 where id = $1""", doc_id, now_utc())
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        if job_id:
            await ai_jobs.fail(job_id, msg)
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
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "venture.draft",
                                  ref_id=str(doc["id"]), engine=engine,
                                  model=body.model, effort=body.effort)
    asyncio.create_task(_run_draft(
        doc["id"], engine, keys, serialize(ctx["org"]), serialize(profile),
        doc["kind"], doc.get("target", ""), body.notes,
        ctx["user"], ctx["org_id"], model=body.model, effort=body.effort,
        job_id=job_id))
    return {"ok": True, "status": "drafting", "jobId": str(job_id)}


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


class FromProgramIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    url: str = Field(default="", max_length=500)
    model: str = ""


@router.post("/{orgId}/venture-docs/from-program")
async def create_from_program(body: FromProgramIn,
                              ctx: dict = Depends(require_role("editor"))):
    """Start an accelerator application from a program's own page: fetch the
    URL, AI-extract its real questions + tips, scaffold the answers."""
    import httpx
    page_text = ""
    if body.url:
        if not body.url.lower().startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="URL must start with http(s)://")
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                r = await client.get(body.url, headers={"User-Agent": "CaptureAgent/1.0"})
                if r.status_code < 400:
                    import re as _re
                    page_text = _re.sub(r"<[^>]+>", " ", r.text)
                    page_text = _re.sub(r"\s+", " ", page_text)[:40000]
        except Exception:  # noqa: BLE001 — page fetch is best-effort
            page_text = ""
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="venture.from_program")
    profile = await db.fetchrow(
        "select * from org_profiles where organization_id = $1", ctx["org_id"])
    md, model_used = await venture_ai.form_from_program(
        keys.get("anthropic", ""), body.name.strip(), page_text,
        serialize(ctx["org"]), serialize(profile), model=body.model)
    row = await db.fetchrow(
        """insert into venture_docs (organization_id, kind, target, title,
                                     content_md, model, created_by)
           values ($1, 'accelerator_application', $2, $3, $4, $5, $6) returning *""",
        ctx["org_id"], body.name.strip(),
        f"Accelerator application — {body.name.strip()}", md, model_used,
        as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "venture.from_program",
                      body.name.strip(), {"hadPage": bool(page_text),
                                          "tailored": bool(model_used)})
    return serialize(row)
