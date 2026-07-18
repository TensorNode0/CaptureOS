"""Supabase Storage adapter + text extraction for uploaded files.

The bucket is `captureagent-org-files`, provisioned by migration 0021. Objects
live at `{org_id}/{uuid}-{safe_filename}` so each org's tree is scoped by
prefix even though we authorize via the backend rather than storage RLS.

All calls use SUPABASE_SERVICE_ROLE_KEY (server-side only). Browsers never
touch the storage API directly — they hit our own /files endpoints, which
mint short-lived signed URLs for actual downloads.
"""
from __future__ import annotations

import io
import os
import re
import uuid
from typing import Optional

import httpx

BUCKET = "captureagent-org-files"
_MAX_EXTRACTED = 50_000            # 50KB cap so AI prompts stay sane
_SIGNED_URL_TTL_SEC = 60 * 15      # 15 min


def _service_headers() -> dict:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing — Files feature disabled.")
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _base() -> str:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL missing — Files feature disabled.")
    return url


_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def build_object_path(org_id: str, filename: str) -> str:
    """`{org}/{uuid}-{sanitized}` so listing by prefix works and duplicate
    filenames don't clobber each other."""
    safe = _SAFE.sub("_", filename)[:120] or "file"
    return f"{org_id}/{uuid.uuid4().hex}-{safe}"


async def upload(path: str, content: bytes, content_type: str) -> None:
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"{_base()}/storage/v1/object/{BUCKET}/{path}",
            headers={**_service_headers(), "Content-Type": content_type or "application/octet-stream"},
            content=content)
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase upload failed {r.status_code}: {r.text[:200]}")


async def delete(path: str) -> None:
    """Idempotent: 404 is treated as success (already gone)."""
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.request("DELETE", f"{_base()}/storage/v1/object/{BUCKET}",
                            headers=_service_headers(),
                            json={"prefixes": [path]})
    if r.status_code >= 400 and r.status_code != 404:
        raise RuntimeError(f"Supabase delete failed {r.status_code}: {r.text[:200]}")


async def signed_url(path: str, ttl_seconds: int = _SIGNED_URL_TTL_SEC) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{_base()}/storage/v1/object/sign/{BUCKET}/{path}",
            headers=_service_headers(),
            json={"expiresIn": ttl_seconds})
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase sign failed {r.status_code}: {r.text[:200]}")
    signed = (r.json() or {}).get("signedURL", "")
    if not signed:
        raise RuntimeError("Supabase returned no signedURL")
    # Endpoint returns a relative URL like `/storage/v1/object/sign/<bucket>/...?token=...`
    return f"{_base()}{signed}" if signed.startswith("/") else signed


# ---------------- Text extraction ----------------

def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for page in reader.pages[:100]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(parts)


def _extract_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def extract_text(filename: str, mime: str, content: bytes) -> str:
    """Best-effort extract. Returns "" for unsupported types — no exception."""
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    m = (mime or "").lower()
    try:
        if ext == "pdf" or "pdf" in m:
            return _extract_pdf(content)[:_MAX_EXTRACTED]
        if ext == "docx" or "wordprocessingml" in m:
            return _extract_docx(content)[:_MAX_EXTRACTED]
        if ext in ("txt", "md") or m.startswith("text/"):
            return content.decode("utf-8", errors="replace")[:_MAX_EXTRACTED]
    except Exception:  # noqa: BLE001 — extraction is best-effort
        return ""
    return ""
