from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from bson import ObjectId

from database import db
from utils import now_utc, serialize, oid
from auth_utils import get_current_user
from rbac import require_role, get_membership, ROLE_RANK
from domain import (write_audit, encrypt_secret, decrypt_secret, mask_secret)

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


# ---------------- Organizations ----------------
class OrgIn(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    naics: List[str] = []
    keywords: List[str] = []


@router.post("")
async def create_org(body: OrgIn, user: dict = Depends(get_current_user)):
    org = {
        "name": body.name.strip(),
        "naics": body.naics,
        "keywords": body.keywords,
        "ownerId": ObjectId(user["id"]),
        "createdAt": now_utc(),
    }
    res = await db.organizations.insert_one(org)
    await db.memberships.insert_one({
        "userId": ObjectId(user["id"]),
        "organizationId": res.inserted_id,
        "role": "owner",
        "invitedBy": None,
        "invitedEmail": user["email"],
        "status": "active",
        "createdAt": now_utc(),
    })
    await db.orgProfile.insert_one({
        "organizationId": res.inserted_id,
        "uei": "", "cage": "", "samActive": False, "isSmall": True,
        "certs": {"sba": False, "eightA": False, "hubzone": False,
                  "sdvosb": False, "wosb": False, "edwosb": False, "vosb": False},
        "cmmcLevel": "Level 1", "sprsScore": None, "sizeNote": "", "notes": "",
    })
    await write_audit(res.inserted_id, user, "org.create", body.name)
    org["_id"] = res.inserted_id
    out = serialize(org)
    out["role"] = "owner"
    return out


@router.get("")
async def list_orgs(user: dict = Depends(get_current_user)):
    memberships = await db.memberships.find(
        {"userId": ObjectId(user["id"]), "status": "active"}).to_list(100)
    result = []
    for m in memberships:
        org = await db.organizations.find_one({"_id": m["organizationId"]})
        if org:
            o = serialize(org)
            o["role"] = m["role"]
            result.append(o)
    return result


@router.get("/{orgId}")
async def get_org(ctx: dict = Depends(require_role("viewer"))):
    o = serialize(ctx["org"])
    o["role"] = ctx["role"]
    return o


@router.put("/{orgId}")
async def update_org(body: OrgIn, ctx: dict = Depends(require_role("admin"))):
    await db.organizations.update_one(
        {"_id": ctx["org_oid"]},
        {"$set": {"name": body.name.strip(), "naics": body.naics,
                  "keywords": body.keywords}})
    await write_audit(ctx["org_oid"], ctx["user"], "org.update", body.name)
    org = await db.organizations.find_one({"_id": ctx["org_oid"]})
    return serialize(org)


# ---------------- Org Profile ----------------
class CertsIn(BaseModel):
    sba: bool = False
    eightA: bool = False
    hubzone: bool = False
    sdvosb: bool = False
    wosb: bool = False
    edwosb: bool = False
    vosb: bool = False


class ProfileIn(BaseModel):
    uei: str = ""
    cage: str = ""
    samActive: bool = False
    isSmall: bool = True
    certs: CertsIn = CertsIn()
    cmmcLevel: str = "Level 1"
    sprsScore: Optional[int] = None
    sizeNote: str = ""
    notes: str = ""


@router.get("/{orgId}/profile")
async def get_profile(ctx: dict = Depends(require_role("viewer"))):
    prof = await db.orgProfile.find_one({"organizationId": ctx["org_oid"]})
    return serialize(prof) if prof else None


@router.put("/{orgId}/profile")
async def update_profile(body: ProfileIn, ctx: dict = Depends(require_role("admin"))):
    data = body.model_dump()
    data["certs"] = body.certs.model_dump()
    await db.orgProfile.update_one(
        {"organizationId": ctx["org_oid"]},
        {"$set": {**data, "organizationId": ctx["org_oid"]}}, upsert=True)
    await write_audit(ctx["org_oid"], ctx["user"], "profile.update", ctx["org"]["name"])
    prof = await db.orgProfile.find_one({"organizationId": ctx["org_oid"]})
    return serialize(prof)


# ---------------- Members ----------------
class InviteIn(BaseModel):
    email: EmailStr
    role: str = "viewer"


class RoleIn(BaseModel):
    role: str


class TransferIn(BaseModel):
    membershipId: str


VALID_ROLES = {"viewer", "editor", "admin"}


@router.get("/{orgId}/members")
async def list_members(ctx: dict = Depends(require_role("admin"))):
    members = await db.memberships.find({"organizationId": ctx["org_oid"]}).to_list(500)
    out = []
    for m in members:
        entry = serialize(m)
        if m.get("userId"):
            u = await db.users.find_one({"_id": m["userId"]})
            if u:
                entry["name"] = u.get("name")
                entry["email"] = u.get("email")
                entry["emailVerified"] = u.get("emailVerified", False)
        if not entry.get("email"):
            entry["email"] = m.get("invitedEmail")
        out.append(entry)
    return out


@router.post("/{orgId}/members/invite")
async def invite_member(body: InviteIn, ctx: dict = Depends(require_role("admin"))):
    role = body.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    email = body.email.lower().strip()
    existing_user = await db.users.find_one({"email": email})
    user_oid = existing_user["_id"] if existing_user else None
    # already a member?
    dup = await db.memberships.find_one({
        "organizationId": ctx["org_oid"],
        "$or": [{"invitedEmail": email}, {"userId": user_oid}] if user_oid else [{"invitedEmail": email}],
    })
    if dup:
        raise HTTPException(status_code=400, detail="This email is already a member or invited")
    status = "active" if existing_user else "invited"
    res = await db.memberships.insert_one({
        "userId": user_oid,
        "invitedEmail": email,
        "organizationId": ctx["org_oid"],
        "role": role,
        "invitedBy": ObjectId(ctx["user"]["id"]),
        "status": status,
        "createdAt": now_utc(),
    })
    invite_url = f"{__import__('os').environ.get('FRONTEND_URL','')}/login?invited={email}"
    print(f"[EMAIL-MOCK] Invite for {email} to org {ctx['org']['name']}: {invite_url}")
    await write_audit(ctx["org_oid"], ctx["user"], "member.invite", email, {"role": role})
    return {"ok": True, "membershipId": str(res.inserted_id), "status": status,
            "inviteUrl": invite_url}


@router.put("/{orgId}/members/{membershipId}")
async def change_role(body: RoleIn, membershipId: str, ctx: dict = Depends(require_role("admin"))):
    role = body.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role (cannot assign owner here)")
    mid = oid(membershipId)
    m = await db.memberships.find_one({"_id": mid, "organizationId": ctx["org_oid"]})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot change the Owner's role here")
    await db.memberships.update_one({"_id": mid}, {"$set": {"role": role}})
    await write_audit(ctx["org_oid"], ctx["user"], "member.role_change",
                      m.get("invitedEmail"), {"role": role})
    return {"ok": True}


@router.delete("/{orgId}/members/{membershipId}")
async def remove_member(membershipId: str, ctx: dict = Depends(require_role("admin"))):
    mid = oid(membershipId)
    m = await db.memberships.find_one({"_id": mid, "organizationId": ctx["org_oid"]})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the Owner")
    await db.memberships.delete_one({"_id": mid})
    await write_audit(ctx["org_oid"], ctx["user"], "member.remove", m.get("invitedEmail"))
    return {"ok": True}


@router.post("/{orgId}/members/transfer-ownership")
async def transfer_ownership(body: TransferIn, ctx: dict = Depends(require_role("owner"))):
    mid = oid(body.membershipId)
    target = await db.memberships.find_one({"_id": mid, "organizationId": ctx["org_oid"]})
    if not target or not target.get("userId"):
        raise HTTPException(status_code=404, detail="Target member not found / not active")
    # demote current owner to admin, promote target to owner
    await db.memberships.update_one(
        {"organizationId": ctx["org_oid"], "userId": ObjectId(ctx["user"]["id"])},
        {"$set": {"role": "admin"}})
    await db.memberships.update_one({"_id": mid}, {"$set": {"role": "owner"}})
    await db.organizations.update_one({"_id": ctx["org_oid"]},
                                      {"$set": {"ownerId": target["userId"]}})
    await write_audit(ctx["org_oid"], ctx["user"], "org.transfer_ownership",
                      target.get("invitedEmail"))
    return {"ok": True}


# ---------------- Audit ----------------
@router.get("/{orgId}/audit")
async def get_audit(ctx: dict = Depends(require_role("admin"))):
    logs = await db.auditLog.find({"organizationId": ctx["org_oid"]}) \
        .sort("at", -1).limit(200).to_list(200)
    return [serialize(l) for l in logs]


# ---------------- Secrets / Settings ----------------
class SecretsIn(BaseModel):
    anthropicKey: Optional[str] = None
    samKey: Optional[str] = None


@router.get("/{orgId}/secrets")
async def get_secrets(ctx: dict = Depends(require_role("admin"))):
    rec = await db.secrets.find_one({"organizationId": ctx["org_oid"]})
    if not rec:
        return {"anthropicKey": "", "samKey": "", "anthropicSet": False, "samSet": False}
    a = decrypt_secret(rec.get("anthropicKey", ""))
    s = decrypt_secret(rec.get("samKey", ""))
    return {
        "anthropicKey": mask_secret(a),
        "samKey": mask_secret(s),
        "anthropicSet": bool(a),
        "samSet": bool(s),
        "updatedAt": serialize(rec).get("updatedAt"),
    }


@router.put("/{orgId}/secrets")
async def update_secrets(body: SecretsIn, ctx: dict = Depends(require_role("admin"))):
    rec = await db.secrets.find_one({"organizationId": ctx["org_oid"]}) or {}
    update = {"organizationId": ctx["org_oid"],
              "updatedBy": ObjectId(ctx["user"]["id"]), "updatedAt": now_utc()}
    # only overwrite when a non-masked, non-empty value is provided
    if body.anthropicKey is not None and body.anthropicKey.strip() and "…" not in body.anthropicKey:
        update["anthropicKey"] = encrypt_secret(body.anthropicKey.strip())
    else:
        update["anthropicKey"] = rec.get("anthropicKey", "")
    if body.samKey is not None and body.samKey.strip() and "…" not in body.samKey:
        update["samKey"] = encrypt_secret(body.samKey.strip())
    else:
        update["samKey"] = rec.get("samKey", "")
    await db.secrets.update_one({"organizationId": ctx["org_oid"]},
                                {"$set": update}, upsert=True)
    await write_audit(ctx["org_oid"], ctx["user"], "secrets.update", "API keys")
    # MOCK validation result while integrations are mocked
    a = decrypt_secret(update["anthropicKey"])
    s = decrypt_secret(update["samKey"])
    return {
        "ok": True,
        "anthropicKey": mask_secret(a), "samKey": mask_secret(s),
        "anthropicSet": bool(a), "samSet": bool(s),
        "validation": {
            "anthropic": "valid (mock)" if a else "not set",
            "sam": "valid (mock)" if s else "not set",
        },
    }
