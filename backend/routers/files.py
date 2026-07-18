"""Files & Media Storage endpoints.

Two use cases share this router:
  * ORG-level assets — 7 curated categories, feed AI at every prompt.
  * PER-ITEM attachments — bound to an opportunity/proposal/venture_doc.

Uploads go to Supabase Storage; DB rows track metadata + extracted text.
Downloads use short-lived signed URLs minted by the backend."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query

import database as db
from utils import serialize, as_uuid, now_utc
from rbac import require_role
from billing import assert_full_tier
from domain import write_audit
import files_storage as storage

router = APIRouter(prefix="/api/orgs", tags=["files"])

VALID_CATEGORIES = {
    "past_performance", "commercialization", "capability_statements",
    "quad_charts", "resumes", "letters_of_support", "pitch_decks",
}
VALID_ENTITY_TYPES = {"opportunity", "proposal", "venture_doc"}
MAX_BYTES = 25 * 1024 * 1024   # 25 MB per file — safe under most proxy limits


def _serialize_row(row) -> dict:
    """Serialize + drop the heavy `extracted_text` field from list views. The
    text is used server-side to feed AI prompts, not shipped to the browser."""
    d = serialize(dict(row))
    d.pop("extractedText", None)
    return d


@router.post("/{orgId}/files")
async def upload_file(
    orgId: str,
    file: UploadFile = File(...),
    category: str = Form(""),
    entityType: str = Form(""),
    entityId: Optional[str] = Form(None),
    ctx: dict = Depends(require_role("editor")),
):
    """Upload one file. Exactly one of (category) or (entityType+entityId)
    must be provided — org-level asset vs per-item attachment."""
    await assert_full_tier(ctx["user"])
    if bool(category) == bool(entityType):
        raise HTTPException(status_code=400,
            detail="Provide either category (org asset) OR entityType+entityId (attachment).")
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400,
            detail=f"Invalid category. Allowed: {sorted(VALID_CATEGORIES)}")
    if entityType:
        if entityType not in VALID_ENTITY_TYPES:
            raise HTTPException(status_code=400,
                detail=f"Invalid entityType. Allowed: {sorted(VALID_ENTITY_TYPES)}")
        if not entityId:
            raise HTTPException(status_code=400,
                detail="entityId required when entityType is set.")

    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413,
            detail=f"File too large ({len(content)/1e6:.1f} MB). Max is {MAX_BYTES/1e6:.0f} MB.")

    path = storage.build_object_path(ctx["org_id"], file.filename or "file")
    try:
        await storage.upload(path, content, file.content_type or "application/octet-stream")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {str(e)[:200]}")

    extracted = storage.extract_text(file.filename or "", file.content_type or "", content)

    row = await db.fetchrow(
        """insert into organization_files
              (organization_id, category, entity_type, entity_id, filename,
               mime, size_bytes, storage_path, extracted_text, uploaded_by)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
           returning *""",
        as_uuid(orgId), category, entityType,
        as_uuid(entityId) if entityId else None,
        (file.filename or "file")[:250],
        (file.content_type or "")[:100], len(content), path,
        extracted, as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "files.upload",
                      row["filename"],
                      {"category": category, "entityType": entityType,
                       "sizeBytes": len(content),
                       "extractedChars": len(extracted)})
    return _serialize_row(row)


@router.get("/{orgId}/files")
async def list_files(
    orgId: str,
    category: str = Query(""),
    entityType: str = Query(""),
    entityId: Optional[str] = Query(None),
    ctx: dict = Depends(require_role("viewer")),
):
    """List files for the org. Filter by category (org assets), by
    entityType+entityId (attachments), or leave both blank for the Disk
    Storage tab (returns everything, most recent first)."""
    await assert_full_tier(ctx["user"])
    sql = ["select id, organization_id, category, entity_type, entity_id, "
           "filename, mime, size_bytes, storage_path, uploaded_by, created_at "
           "from organization_files where organization_id = $1"]
    args = [as_uuid(orgId)]
    if category:
        sql.append(f"and category = ${len(args) + 1}")
        args.append(category)
    if entityType:
        sql.append(f"and entity_type = ${len(args) + 1}")
        args.append(entityType)
    if entityId:
        sql.append(f"and entity_id = ${len(args) + 1}")
        args.append(as_uuid(entityId))
    sql.append("order by created_at desc limit 500")
    rows = await db.fetch(" ".join(sql), *args)
    return [_serialize_row(r) for r in rows]


@router.get("/{orgId}/files/{fileId}/url")
async def download_url(orgId: str, fileId: str,
                       ctx: dict = Depends(require_role("viewer"))):
    """Return a short-lived signed URL the browser can use to download."""
    await assert_full_tier(ctx["user"])
    row = await db.fetchrow(
        "select storage_path, filename from organization_files "
        "where id = $1 and organization_id = $2",
        as_uuid(fileId), as_uuid(orgId))
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        url = await storage.signed_url(row["storage_path"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e)[:200])
    return {"url": url, "filename": row["filename"]}


@router.delete("/{orgId}/files/{fileId}")
async def delete_file(orgId: str, fileId: str,
                      ctx: dict = Depends(require_role("editor"))):
    await assert_full_tier(ctx["user"])
    row = await db.fetchrow(
        "select storage_path, filename from organization_files "
        "where id = $1 and organization_id = $2",
        as_uuid(fileId), as_uuid(orgId))
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        await storage.delete(row["storage_path"])
    except Exception:  # noqa: BLE001 — DB row still gets removed
        pass
    await db.execute("delete from organization_files where id = $1", as_uuid(fileId))
    await write_audit(ctx["org_id"], ctx["user"], "files.delete", row["filename"])
    return {"ok": True}


# ---------------- Server-side helper used by AI prompt-builders ----------------

async def gather_org_file_context(org_id, entity_type: str = "",
                                  entity_id: Optional[str] = None,
                                  max_chars: int = 24_000) -> str:
    """Return the extracted text from an org's uploaded files, formatted as a
    single string suitable for splicing into an AI prompt. Always includes
    every org-level asset (7 categories); optionally adds files attached to a
    specific entity when entity_type + entity_id are provided.

    Concatenated output is capped at `max_chars` (default 24KB) so prompts
    don't balloon past the model context window. Files are prioritized by
    recency and, within org-level assets, by category (past_performance and
    capability_statements first — the two categories that most affect AI
    scoring/writing quality)."""
    priority = ["past_performance", "capability_statements", "commercialization",
                "quad_charts", "resumes", "letters_of_support", "pitch_decks"]
    args = [as_uuid(org_id)]
    sql = ("select filename, category, extracted_text from organization_files "
           "where organization_id = $1 and coalesce(extracted_text,'') <> '' "
           "and category <> ''")
    org_rows = await db.fetch(sql, *args)

    ent_rows = []
    if entity_type and entity_id and entity_type in {"opportunity", "proposal", "venture_doc"}:
        ent_rows = await db.fetch(
            """select filename, category, extracted_text from organization_files
                 where organization_id = $1 and entity_type = $2 and entity_id = $3
                       and coalesce(extracted_text,'') <> ''
                 order by created_at desc""",
            as_uuid(org_id), entity_type, as_uuid(entity_id))

    def _key(row):
        try:
            return priority.index(row["category"])
        except ValueError:
            return 999
    org_rows = sorted(org_rows, key=_key)

    buf, total = [], 0
    for r in list(org_rows) + list(ent_rows):
        header = f"\n\n--- FILE: {r['filename']} · {r['category'] or 'attachment'} ---\n"
        body   = (r["extracted_text"] or "")[:4000]
        chunk  = header + body
        if total + len(chunk) > max_chars:
            break
        buf.append(chunk)
        total += len(chunk)
    return "".join(buf).strip()
