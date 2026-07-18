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
from routers import files as files_router

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


_SCAN_KIND_MAP = {"accelerator_scan": "accelerator", "investor_scan": "investor"}


def _extract_discovered_block(md: str):
    """Pull the trailing ```json { "discovered": [...] } ``` block from a scan
    result and strip it out of the markdown. Returns (list_of_items, cleaned_md).
    Silent on parse errors — discovery persistence is best-effort."""
    import re, json as _json
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```\s*$", md or "", re.MULTILINE)
    if not m:
        return [], md
    try:
        parsed = _json.loads(m.group(1))
        items = parsed.get("discovered") if isinstance(parsed, dict) else None
        if not isinstance(items, list):
            return [], md
        cleaned = (md[:m.start()] + md[m.end():]).rstrip() + "\n"
        return items, cleaned
    except Exception:
        return [], md


async def _persist_discovered(org_id, doc_id, kind_key, items):
    """Upsert discovered accelerator/investor programs so they show up as extra
    rows on the venture pages alongside the curated seed lists."""
    if not items or kind_key not in _SCAN_KIND_MAP:
        return 0
    dv_kind = _SCAN_KIND_MAP[kind_key]
    saved = 0
    for it in items:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        # Drop `name` from payload to avoid duplication; keep everything else.
        payload = {k: v for k, v in it.items() if k != "name"}
        await db.execute(
            """insert into discovered_venture
                   (organization_id, kind, name, data, source_doc_id)
               values ($1, $2, $3, $4, $5)
               on conflict (organization_id, kind, name) do update
                   set data          = excluded.data,
                       source_doc_id = excluded.source_doc_id,
                       discovered_at = now()""",
            as_uuid(org_id), dv_kind, name, payload,
            as_uuid(doc_id) if doc_id else None)
        saved += 1
    return saved


async def _run_draft(doc_id, engine, keys, org, profile, kind, target, notes,
                     user, org_id, model="", effort="", job_id=None,
                     files_context=""):
    try:
        md, data, used_model = await venture_ai.draft(
            engine, keys, kind, org, profile, target, notes,
            model=model, effort=effort, job_id=job_id,
            files_context=files_context)
        if job_id:
            await ai_jobs.stage(job_id, "Saving the draft…", 95)
        discovered_items, md = _extract_discovered_block(md)
        await db.execute(
            """update venture_docs
               set content_md = $2, content_json = $3, draft_status = 'idle',
                   draft_error = '', model = $4, updated_at = $5
               where id = $1""",
            doc_id, md, data, used_model, now_utc())
        saved = await _persist_discovered(org_id, doc_id, kind, discovered_items)
        if job_id:
            note = f"Draft ready · indexed {saved} program(s)" if saved else "Draft ready"
            await ai_jobs.finish(job_id, note)
        await write_audit(org_id, user, "venture.draft", kind,
                          {"engine": engine, "model": used_model,
                           "indexed": saved})
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
    files_context = await files_router.gather_org_file_context(
        ctx["org_id"], entity_type="venture_doc", entity_id=str(doc["id"]))
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "venture.draft",
                                  ref_id=str(doc["id"]), engine=engine,
                                  model=body.model, effort=body.effort)
    asyncio.create_task(_run_draft(
        doc["id"], engine, keys, serialize(ctx["org"]), serialize(profile),
        doc["kind"], doc.get("target", ""), body.notes,
        ctx["user"], ctx["org_id"], model=body.model, effort=body.effort,
        job_id=job_id, files_context=files_context))
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


@router.post("/{orgId}/venture-docs/{docId}/redraft-form")
async def redraft_accelerator_form(docId: str,
                                   ctx: dict = Depends(require_role("editor"))):
    """Regenerate the fillable-form schema for an existing accelerator
    application. Preserves any answers the founder already entered by mapping
    them across on question `id`; new questions the AI picks up appear with
    their AI-drafted answers, and questions no longer relevant are dropped."""
    doc = await _get_doc(ctx["org_id"], docId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("kind") != "accelerator_application":
        raise HTTPException(status_code=400,
            detail="This document is not an accelerator application.")
    prev = (doc.get("content_json") or {})
    prev_answers = {q.get("id"): q.get("answer", "")
                    for q in (prev.get("questions") or [])}

    # Prefer the target/name we already stored — the program page has moved on
    # from the initial URL and we don't keep the URL in venture_docs. Users can
    # always paste fresh page text via a redraft via `notes` if needed.
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"],
                                   purpose="venture.redraft_form")
    profile = await db.fetchrow(
        "select * from org_profiles where organization_id = $1", ctx["org_id"])
    files_context = await files_router.gather_org_file_context(
        ctx["org_id"], entity_type="venture_doc", entity_id=str(doc["id"]))
    md, schema, model_used = await venture_ai.form_from_program(
        keys.get("anthropic", ""), doc["target"] or doc["title"], "",
        serialize(ctx["org"]), serialize(profile), model="",
        files_context=files_context)
    # Merge previous answers onto matching new questions so the founder's edits
    # survive the redraft. AI answers stay on any brand-new questions.
    for q in schema.get("questions", []):
        if q["id"] in prev_answers and prev_answers[q["id"]]:
            q["answer"] = prev_answers[q["id"]]
    row = await db.fetchrow(
        """update venture_docs
             set content_md = $2, content_json = $3, model = $4, updated_at = $5
             where id = $1 returning *""",
        doc["id"], md, schema, model_used or doc.get("model", ""), now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "venture.redraft_form",
                      doc.get("title"), {"model": model_used})
    return serialize(row)



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
    files_context = await files_router.gather_org_file_context(ctx["org_id"])
    md, schema, model_used = await venture_ai.form_from_program(
        keys.get("anthropic", ""), body.name.strip(), page_text,
        serialize(ctx["org"]), serialize(profile), model=body.model,
        files_context=files_context)
    row = await db.fetchrow(
        """insert into venture_docs (organization_id, kind, target, title,
                                     content_md, content_json, model, created_by)
           values ($1, 'accelerator_application', $2, $3, $4, $5, $6, $7)
           returning *""",
        ctx["org_id"], body.name.strip(),
        f"Accelerator application — {body.name.strip()}", md, schema, model_used,
        as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "venture.from_program",
                      body.name.strip(), {"hadPage": bool(page_text),
                                          "tailored": bool(model_used)})
    return serialize(row)


# --------- Discovered programs (from AI scans) — merged with curated lists ---------
_DISCOVERED_KINDS = {"accelerator", "investor"}


@router.get("/{orgId}/venture/discovered/{kind}")
async def list_discovered(kind: str,
                          ctx: dict = Depends(require_role("viewer"))):
    """Return venture programs the AI scan discovered for this org, most recent
    first. Frontend merges these with the curated seed list for display."""
    if kind not in _DISCOVERED_KINDS:
        raise HTTPException(status_code=400, detail="Invalid kind")
    rows = await db.fetch(
        """select id, name, data, source_doc_id, discovered_at
             from discovered_venture
             where organization_id = $1 and kind = $2
             order by discovered_at desc
             limit 200""",
        as_uuid(ctx["org_id"]), kind)
    return [{
        "id": str(r["id"]),
        "name": r["name"],
        "discoveredAt": r["discovered_at"].isoformat() if r["discovered_at"] else None,
        "sourceDocId": str(r["source_doc_id"]) if r["source_doc_id"] else None,
        **(r["data"] or {}),
    } for r in rows]


@router.delete("/{orgId}/venture/discovered/{kind}/{itemId}")
async def delete_discovered(kind: str, itemId: str,
                            ctx: dict = Depends(require_role("editor"))):
    """Remove a discovered program from the merged list (e.g. duplicate of a
    curated entry or a bad AI pick)."""
    if kind not in _DISCOVERED_KINDS:
        raise HTTPException(status_code=400, detail="Invalid kind")
    await db.execute(
        """delete from discovered_venture
             where id = $1 and organization_id = $2 and kind = $3""",
        as_uuid(itemId), as_uuid(ctx["org_id"]), kind)
    await write_audit(ctx["org_id"], ctx["user"], "venture.discovered.remove",
                      kind, {"id": itemId})
    return {"ok": True}
