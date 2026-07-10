"""Subcontractor shared-access: a subcontractor sees ONLY the specific
proposal documents / capability sections the admin granted, read or write.
No other endpoint in the app is reachable at rank 0."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

import database as db
from utils import now_utc, serialize, as_uuid
from rbac import require_role
from auth_utils import get_current_user
from domain import write_audit

router = APIRouter(prefix="/api/orgs", tags=["shared"])

CAP_SECTIONS = {
    "summary": "Title, abstract & executive summary",
    "sow": "Statement of Work",
    "wbs": "WBS & schedule",
    "budget": "Budget",
}


async def _sub_membership(org_id, user_id):
    return await db.fetchrow(
        """select * from memberships where organization_id = $1 and user_id = $2
           and status = 'active' and role = 'subcontractor'""",
        org_id, as_uuid(user_id))


def _cap_slice(content, key):
    content = content or {}
    if key == "summary":
        return {"title": content.get("title"), "abstract": content.get("abstract"),
                "executiveSummary": content.get("executiveSummary")}
    if key == "wbs":
        return {"wbs": content.get("wbs") or [],
                "scheduleMonths": content.get("scheduleMonths")}
    return {key: content.get(key)}


@router.get("/{orgId}/shared")
async def my_shared(orgId: str, user: dict = Depends(get_current_user)):
    org_id = as_uuid(orgId)
    m = await _sub_membership(org_id, user["id"]) if org_id else None
    if not m:
        raise HTTPException(status_code=403, detail="No subcontractor access here")
    grants = await db.fetch(
        """select g.*, o.title as opp_title, o.sol_number, o.agency
           from subcontractor_grants g join opportunities o on o.id = g.opportunity_id
           where g.membership_id = $1 order by g.created_at""",
        m["id"])
    out = []
    for g in grants:
        entry = {"grantId": str(g["id"]), "access": g["access"],
                 "resourceType": g["resource_type"],
                 "opportunity": {"title": g["opp_title"], "solNumber": g["sol_number"],
                                 "agency": g["agency"]}}
        if g["resource_type"] == "proposal_doc":
            doc = await db.fetchrow(
                "select title, fmt, content_md, content_json, status from proposal_documents where id = $1",
                as_uuid(g["resource_id"]))
            if not doc:
                continue
            entry.update({"label": doc["title"], "fmt": doc["fmt"],
                          "contentMd": doc["content_md"],
                          "contentJson": doc["content_json"], "status": doc["status"]})
        else:
            cap = await db.fetchrow(
                "select content from capabilities where opportunity_id = $1",
                g["opportunity_id"])
            key = g["resource_id"]
            entry.update({"label": CAP_SECTIONS.get(key, key), "sectionKey": key,
                          "content": _cap_slice((cap or {}).get("content"), key)})
        out.append(entry)
    return out


class SharedUpdate(BaseModel):
    contentMd: Optional[str] = None
    contentJson: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None  # capability section slice


@router.put("/{orgId}/shared/{grantId}")
async def update_shared(orgId: str, grantId: str, body: SharedUpdate,
                        user: dict = Depends(get_current_user)):
    org_id = as_uuid(orgId)
    m = await _sub_membership(org_id, user["id"]) if org_id else None
    if not m:
        raise HTTPException(status_code=403, detail="No subcontractor access here")
    g = await db.fetchrow(
        "select * from subcontractor_grants where id = $1 and membership_id = $2",
        as_uuid(grantId), m["id"])
    if not g:
        raise HTTPException(status_code=404, detail="Grant not found")
    if g["access"] != "write":
        raise HTTPException(status_code=403, detail="This share is read-only")

    if g["resource_type"] == "proposal_doc":
        doc = await db.fetchrow("select * from proposal_documents where id = $1",
                                as_uuid(g["resource_id"]))
        if not doc:
            raise HTTPException(status_code=404, detail="Document no longer exists")
        md = body.contentMd if body.contentMd is not None else doc["content_md"]
        cj = body.contentJson if body.contentJson is not None else doc["content_json"]
        await db.execute(
            """update proposal_documents set content_md = $2, content_json = $3,
               status = 'edited', updated_at = $4 where id = $1""",
            doc["id"], md, cj, now_utc())
    else:
        if not isinstance(body.content, dict):
            raise HTTPException(status_code=400, detail="content object required")
        cap = await db.fetchrow(
            "select id, content from capabilities where opportunity_id = $1",
            g["opportunity_id"])
        if not cap:
            raise HTTPException(status_code=404, detail="Capability no longer exists")
        content = dict(cap["content"] or {})
        key = g["resource_id"]
        if key == "summary":
            for f in ("title", "abstract", "executiveSummary"):
                if f in body.content:
                    content[f] = body.content[f]
        elif key == "wbs":
            if "wbs" in body.content:
                content["wbs"] = body.content["wbs"]
            if "scheduleMonths" in body.content:
                content["scheduleMonths"] = body.content["scheduleMonths"]
        else:
            if key in body.content:
                content[key] = body.content[key]
        await db.execute(
            "update capabilities set content = $2, updated_at = $3 where id = $1",
            cap["id"], content, now_utc())
    await write_audit(org_id, user, "shared.update",
                      f"{g['resource_type']}:{g['resource_id']}")
    return {"ok": True}


# ─────────────── Admin: manage a subcontractor's grants ───────────────
class GrantIn(BaseModel):
    resourceType: str
    resourceId: str
    access: str  # read | write


class GrantsPut(BaseModel):
    opportunityId: str
    grants: List[GrantIn] = []


@router.get("/{orgId}/members/{membershipId}/grants")
async def list_grants(membershipId: str, ctx: dict = Depends(require_role("admin"))):
    mid = as_uuid(membershipId)
    rows = await db.fetch(
        "select * from subcontractor_grants where membership_id = $1 and organization_id = $2",
        mid, ctx["org_id"]) if mid else []
    return [serialize(r) for r in rows]


@router.put("/{orgId}/members/{membershipId}/grants")
async def set_grants(membershipId: str, body: GrantsPut,
                     ctx: dict = Depends(require_role("admin"))):
    """Replace this subcontractor's grants for one opportunity."""
    mid = as_uuid(membershipId)
    m = await db.fetchrow(
        "select * from memberships where id = $1 and organization_id = $2",
        mid, ctx["org_id"]) if mid else None
    if not m or m.get("role") != "subcontractor":
        raise HTTPException(status_code=404, detail="Subcontractor member not found")
    opp_id = as_uuid(body.opportunityId)
    opp = await db.fetchrow(
        "select id, title from opportunities where id = $1 and organization_id = $2",
        opp_id, ctx["org_id"]) if opp_id else None
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    for gr in body.grants:
        if gr.resourceType not in ("proposal_doc", "capability_section") \
                or gr.access not in ("read", "write"):
            raise HTTPException(status_code=400, detail="Invalid grant entry")
        if gr.resourceType == "capability_section" and gr.resourceId not in CAP_SECTIONS:
            raise HTTPException(status_code=400, detail=f"Unknown section {gr.resourceId}")
    await db.execute(
        "delete from subcontractor_grants where membership_id = $1 and opportunity_id = $2",
        mid, opp["id"])
    for gr in body.grants:
        await db.execute(
            """insert into subcontractor_grants
               (organization_id, membership_id, opportunity_id, resource_type,
                resource_id, access, created_by)
               values ($1, $2, $3, $4, $5, $6, $7)""",
            ctx["org_id"], mid, opp["id"], gr.resourceType, gr.resourceId,
            gr.access, as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "shared.grants_set",
                      m.get("invited_email"),
                      {"opportunity": opp["title"], "count": len(body.grants)})
    return {"ok": True, "count": len(body.grants)}
