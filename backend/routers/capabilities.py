"""Proposed-capability endpoints: generate (AI), review/edit, approve, render,
export. One live capability per opportunity, with an approval version history."""
import base64
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Any, Dict, Optional

import database as db
from utils import now_utc, serialize, as_uuid
from rbac import require_role, require_perm
from domain import write_audit
import capability_ai
import ai_jobs
import exports
import genai
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["capabilities"])

MAX_PNG_BYTES = 3 * 1024 * 1024


async def _get_opp(org_id, opp_id):
    oid_ = as_uuid(opp_id)
    if oid_ is None:
        return None
    return await db.fetchrow(
        "select * from opportunities where id = $1 and organization_id = $2",
        oid_, org_id)


async def _get_cap(org_id, opp_id):
    oid_ = as_uuid(opp_id)
    if oid_ is None:
        return None
    return await db.fetchrow(
        "select * from capabilities where opportunity_id = $1 and organization_id = $2",
        oid_, org_id)


def _cap_payload(cap):
    if cap is None:
        return None
    has_png = bool(cap.get("rendering_png"))
    row = {k: v for k, v in cap.items() if k != "rendering_png"}
    out = serialize(row)
    out["hasRenderingPng"] = has_png
    return out


async def _run_generation(cap_id, engine, keys, org, profile, opp, user,
                          model="", effort="", job_id=None):
    try:
        content, used_model = await capability_ai.generate_capability(
            engine, keys, org, profile, opp, model=model, effort=effort, job_id=job_id)
        if job_id:
            await ai_jobs.stage(job_id, "Saving the capability…", 95)
        await db.execute(
            """update capabilities
               set content = $2, model = $3, generation_status = 'ready',
                   generation_error = '', status = 'draft', updated_at = $4
               where id = $1""",
            cap_id, content, used_model, now_utc())
        if job_id:
            await ai_jobs.finish(job_id, "Capability ready")
        await write_audit(org["id"], user, "capability.generate",
                          opp.get("title"), {"model": used_model})
    except ai_jobs.JobCancelled:
        await db.execute(
            """update capabilities
               set generation_status = 'idle', generation_error = '', updated_at = $2
               where id = $1""", cap_id, now_utc())
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "authentication" in msg.lower() or "401" in msg or "invalid x-api-key" in msg.lower():
            msg = "The AI provider rejected the API key. Update it in Settings → API Keys."
        if job_id:
            await ai_jobs.fail(job_id, msg)
        await db.execute(
            """update capabilities
               set generation_status = 'error', generation_error = $2, updated_at = $3
               where id = $1""",
            cap_id, msg[:900], now_utc())


@router.get("/{orgId}/opportunities/{oppId}/capability")
async def get_capability(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    cap = await _get_cap(ctx["org_id"], oppId)
    return _cap_payload(cap)


class GenerateIn(BaseModel):
    engine: str = "claude"
    model: str = ""
    effort: str = "standard"


AI_ENGINES = {"claude": "anthropic", "openai": "openai", "gemini": "gemini",
              "emergent": "emergent", "asksage": "asksage"}


@router.post("/{orgId}/opportunities/{oppId}/capability/generate")
async def generate_capability(oppId: str, body: GenerateIn = None,
                              ctx: dict = Depends(require_perm("proposal.create"))):
    body = body or GenerateIn()
    opp = await _get_opp(ctx["org_id"], oppId)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    keys = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="capability.generate")
    engine = body.engine if body.engine in AI_ENGINES else "claude"
    if not keys.get(AI_ENGINES[engine]):
        raise HTTPException(status_code=400,
            detail=f"No {genai.ENGINE_LABELS[engine]} API key set. Add it in Settings → API Keys.")
    cap = await _get_cap(ctx["org_id"], oppId)
    if cap and cap.get("generation_status") == "generating":
        raise HTTPException(status_code=409, detail="Generation already in progress")
    if cap:
        version = cap["version"] + (1 if cap.get("status") == "approved" else 0)
        cap = await db.fetchrow(
            """update capabilities
               set generation_status = 'generating', generation_error = '',
                   version = $2, updated_at = $3
               where id = $1 returning *""",
            cap["id"], version, now_utc())
    else:
        cap = await db.fetchrow(
            """insert into capabilities
                   (organization_id, opportunity_id, generation_status, created_by)
               values ($1, $2, 'generating', $3) returning *""",
            ctx["org_id"], opp["id"], as_uuid(ctx["user"]["id"]))

    profile = await db.fetchrow(
        "select * from org_profiles where organization_id = $1", ctx["org_id"])
    job_id = await ai_jobs.create(ctx["org_id"], ctx["user"], "capability.generate",
                                  ref_id=str(opp["id"]), engine=engine,
                                  model=body.model, effort=body.effort)
    asyncio.create_task(_run_generation(
        cap["id"], engine, keys, serialize(ctx["org"]), serialize(profile),
        serialize(opp), ctx["user"], model=body.model, effort=body.effort,
        job_id=job_id))
    return {"ok": True, "status": "generating", "capabilityId": str(cap["id"]),
            "jobId": str(job_id)}


class CapabilityUpdate(BaseModel):
    content: Dict[str, Any]


@router.put("/{orgId}/opportunities/{oppId}/capability")
async def update_capability(oppId: str, body: CapabilityUpdate,
                            ctx: dict = Depends(require_role("editor"))):
    cap = await _get_cap(ctx["org_id"], oppId)
    if not cap:
        raise HTTPException(status_code=404, detail="No capability generated yet")
    if cap.get("generation_status") == "generating":
        raise HTTPException(status_code=409, detail="Generation in progress — wait for it to finish")
    content = capability_ai.normalize_content(body.content)
    # keep the existing rendering if the client didn't send one
    if not content.get("renderingSvg"):
        content["renderingSvg"] = (cap.get("content") or {}).get("renderingSvg", "")
    was_approved = cap.get("status") == "approved"
    fresh = await db.fetchrow(
        """update capabilities
           set content = $2, status = 'draft',
               version = version + $3, updated_at = $4
           where id = $1 returning *""",
        cap["id"], content, 1 if was_approved else 0, now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "capability.edit",
                      content.get("title") or "capability")
    return _cap_payload(fresh)


@router.post("/{orgId}/opportunities/{oppId}/capability/approve")
async def approve_capability(oppId: str, ctx: dict = Depends(require_perm("proposal.approve"))):
    cap = await _get_cap(ctx["org_id"], oppId)
    if not cap:
        raise HTTPException(status_code=404, detail="No capability generated yet")
    if cap.get("generation_status") != "ready":
        raise HTTPException(status_code=400, detail="Capability is not ready to approve")
    uid = as_uuid(ctx["user"]["id"])
    await db.execute(
        """insert into capability_versions (capability_id, version, status, content, created_by)
           values ($1, $2, 'approved', $3, $4)""",
        cap["id"], cap["version"], cap.get("content") or {}, uid)
    fresh = await db.fetchrow(
        """update capabilities
           set status = 'approved', approved_by = $2, approved_at = $3, updated_at = $3
           where id = $1 returning *""",
        cap["id"], uid, now_utc())
    await write_audit(ctx["org_id"], ctx["user"], "capability.approve",
                      (cap.get("content") or {}).get("title") or "capability",
                      {"version": cap["version"]})
    return _cap_payload(fresh)


@router.get("/{orgId}/opportunities/{oppId}/capability/versions")
async def list_versions(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    cap = await _get_cap(ctx["org_id"], oppId)
    if not cap:
        return []
    rows = await db.fetch(
        """select id, version, status, created_by, created_at
           from capability_versions where capability_id = $1
           order by version desc, created_at desc""",
        cap["id"])
    return [serialize(r) for r in rows]


class RenderingIn(BaseModel):
    pngBase64: str


@router.post("/{orgId}/opportunities/{oppId}/capability/rendering")
async def upload_rendering(oppId: str, body: RenderingIn,
                           ctx: dict = Depends(require_role("editor"))):
    cap = await _get_cap(ctx["org_id"], oppId)
    if not cap:
        raise HTTPException(status_code=404, detail="No capability generated yet")
    raw = body.pngBase64
    if "," in raw[:64]:  # strip data:image/png;base64, prefix
        raw = raw.split(",", 1)[1]
    try:
        png = base64.b64decode(raw, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 PNG payload")
    if len(png) > MAX_PNG_BYTES:
        raise HTTPException(status_code=400, detail="PNG too large (max 3 MB)")
    if not png.startswith(b"\x89PNG"):
        raise HTTPException(status_code=400, detail="Payload is not a PNG image")
    await db.execute(
        "update capabilities set rendering_png = $2, updated_at = $3 where id = $1",
        cap["id"], png, now_utc())
    return {"ok": True, "bytes": len(png)}


@router.get("/{orgId}/opportunities/{oppId}/capability/rendering.png")
async def get_rendering(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    cap = await _get_cap(ctx["org_id"], oppId)
    if not cap or not cap.get("rendering_png"):
        raise HTTPException(status_code=404, detail="No rendering uploaded")
    return Response(content=bytes(cap["rendering_png"]), media_type="image/png")


@router.get("/{orgId}/opportunities/{oppId}/capability/export/docx")
async def export_capability_docx(oppId: str, ctx: dict = Depends(require_role("viewer"))):
    opp = await _get_opp(ctx["org_id"], oppId)
    cap = await _get_cap(ctx["org_id"], oppId)
    if not opp or not cap or not (cap.get("content") or {}).get("title"):
        raise HTTPException(status_code=404, detail="No capability to export")
    content = cap["content"]
    png = bytes(cap["rendering_png"]) if cap.get("rendering_png") else None
    data = exports.capability_docx(content, serialize(opp), ctx["org"]["name"], png)
    filename = exports.safe_filename(f"Proposed_Capability_{content.get('title', '')}", "docx")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
