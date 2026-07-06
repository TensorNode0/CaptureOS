"""Role-based access control.

Functional roles (one per member per org):
  admin            — the org's Authorized Organizational Representative side:
                     can do anything, including everything a capture manager
                     can, plus entity info, members/roles, API keys, and the
                     only role that can submit / mark proposals as submitted.
  capture_manager  — runs the pipeline: creates and approves capabilities and
                     proposal packages; sees dashboards; may request a
                     time-boxed grant from the admin to edit entity info.
  pi / proposal_writer / technical_writer / editor
                   — contributors: edit opportunity and proposal content and
                     run AI drafting on volumes, but cannot create/approve
                     proposal packages, submit, or administer the org.
  viewer           — read-only.

`owner` is a legacy alias kept for pre-existing rows; it ranks above admin.
"""
from fastapi import HTTPException, Depends, Path

import database as db
from auth_utils import get_current_user
from utils import as_uuid

ROLE_RANK = {
    "viewer": 1,
    "editor": 2, "technical_writer": 2, "proposal_writer": 2, "pi": 2,
    "capture_manager": 3,
    "admin": 4,
    "owner": 5,
}

ASSIGNABLE_ROLES = {"viewer", "editor", "technical_writer", "proposal_writer",
                    "pi", "capture_manager", "admin"}

# Permission → roles that hold it. Admins can do anything; capture managers
# run the pipeline (create/approve) but cannot submit; contributors draft.
PERMISSIONS = {
    "proposal.create":  {"capture_manager", "admin", "owner"},
    "proposal.approve": {"capture_manager", "admin", "owner"},
    "proposal.submit":  {"admin", "owner"},
    "dashboard.view":   {"admin", "owner", "capture_manager"},
    "entity.edit":      {"admin", "owner"},  # capture_manager via approved grant
}


def has_perm(role: str, perm: str) -> bool:
    return role in PERMISSIONS.get(perm, set())


async def get_membership(org_id, user_id):
    o = as_uuid(org_id)
    u = as_uuid(user_id)
    if o is None or u is None:
        return None
    return await db.fetchrow(
        """select * from memberships
           where organization_id = $1 and user_id = $2 and status = 'active'""",
        o, u)


async def _build_ctx(orgId: str, user: dict) -> dict:
    o = as_uuid(orgId)
    if o is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    org = await db.fetchrow("select * from organizations where id = $1", o)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    membership = await get_membership(orgId, user["id"])
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")
    return {"user": user, "org": org, "org_id": o,
            "role": membership.get("role", "viewer"), "membership": membership}


def require_role(min_role: str):
    """Rank-based gate (viewer < contributor < capture_manager < admin)."""
    async def _dep(orgId: str = Path(...), user: dict = Depends(get_current_user)):
        ctx = await _build_ctx(orgId, user)
        if ROLE_RANK.get(ctx["role"], 0) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403,
                                detail=f"Requires {min_role} role (you are {ctx['role']})")
        return ctx
    return _dep


def require_perm(perm: str):
    """Permission-based gate for the strict product rules."""
    async def _dep(orgId: str = Path(...), user: dict = Depends(get_current_user)):
        ctx = await _build_ctx(orgId, user)
        if not has_perm(ctx["role"], perm):
            allowed = " or ".join(sorted(PERMISSIONS.get(perm, set()))) or "nobody"
            raise HTTPException(status_code=403,
                                detail=f"This action requires the {allowed} role "
                                       f"(you are {ctx['role']})")
        return ctx
    return _dep
