from fastapi import HTTPException, Depends, Path

import database as db
from auth_utils import get_current_user
from utils import as_uuid

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}


async def get_membership(org_id, user_id):
    o = as_uuid(org_id)
    u = as_uuid(user_id)
    if o is None or u is None:
        return None
    return await db.fetchrow(
        """select * from memberships
           where organization_id = $1 and user_id = $2 and status = 'active'""",
        o, u)


def require_role(min_role: str):
    """Dependency factory: ensures the current user has >= min_role in the org
    identified by path param `orgId`. Returns a context dict."""
    async def _dep(orgId: str = Path(...), user: dict = Depends(get_current_user)):
        o = as_uuid(orgId)
        if o is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        org = await db.fetchrow("select * from organizations where id = $1", o)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        membership = await get_membership(orgId, user["id"])
        if not membership:
            raise HTTPException(status_code=403, detail="You are not a member of this organization")
        role = membership.get("role", "viewer")
        if ROLE_RANK.get(role, 0) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403,
                                detail=f"Requires {min_role} role (you are {role})")
        return {"user": user, "org": org, "org_id": o, "role": role,
                "membership": membership}
    return _dep
