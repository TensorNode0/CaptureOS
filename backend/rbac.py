from fastapi import HTTPException, Depends, Path
from bson import ObjectId

from database import db
from auth_utils import get_current_user
from utils import oid

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3, "owner": 4}


async def get_membership(org_id: str, user_id: str):
    o = oid(org_id)
    if not o:
        return None
    return await db.memberships.find_one({
        "organizationId": o,
        "userId": ObjectId(user_id),
        "status": "active",
    })


def require_role(min_role: str):
    """Dependency factory: ensures the current user has >= min_role in the org
    identified by path param `orgId`. Returns a context dict."""
    async def _dep(orgId: str = Path(...), user: dict = Depends(get_current_user)):
        o = oid(orgId)
        if not o:
            raise HTTPException(status_code=404, detail="Organization not found")
        org = await db.organizations.find_one({"_id": o})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        membership = await get_membership(orgId, user["id"])
        if not membership:
            raise HTTPException(status_code=403, detail="You are not a member of this organization")
        role = membership.get("role", "viewer")
        if ROLE_RANK.get(role, 0) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403,
                                detail=f"Requires {min_role} role (you are {role})")
        return {"user": user, "org": org, "org_oid": o, "role": role,
                "membership": membership}
    return _dep
