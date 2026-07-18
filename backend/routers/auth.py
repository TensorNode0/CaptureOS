"""Auth surface for a Supabase-Auth app.

Identity/passwords/email are owned by Supabase (GoTrue). The frontend signs in
with supabase-js and calls these endpoints with the Supabase access token:
  GET    /auth/me         → the app profile payload (orgs + roles) for the token
  POST   /auth/logout     → no-op (supabase-js clears the session client-side)
  POST   /auth/refresh    → no-op (supabase-js auto-refreshes the session)
  DELETE /auth/me         → hard-delete the user's account + owned orgs

/auth/test-login exists only when AUTH_TEST_MODE=1 (tests/local demo): it mints
a Supabase-shaped token and auto-provisions the profile, so the suite can run
without a live Supabase project. It is never enabled in production.
"""
import os
import io
import json
import zipfile
import httpx
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, EmailStr, Field

import database as db
from utils import serialize, as_uuid, now_utc
from auth_utils import (get_current_user, mint_supabase_token, provision_profile,
                        AUTH_TEST_MODE, SUPABASE_URL)
from domain import write_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _user_payload(user_row):
    u = serialize(user_row)
    u.pop("passwordHash", None)
    orgs = await db.fetch(
        """select o.id, o.name, m.role
           from memberships m join organizations o on o.id = m.organization_id
           where m.user_id = $1 and m.status = 'active'
           order by o.created_at""",
        as_uuid(u["id"]))
    u["organizations"] = [
        {"id": str(o["id"]), "name": o["name"], "role": o["role"]} for o in orgs
    ]
    pending = await db.fetch(
        """select o.id, o.name
           from memberships m join organizations o on o.id = m.organization_id
           where m.user_id = $1 and m.status = 'pending'""",
        as_uuid(u["id"]))
    u["pendingOrganizations"] = [
        {"id": str(o["id"]), "name": o["name"]} for o in pending
    ]
    return u


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    row = await db.fetchrow("select * from users where id = $1", as_uuid(user["id"]))
    return await _user_payload(row)


@router.post("/logout")
async def logout():
    # Session lives in supabase-js on the client; nothing to clear server-side.
    return {"ok": True}


@router.post("/refresh")
async def refresh():
    # supabase-js refreshes the session automatically; kept for the idle-timer.
    return {"ok": True}


class TestLoginIn(BaseModel):
    email: EmailStr
    name: str = Field(default="", max_length=120)


@router.post("/test-login")
async def test_login(body: TestLoginIn):
    """Mint a token + ensure a profile exists. AUTH_TEST_MODE only."""
    if not AUTH_TEST_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    import uuid
    email = body.email.lower().strip()
    existing = await db.fetchrow("select * from users where email = $1", email)
    auth_uid = existing["auth_uid"] if existing and existing.get("auth_uid") \
        else uuid.uuid5(uuid.NAMESPACE_DNS, email)
    user = await provision_profile(str(auth_uid), email, body.name)
    payload = await _user_payload(user)
    payload["accessToken"] = mint_supabase_token(user["auth_uid"], email)
    return payload




class DeleteAccountIn(BaseModel):
    """Body for the destructive DELETE /auth/me request.

    `confirmEmail` MUST match the caller's own email (case-insensitive) — this
    is the anti-mis-click guard shown in the UI. `reason` is optional feedback
    stored on the audit trail so we can learn why users leave."""
    confirmEmail: EmailStr
    reason: str = Field(default="", max_length=500)


async def _delete_supabase_auth_user(auth_uid: str) -> None:
    """Remove the user's row from Supabase's auth.users via the Admin API.
    Uses the service_role key (server-side only). Failure is fatal — if we
    can't delete the auth identity, the user could still log back in and see
    a broken (profile-less) app, which is worse than a rolled-back delete."""
    if not (SUPABASE_URL and auth_uid):
        raise HTTPException(status_code=500,
            detail="SUPABASE_URL not configured; cannot finalize account deletion.")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not service_key:
        raise HTTPException(status_code=500,
            detail="SUPABASE_SERVICE_ROLE_KEY not configured; cannot delete auth user.")
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{auth_uid}"
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.delete(url, headers=headers)
    # 200 = deleted, 404 = already gone (idempotent success), anything else = fail
    if resp.status_code not in (200, 204, 404):
        raise HTTPException(status_code=502,
            detail=f"Supabase admin API rejected delete ({resp.status_code}): {resp.text[:300]}")


@router.delete("/me")
async def delete_account(body: DeleteAccountIn, user: dict = Depends(get_current_user)):
    """Hard-delete the current user's account and their data.

    Behavior:
      - Orgs the user SOLELY owns are deleted entirely (all opportunities,
        proposals, secrets, venture docs, etc. cascade with them).
      - Orgs with other active members: user's membership is dropped; if the
        user was the owner, ownership transfers to the oldest remaining active
        owner or (fallback) any remaining active admin/editor.
      - Historical audit references (created_by/submitted_by/decided_by) become
        NULL thanks to migration 0019 — deleted-user rows aren't hidden.
      - Supabase auth.users record is deleted so the email is fully released.

    Paid-tier subscription cancellation (Stripe) is queued via
    account_deletion_requests when Phase 2 (billing) is in place; today it's a
    no-op — deletion is immediate."""
    email = (user.get("email") or "").lower().strip()
    if not email or email != body.confirmEmail.lower().strip():
        raise HTTPException(status_code=400,
            detail="Confirmation email does not match the signed-in account.")
    row = await db.fetchrow("select * from users where id = $1", as_uuid(user["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    auth_uid = row.get("auth_uid")

    # Snapshot memberships so we know what to delete vs. drop.
    memberships = await db.fetch(
        """select m.organization_id, m.role, m.status, o.name as org_name
             from memberships m
             join organizations o on o.id = m.organization_id
             where m.user_id = $1""",
        as_uuid(user["id"]))
    orgs_to_wipe = []      # orgs where this user is the only active member
    orgs_to_leave = []     # orgs with other active members
    for m in memberships:
        others = await db.fetchval(
            """select count(*) from memberships
                 where organization_id = $1 and user_id <> $2 and status = 'active'""",
            m["organization_id"], as_uuid(user["id"]))
        if others == 0:
            orgs_to_wipe.append(m)
        else:
            orgs_to_leave.append(m)

    # Log the intent before mutating anything — if the delete fails midway we
    # want a record of *why* it was attempted.
    await db.execute(
        """insert into account_deletion_requests
              (user_id, email, reason, orgs_deleted, memberships_dropped, status)
           values ($1, $2, $3, $4, $5, 'pending')""",
        as_uuid(user["id"]), email, (body.reason or "")[:500],
        len(orgs_to_wipe), len(orgs_to_leave))

    # 1) Delete solely-owned orgs (cascades all org data).
    for m in orgs_to_wipe:
        await write_audit(str(m["organization_id"]), user, "account.delete.org_wiped",
                          m["org_name"], {"reason": "sole active member"})
        await db.execute("delete from organizations where id = $1", m["organization_id"])
    # 2) Drop memberships from orgs that survive (transfer ownership if needed).
    for m in orgs_to_leave:
        if m["role"] == "owner":
            # Prefer promoting the oldest remaining active owner, else an admin,
            # else an editor. Guarantees the org always has a signed owner.
            new_owner = await db.fetchrow(
                """select m.user_id from memberships m
                     where m.organization_id = $1
                       and m.user_id <> $2 and m.status = 'active'
                     order by case m.role
                                  when 'owner'  then 0
                                  when 'admin'  then 1
                                  when 'editor' then 2
                                  else 3 end,
                              m.joined_at
                     limit 1""",
                m["organization_id"], as_uuid(user["id"]))
            if new_owner:
                await db.execute(
                    """update memberships set role = 'owner'
                         where organization_id = $1 and user_id = $2""",
                    m["organization_id"], new_owner["user_id"])
                await db.execute(
                    """update organizations set owner_id = $2
                         where id = $1""",
                    m["organization_id"], new_owner["user_id"])
        await db.execute(
            """delete from memberships
                 where organization_id = $1 and user_id = $2""",
            m["organization_id"], as_uuid(user["id"]))

    # 3) Delete the public.users row. Audit rows keyed by org (not user_id)
    #    stay; other user refs get NULLed via migration 0019.
    await db.execute("delete from users where id = $1", as_uuid(user["id"]))

    # 3b) Cancel any active Stripe subscription so the user is not billed
    #    after their account is gone. Best-effort: log and continue on failure —
    #    Stripe support can be involved manually if the API call errors.
    try:
        import stripe as _stripe
        _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or ""
        sub_row = await db.fetchrow(
            """select stripe_subscription_id from user_subscriptions
                 where user_id = $1 and stripe_subscription_id <> ''""",
            as_uuid(user["id"]))
        if sub_row and _stripe.api_key:
            try:
                _stripe.Subscription.cancel(sub_row["stripe_subscription_id"])
            except _stripe.error.StripeError:
                pass  # webhook will still fire later; nothing to block on
    except ImportError:
        pass

    # 4) Delete the Supabase auth identity so the email is fully released
    #    and the user gets a "user not found" if they try to sign in again.
    if auth_uid:
        try:
            await _delete_supabase_auth_user(str(auth_uid))
        except HTTPException:
            await db.execute(
                """update account_deletion_requests set status = 'failed',
                         completed_at = $2
                     where user_id = $1 and status = 'pending'""",
                as_uuid(user["id"]), now_utc())
            raise

    await db.execute(
        """update account_deletion_requests set status = 'completed',
               completed_at = $2
             where user_id = $1 and status = 'pending'""",
        as_uuid(user["id"]), now_utc())
    return {"ok": True,
            "orgsDeleted": len(orgs_to_wipe),
            "membershipsDropped": len(orgs_to_leave)}


# ---------------------- Export my data (GDPR-friendly) ----------------------

def _rows_to_json(rows):
    """Turn asyncpg Records into JSON-safe dicts (dates → ISO, uuid → str)."""
    return [json.loads(json.dumps(serialize(r), default=str)) for r in rows]


@router.get("/me/export")
async def export_my_data(user: dict = Depends(get_current_user)):
    """Return a ZIP of everything the current user can see: their profile,
    every org they belong to, and every record in those orgs (opportunities,
    proposals, capabilities, competitive reports, venture docs, uploaded
    file metadata). Binary file contents are NOT bundled — they're linked
    to their Supabase Storage `storage_path` in `org_files.json` so users
    can pull them via signed URLs. This keeps the ZIP small and predictable.

    The output is served inline so the browser downloads it as
    captureagent-export-YYYYMMDD.zip.
    """
    uid = as_uuid(user["id"])
    profile_row = await db.fetchrow("select * from users where id = $1", uid)
    if not profile_row:
        raise HTTPException(status_code=404, detail="Profile not found")

    memberships = await db.fetch(
        """select m.organization_id, m.role, m.created_at as joined_at,
                  o.name as org_name
             from memberships m
             join organizations o on o.id = m.organization_id
             where m.user_id = $1 and m.status = 'active'
             order by o.created_at""",
        uid)

    sub_row = await db.fetchrow(
        "select * from user_subscriptions where user_id = $1", uid)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", (
            "CaptureAgent data export\n"
            f"Generated: {now_utc().isoformat()}\n"
            f"Account: {user.get('email', '')}\n\n"
            "This archive contains every record you have visibility into on\n"
            "captureagent.us at the time of export. Uploaded file contents\n"
            "(PDFs, decks, spreadsheets) are NOT embedded — see\n"
            "`org_files.json` for each org and use the corresponding signed\n"
            "URL endpoint (/api/orgs/<orgId>/files/<fileId>/url) to fetch the\n"
            "binaries individually.\n"
        ))
        # Redact the legacy password_hash column — Supabase Auth owns the
        # password now anyway, and the ZIP is exported over an authenticated
        # endpoint that the account owner shouldn't accidentally re-share.
        prof = _rows_to_json([profile_row])[0]
        prof.pop("password_hash", None)
        prof.pop("passwordHash", None)
        zf.writestr("account/profile.json", json.dumps(prof, indent=2))
        zf.writestr("account/subscription.json", json.dumps(
            (_rows_to_json([sub_row])[0] if sub_row else {}), indent=2))
        zf.writestr("account/memberships.json", json.dumps(
            _rows_to_json(memberships), indent=2))

        for m in memberships:
            org_id = m["organization_id"]
            slug = f"organizations/{org_id}"
            org = await db.fetchrow(
                "select * from organizations where id = $1", org_id)
            profile = await db.fetchrow(
                "select * from org_profiles where organization_id = $1", org_id)
            members = await db.fetch(
                """select m.role, m.status, m.created_at as joined_at, u.email, u.name
                     from memberships m
                     left join users u on u.id = m.user_id
                     where m.organization_id = $1
                     order by m.created_at""", org_id)
            opps = await db.fetch(
                "select * from opportunities where organization_id = $1", org_id)
            props = await db.fetch(
                """select p.*, o.title as opportunity_title
                     from proposals p
                     join opportunities o on o.id = p.opportunity_id
                     where p.organization_id = $1""", org_id)
            prop_docs = await db.fetch(
                """select d.* from proposal_documents d
                     join proposals p on p.id = d.proposal_id
                     where p.organization_id = $1""", org_id)
            caps = await db.fetch(
                "select id, opportunity_id, content, created_at, updated_at from capabilities where organization_id = $1", org_id)
            comp_reports = await db.fetch(
                "select * from competitive_reports where organization_id = $1", org_id)
            venture_docs = await db.fetch(
                "select * from venture_docs where organization_id = $1", org_id)
            org_files = await db.fetch(
                """select id, category, entity_type, entity_id, filename,
                          mime, size_bytes, storage_path, uploaded_by, created_at
                     from organization_files where organization_id = $1""", org_id)
            audits = await db.fetch(
                """select * from audit_log where organization_id = $1
                     order by at desc limit 5000""", org_id)

            zf.writestr(f"{slug}/organization.json",
                        json.dumps(_rows_to_json([org])[0] if org else {}, indent=2))
            zf.writestr(f"{slug}/profile.json",
                        json.dumps((_rows_to_json([profile])[0] if profile else {}), indent=2))
            zf.writestr(f"{slug}/members.json",
                        json.dumps(_rows_to_json(members), indent=2))
            zf.writestr(f"{slug}/opportunities.json",
                        json.dumps(_rows_to_json(opps), indent=2))
            zf.writestr(f"{slug}/proposals.json",
                        json.dumps(_rows_to_json(props), indent=2))
            zf.writestr(f"{slug}/proposal_documents.json",
                        json.dumps(_rows_to_json(prop_docs), indent=2))
            zf.writestr(f"{slug}/capabilities.json",
                        json.dumps(_rows_to_json(caps), indent=2))
            zf.writestr(f"{slug}/competitive_reports.json",
                        json.dumps(_rows_to_json(comp_reports), indent=2))
            zf.writestr(f"{slug}/venture_docs.json",
                        json.dumps(_rows_to_json(venture_docs), indent=2))
            zf.writestr(f"{slug}/org_files.json",
                        json.dumps(_rows_to_json(org_files), indent=2))
            zf.writestr(f"{slug}/audit_log.json",
                        json.dumps(_rows_to_json(audits), indent=2))

    # No audit row at the user level — audit_log rows are org-scoped and this
    # export can span multiple orgs. Per-org read is authorized by membership;
    # the request will show up in server access logs.
    stamp = now_utc().strftime("%Y%m%d")
    filename = f"captureagent-export-{stamp}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
