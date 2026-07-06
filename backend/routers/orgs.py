import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from secrets import token_hex

import database as db
import email_service
from utils import now_utc, serialize, as_uuid
from auth_utils import get_current_user
from rbac import require_role, ASSIGNABLE_ROLES
from domain import write_audit
import org_keys

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


def _gen_join_code():
    return token_hex(4).upper()  # 8-char shareable code


DEFAULT_CERTS = {"sba": False, "eightA": False, "hubzone": False,
                 "sdvosb": False, "wosb": False, "edwosb": False, "vosb": False}

# Public mailbox providers never claim an org domain — those users create an
# org without a domain (colleagues join via invite or join code instead).
PUBLIC_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "outlook.com",
    "hotmail.com", "live.com", "msn.com", "aol.com", "icloud.com", "me.com",
    "mac.com", "proton.me", "protonmail.com", "pm.me", "mail.com", "gmx.com",
    "zoho.com", "comcast.net", "verizon.net", "att.net",
}


def _email_domain(email: str) -> str:
    return (email or "").rsplit("@", 1)[-1].lower().strip()


def _is_public_domain(domain: str) -> bool:
    return domain in PUBLIC_EMAIL_DOMAINS or not domain


async def _org_admin_emails(org_id):
    rows = await db.fetch(
        """select u.email from memberships m join users u on u.id = m.user_id
           where m.organization_id = $1 and m.status = 'active'
             and m.role in ('admin', 'owner')""", org_id)
    return [r["email"] for r in rows]


# ---------------- Organizations ----------------
class OrgIn(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    naics: List[str] = []
    keywords: List[str] = []
    certifyAor: bool = False


@router.get("/domain-status")
async def domain_status(user: dict = Depends(get_current_user)):
    """Signup routing: does an org already exist for this user's email domain?"""
    domain = _email_domain(user["email"])
    public = _is_public_domain(domain)
    org = None
    membership = None
    if not public:
        org = await db.fetchrow(
            "select id, name from organizations where lower(domain) = $1", domain)
        if org:
            membership = await db.fetchrow(
                """select status from memberships
                   where organization_id = $1 and user_id = $2""",
                org["id"], as_uuid(user["id"]))
    return {
        "domain": domain,
        "publicDomain": public,
        "org": {"id": str(org["id"]), "name": org["name"]} if org else None,
        "membershipStatus": membership["status"] if membership else None,
    }


@router.post("")
async def create_org(body: OrgIn, user: dict = Depends(get_current_user)):
    if not body.certifyAor:
        raise HTTPException(status_code=400, detail=(
            "You must certify that you are your organization's Authorized "
            "Organizational Representative (AOR) / Administrator to create a workspace."))
    uid = as_uuid(user["id"])
    domain = _email_domain(user["email"])
    if _is_public_domain(domain):
        domain = ""
    else:
        taken = await db.fetchrow(
            "select id, name from organizations where lower(domain) = $1", domain)
        if taken:
            member = await db.fetchrow(
                """select id from memberships where organization_id = $1
                   and user_id = $2 and status = 'active'""", taken["id"], uid)
            if not member:
                raise HTTPException(status_code=409, detail=(
                    f"{taken['name']} already has a CaptureAgent workspace for @{domain}. "
                    "Request to join it instead — its administrator will approve you."))
            domain = ""  # existing member spinning up an extra workspace: no new claim
    org = await db.fetchrow(
        """insert into organizations (name, naics, keywords, owner_id, join_code,
                                      domain, aor_certified_by, aor_certified_at)
           values ($1, $2, $3, $4, $5, $6, $4, $7) returning *""",
        body.name.strip(), body.naics, body.keywords, uid, _gen_join_code(),
        domain, now_utc())
    await db.execute(
        """insert into memberships (user_id, invited_email, organization_id, role,
                                    invited_by, status)
           values ($1, $2, $3, 'admin', null, 'active')""",
        uid, user["email"], org["id"])
    await db.execute(
        """insert into org_profiles (organization_id, certs)
           values ($1, $2)""",
        org["id"], DEFAULT_CERTS)
    await write_audit(org["id"], user, "org.create", body.name,
                      {"aorCertified": True, "domain": domain})
    out = serialize(org)
    out["role"] = "admin"
    return out


@router.post("/{orgId}/join-request")
async def request_to_join(orgId: str, user: dict = Depends(get_current_user)):
    """Self-signup with a known company domain → pending until admin approves."""
    oid_ = as_uuid(orgId)
    org = await db.fetchrow("select * from organizations where id = $1", oid_) if oid_ else None
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not org.get("domain") or _email_domain(user["email"]) != org["domain"].lower():
        raise HTTPException(status_code=403, detail=(
            "Your email domain does not match this organization. "
            "Ask an administrator for an invite or a join code."))
    existing = await db.fetchrow(
        "select * from memberships where organization_id = $1 and user_id = $2",
        org["id"], as_uuid(user["id"]))
    if existing:
        if existing["status"] == "pending":
            return {"ok": True, "status": "pending"}
        raise HTTPException(status_code=400, detail="You already have access to this organization")
    await db.execute(
        """insert into memberships (user_id, invited_email, organization_id, role,
                                    invited_by, status)
           values ($1, $2, $3, 'viewer', null, 'pending')""",
        as_uuid(user["id"]), user["email"], org["id"])
    await write_audit(org["id"], user, "member.join_request", user["email"])
    for admin_email in await _org_admin_emails(org["id"]):
        try:
            await email_service.send(
                admin_email, f"CaptureAgent: access request for {org['name']}",
                email_service._layout(
                    "New access request",
                    f"{user.get('name') or user['email']} ({user['email']}) requested "
                    f"access to the {org['name']} workspace. Approve or deny them and "
                    "assign a role from the Admin page.",
                    f"{os.environ.get('FRONTEND_URL', '')}/admin", "Review request"))
        except Exception as e:
            print(f"[EMAIL-ERROR] join-request notify failed: {e}")
    return {"ok": True, "status": "pending"}


@router.get("")
async def list_orgs(user: dict = Depends(get_current_user)):
    rows = await db.fetch(
        """select o.*, m.role as member_role
           from memberships m join organizations o on o.id = m.organization_id
           where m.user_id = $1 and m.status = 'active'
           order by o.created_at""",
        as_uuid(user["id"]))
    result = []
    for r in rows:
        role = r.pop("member_role")
        o = serialize(r)
        o["role"] = role
        result.append(o)
    return result


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=40)


@router.post("/join")
async def join_org(body: JoinIn, user: dict = Depends(get_current_user)):
    code = body.code.strip().upper()
    org = await db.fetchrow("select * from organizations where join_code = $1", code)
    if not org:
        raise HTTPException(status_code=404, detail="Invalid join code")
    uid = as_uuid(user["id"])
    existing = await db.fetchrow(
        "select * from memberships where organization_id = $1 and user_id = $2",
        org["id"], uid)
    if existing:
        if existing.get("status") != "active":
            await db.execute("update memberships set status = 'active' where id = $1",
                             existing["id"])
        else:
            raise HTTPException(status_code=400, detail="You are already a member")
    else:
        await db.execute(
            """insert into memberships (user_id, invited_email, organization_id, role,
                                        invited_by, status, joined_via_code)
               values ($1, $2, $3, 'viewer', null, 'active', true)""",
            uid, user["email"], org["id"])
    await write_audit(org["id"], user, "member.join_code", user["email"])
    out = serialize(org)
    out["role"] = "viewer" if not (existing and existing.get("role")) else existing["role"]
    return out


@router.get("/{orgId}")
async def get_org(ctx: dict = Depends(require_role("viewer"))):
    o = serialize(ctx["org"])
    o["role"] = ctx["role"]
    return o


@router.put("/{orgId}")
async def update_org(body: OrgIn, ctx: dict = Depends(require_role("admin"))):
    org = await db.fetchrow(
        """update organizations set name = $2, naics = $3, keywords = $4
           where id = $1 returning *""",
        ctx["org_id"], body.name.strip(), body.naics, body.keywords)
    await write_audit(ctx["org_id"], ctx["user"], "org.update", body.name)
    return serialize(org)


@router.get("/{orgId}/join-code")
async def get_join_code(ctx: dict = Depends(require_role("admin"))):
    code = ctx["org"].get("join_code")
    if not code:
        code = _gen_join_code()
        await db.execute("update organizations set join_code = $2 where id = $1",
                         ctx["org_id"], code)
    return {"joinCode": code}


@router.post("/{orgId}/join-code/rotate")
async def rotate_join_code(ctx: dict = Depends(require_role("admin"))):
    code = _gen_join_code()
    await db.execute("update organizations set join_code = $2 where id = $1",
                     ctx["org_id"], code)
    await write_audit(ctx["org_id"], ctx["user"], "org.rotate_join_code", ctx["org"]["name"])
    return {"joinCode": code}


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
    capabilities: str = ""
    pastPerformance: str = ""
    techFocus: List[str] = []
    differentiators: str = ""
    commercialization: str = ""
    clearances: str = ""


async def _has_edit_grant(org_id, user_id) -> bool:
    row = await db.fetchrow(
        """select id from profile_edit_requests
           where organization_id = $1 and requested_by = $2
             and status = 'approved' and expires_at > now() limit 1""",
        org_id, as_uuid(user_id))
    return bool(row)


def _can_edit_entity(role: str) -> bool:
    return role in ("admin", "owner")


@router.get("/{orgId}/profile")
async def get_profile(ctx: dict = Depends(require_role("viewer"))):
    prof = await db.fetchrow("select * from org_profiles where organization_id = $1",
                             ctx["org_id"])
    out = serialize(prof) if prof else {}
    can_edit = _can_edit_entity(ctx["role"])
    pending_request = False
    if not can_edit and ctx["role"] == "capture_manager":
        if await _has_edit_grant(ctx["org_id"], ctx["user"]["id"]):
            can_edit = True
        else:
            pending_request = bool(await db.fetchrow(
                """select id from profile_edit_requests
                   where organization_id = $1 and requested_by = $2 and status = 'pending'""",
                ctx["org_id"], as_uuid(ctx["user"]["id"])))
    out["canEdit"] = can_edit
    out["editRequestPending"] = pending_request
    return out


@router.post("/{orgId}/profile/edit-request")
async def request_profile_edit(ctx: dict = Depends(require_role("capture_manager"))):
    """Capture manager asks the admin for a time-boxed entity-info edit window."""
    if _can_edit_entity(ctx["role"]):
        raise HTTPException(status_code=400, detail="You can already edit entity info")
    dup = await db.fetchrow(
        """select id from profile_edit_requests
           where organization_id = $1 and requested_by = $2 and status = 'pending'""",
        ctx["org_id"], as_uuid(ctx["user"]["id"]))
    if dup:
        return {"ok": True, "status": "pending"}
    await db.execute(
        """insert into profile_edit_requests (organization_id, requested_by)
           values ($1, $2)""",
        ctx["org_id"], as_uuid(ctx["user"]["id"]))
    await write_audit(ctx["org_id"], ctx["user"], "profile.edit_request",
                      ctx["org"]["name"])
    for admin_email in await _org_admin_emails(ctx["org_id"]):
        try:
            await email_service.send(
                admin_email, "CaptureAgent: entity-info edit request",
                email_service._layout(
                    "Entity edit request",
                    f"{ctx['user'].get('name') or ctx['user']['email']} (capture manager) "
                    f"requested permission to edit {ctx['org']['name']}'s entity "
                    "information. Approve to grant a 24-hour edit window.",
                    f"{os.environ.get('FRONTEND_URL', '')}/admin", "Review request"))
        except Exception as e:
            print(f"[EMAIL-ERROR] edit-request notify failed: {e}")
    return {"ok": True, "status": "pending"}


@router.get("/{orgId}/profile/edit-requests")
async def list_edit_requests(ctx: dict = Depends(require_role("admin"))):
    rows = await db.fetch(
        """select r.*, u.name as requester_name, u.email as requester_email
           from profile_edit_requests r join users u on u.id = r.requested_by
           where r.organization_id = $1 order by r.created_at desc limit 50""",
        ctx["org_id"])
    out = []
    for r in rows:
        name = r.pop("requester_name", None)
        email = r.pop("requester_email", None)
        entry = serialize(r)
        entry["requesterName"] = name
        entry["requesterEmail"] = email
        out.append(entry)
    return out


class DecideIn(BaseModel):
    approve: bool


@router.post("/{orgId}/profile/edit-requests/{reqId}/decide")
async def decide_edit_request(reqId: str, body: DecideIn,
                              ctx: dict = Depends(require_role("admin"))):
    rid = as_uuid(reqId)
    req = await db.fetchrow(
        """select * from profile_edit_requests
           where id = $1 and organization_id = $2 and status = 'pending'""",
        rid, ctx["org_id"]) if rid else None
    if not req:
        raise HTTPException(status_code=404, detail="Pending request not found")
    status = "approved" if body.approve else "denied"
    expires = now_utc() + timedelta(hours=24) if body.approve else None
    await db.execute(
        """update profile_edit_requests
           set status = $2, decided_by = $3, decided_at = $4, expires_at = $5
           where id = $1""",
        rid, status, as_uuid(ctx["user"]["id"]), now_utc(), expires)
    await write_audit(ctx["org_id"], ctx["user"], f"profile.edit_request_{status}",
                      ctx["org"]["name"])
    return {"ok": True, "status": status}


@router.put("/{orgId}/profile")
async def update_profile(body: ProfileIn, ctx: dict = Depends(require_role("capture_manager"))):
    if not _can_edit_entity(ctx["role"]):
        if not await _has_edit_grant(ctx["org_id"], ctx["user"]["id"]):
            raise HTTPException(status_code=403, detail=(
                "Entity information is managed by your administrator. "
                "Use 'Request edit access' and wait for approval."))
    prof = await db.fetchrow(
        """insert into org_profiles (organization_id, uei, cage, sam_active, is_small,
               certs, cmmc_level, sprs_score, size_note, notes, capabilities,
               past_performance, tech_focus, differentiators, commercialization, clearances)
           values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
           on conflict (organization_id) do update set
               uei = excluded.uei, cage = excluded.cage, sam_active = excluded.sam_active,
               is_small = excluded.is_small, certs = excluded.certs,
               cmmc_level = excluded.cmmc_level, sprs_score = excluded.sprs_score,
               size_note = excluded.size_note, notes = excluded.notes,
               capabilities = excluded.capabilities,
               past_performance = excluded.past_performance,
               tech_focus = excluded.tech_focus,
               differentiators = excluded.differentiators,
               commercialization = excluded.commercialization,
               clearances = excluded.clearances
           returning *""",
        ctx["org_id"], body.uei, body.cage, body.samActive, body.isSmall,
        body.certs.model_dump(), body.cmmcLevel, body.sprsScore, body.sizeNote,
        body.notes, body.capabilities, body.pastPerformance, body.techFocus,
        body.differentiators, body.commercialization, body.clearances)
    await write_audit(ctx["org_id"], ctx["user"], "profile.update", ctx["org"]["name"])
    return serialize(prof)


# ---------------- Members ----------------
class InviteIn(BaseModel):
    email: EmailStr
    role: str = "viewer"


class RoleIn(BaseModel):
    role: str


class TransferIn(BaseModel):
    membershipId: str


VALID_ROLES = ASSIGNABLE_ROLES


@router.get("/{orgId}/members")
async def list_members(ctx: dict = Depends(require_role("admin"))):
    members = await db.fetch(
        """select m.*, u.name as user_name, u.email as user_email,
                  u.email_verified as user_email_verified
           from memberships m left join users u on u.id = m.user_id
           where m.organization_id = $1
           order by m.created_at""",
        ctx["org_id"])
    out = []
    for m in members:
        name = m.pop("user_name", None)
        email = m.pop("user_email", None)
        verified = m.pop("user_email_verified", None)
        entry = serialize(m)
        if name is not None:
            entry["name"] = name
        if email:
            entry["email"] = email
            entry["emailVerified"] = bool(verified)
        if not entry.get("email"):
            entry["email"] = m.get("invited_email")
        out.append(entry)
    return out


@router.post("/{orgId}/members/invite")
async def invite_member(body: InviteIn, ctx: dict = Depends(require_role("admin"))):
    role = body.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    email = body.email.lower().strip()
    existing_user = await db.fetchrow("select * from users where email = $1", email)
    user_id = existing_user["id"] if existing_user else None
    dup = await db.fetchrow(
        """select id from memberships
           where organization_id = $1
             and (invited_email = $2 or (user_id is not null and user_id = $3))""",
        ctx["org_id"], email, user_id)
    if dup:
        raise HTTPException(status_code=400, detail="This email is already a member or invited")
    status = "active" if existing_user else "invited"
    membership = await db.fetchrow(
        """insert into memberships (user_id, invited_email, organization_id, role,
                                    invited_by, status)
           values ($1, $2, $3, $4, $5, $6) returning id""",
        user_id, email, ctx["org_id"], role, as_uuid(ctx["user"]["id"]), status)
    invite_url = f"{os.environ.get('FRONTEND_URL', '')}/login?invited={email}"
    try:
        await email_service.send_invite(email, ctx["org"]["name"], invite_url)
    except Exception as e:
        print(f"[EMAIL-ERROR] invite send failed for {email}: {e}")
    await write_audit(ctx["org_id"], ctx["user"], "member.invite", email, {"role": role})
    return {"ok": True, "membershipId": str(membership["id"]), "status": status,
            "inviteUrl": invite_url}


class ApproveIn(BaseModel):
    role: str = "viewer"


@router.post("/{orgId}/members/{membershipId}/approve")
async def approve_member(membershipId: str, body: ApproveIn,
                         ctx: dict = Depends(require_role("admin"))):
    """Approve a pending (domain self-signup) member and assign their role."""
    role = body.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    mid = as_uuid(membershipId)
    m = await db.fetchrow(
        """select * from memberships
           where id = $1 and organization_id = $2 and status = 'pending'""",
        mid, ctx["org_id"]) if mid else None
    if not m:
        raise HTTPException(status_code=404, detail="Pending member not found")
    await db.execute(
        "update memberships set status = 'active', role = $2 where id = $1", mid, role)
    await write_audit(ctx["org_id"], ctx["user"], "member.approve",
                      m.get("invited_email"), {"role": role})
    try:
        await email_service.send(
            m["invited_email"], f"You're in — {ctx['org']['name']} on CaptureAgent",
            email_service._layout(
                "Access approved",
                f"Your access request to {ctx['org']['name']} was approved with the "
                f"role: {role.replace('_', ' ')}. You can sign in now.",
                f"{os.environ.get('FRONTEND_URL', '')}/login", "Sign in"))
    except Exception as e:
        print(f"[EMAIL-ERROR] approve notify failed: {e}")
    return {"ok": True, "role": role}


@router.put("/{orgId}/members/{membershipId}")
async def change_role(body: RoleIn, membershipId: str, ctx: dict = Depends(require_role("admin"))):
    role = body.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role (cannot assign owner here)")
    mid = as_uuid(membershipId)
    m = await db.fetchrow(
        "select * from memberships where id = $1 and organization_id = $2",
        mid, ctx["org_id"]) if mid else None
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot change the Owner's role here")
    await db.execute("update memberships set role = $2 where id = $1", mid, role)
    await write_audit(ctx["org_id"], ctx["user"], "member.role_change",
                      m.get("invited_email"), {"role": role})
    return {"ok": True}


@router.delete("/{orgId}/members/{membershipId}")
async def remove_member(membershipId: str, ctx: dict = Depends(require_role("admin"))):
    mid = as_uuid(membershipId)
    m = await db.fetchrow(
        "select * from memberships where id = $1 and organization_id = $2",
        mid, ctx["org_id"]) if mid else None
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the Owner")
    await db.execute("delete from memberships where id = $1", mid)
    await write_audit(ctx["org_id"], ctx["user"], "member.remove", m.get("invited_email"))
    return {"ok": True}


@router.post("/{orgId}/members/transfer-ownership")
async def transfer_ownership(body: TransferIn, ctx: dict = Depends(require_role("owner"))):
    mid = as_uuid(body.membershipId)
    target = await db.fetchrow(
        "select * from memberships where id = $1 and organization_id = $2",
        mid, ctx["org_id"]) if mid else None
    if not target or not target.get("user_id"):
        raise HTTPException(status_code=404, detail="Target member not found / not active")
    # demote current owner to admin, promote target to owner
    await db.execute(
        """update memberships set role = 'admin'
           where organization_id = $1 and user_id = $2""",
        ctx["org_id"], as_uuid(ctx["user"]["id"]))
    await db.execute("update memberships set role = 'owner' where id = $1", mid)
    await db.execute("update organizations set owner_id = $2 where id = $1",
                     ctx["org_id"], target["user_id"])
    await write_audit(ctx["org_id"], ctx["user"], "org.transfer_ownership",
                      target.get("invited_email"))
    return {"ok": True}


# ---------------- Audit ----------------
@router.get("/{orgId}/audit")
async def get_audit(ctx: dict = Depends(require_role("admin"))):
    logs = await db.fetch(
        """select * from audit_log where organization_id = $1
           order by at desc limit 200""",
        ctx["org_id"])
    return [serialize(l) for l in logs]


# ---------------- Secrets / Settings ----------------
# Per-org API keys use envelope encryption (see org_keys.py): values encrypted
# with the org's own DEK, DEK wrapped by the server master key. Only masked
# previews ever leave the server, and only org admins reach these endpoints.
class SecretsIn(BaseModel):
    anthropicKey: Optional[str] = None
    samKey: Optional[str] = None
    openaiKey: Optional[str] = None


def _masked_payload(values, extra=None):
    out = {
        "anthropicKey": org_keys.mask_secret(values["anthropic"]),
        "samKey": org_keys.mask_secret(values["sam"]),
        "openaiKey": org_keys.mask_secret(values["openai"]),
        "anthropicSet": bool(values["anthropic"]),
        "samSet": bool(values["sam"]),
        "openaiSet": bool(values["openai"]),
    }
    out.update(extra or {})
    return out


@router.get("/{orgId}/secrets")
async def get_secrets(ctx: dict = Depends(require_role("admin"))):
    values = await org_keys.get_keys(ctx["org_id"], ctx["user"], purpose="admin.view_masked")
    rec = await db.fetchrow(
        "select key_version, updated_at from org_secrets where organization_id = $1",
        ctx["org_id"])
    return _masked_payload(values, {
        "keyVersion": (rec or {}).get("key_version", 1),
        "updatedAt": serialize(rec or {}).get("updatedAt"),
    })


@router.put("/{orgId}/secrets")
async def update_secrets(body: SecretsIn, ctx: dict = Depends(require_role("admin"))):
    values = await org_keys.store_keys(
        ctx["org_id"],
        {"anthropic": body.anthropicKey, "sam": body.samKey, "openai": body.openaiKey},
        ctx["user"]["id"])
    await write_audit(ctx["org_id"], ctx["user"], "secrets.update", "API keys")
    return _masked_payload(values, {
        "ok": True,
        "validation": {
            "anthropic": "saved" if values["anthropic"] else "not set",
            "sam": "saved" if values["sam"] else "not set",
            "openai": "saved" if values["openai"] else "not set",
        },
    })


@router.post("/{orgId}/secrets/rotate-key")
async def rotate_secrets_key(ctx: dict = Depends(require_role("admin"))):
    """Re-encrypt this org's API keys under a brand-new data-encryption key."""
    version = await org_keys.rotate_key(ctx["org_id"], ctx["user"]["id"])
    await write_audit(ctx["org_id"], ctx["user"], "secrets.rotate_key", "API keys",
                      {"keyVersion": version})
    return {"ok": True, "keyVersion": version}
