"""Auth surface for a Supabase-Auth app.

Identity/passwords/email are owned by Supabase (GoTrue). The frontend signs in
with supabase-js and calls these endpoints with the Supabase access token:
  GET  /auth/me         → the app profile payload (orgs + roles) for the token
  POST /auth/logout     → no-op (supabase-js clears the session client-side)
  POST /auth/refresh    → no-op (supabase-js auto-refreshes the session)

/auth/test-login exists only when AUTH_TEST_MODE=1 (tests/local demo): it mints
a Supabase-shaped token and auto-provisions the profile, so the suite can run
without a live Supabase project. It is never enabled in production.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

import database as db
from utils import serialize, as_uuid
from auth_utils import (get_current_user, mint_supabase_token, provision_profile,
                        AUTH_TEST_MODE)

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
