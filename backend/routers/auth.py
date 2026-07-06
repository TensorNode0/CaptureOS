import os
import secrets as pysecrets
from datetime import timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field

import database as db
import email_service
from utils import now_utc, serialize, as_uuid
from auth_utils import (hash_password, verify_password, set_auth_cookies,
                        clear_auth_cookies, get_current_user, create_access_token)

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_ATTEMPTS = 5
LOCKOUT_MIN = 15
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class VerifyIn(BaseModel):
    token: str


async def _attach_pending_invites(user_id, email):
    """Activate any memberships invited by this user's email."""
    await db.execute(
        """update memberships set user_id = $1, status = 'active'
           where invited_email = $2 and status = 'invited'""",
        as_uuid(user_id), email)


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


@router.post("/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower().strip()
    if await db.fetchrow("select id from users where email = $1", email):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    user = await db.fetchrow(
        """insert into users (email, name, password_hash, email_verified)
           values ($1, $2, $3, false) returning *""",
        email, body.name.strip(), hash_password(body.password))
    await _attach_pending_invites(user["id"], email)
    token = pysecrets.token_urlsafe(32)
    await db.execute(
        """insert into email_verify_tokens (token, user_id, expires_at)
           values ($1, $2, $3)""",
        token, user["id"], now_utc() + timedelta(days=2))
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    try:
        await email_service.send_verify(email, verify_url)
    except Exception as e:  # account still created; user can resend
        print(f"[EMAIL-ERROR] verify send failed for {email}: {e}")
    set_auth_cookies(response, str(user["id"]), email)
    payload = await _user_payload(user)
    if not email_service.configured():
        payload["verifyUrl"] = verify_url  # dev only — never in production
    return payload


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    rec = await db.fetchrow("select * from login_attempts where identifier = $1", identifier)
    if rec and rec.get("count", 0) >= MAX_ATTEMPTS:
        if rec.get("lock_until") and rec["lock_until"] > now_utc():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    user = await db.fetchrow("select * from users where email = $1", email)
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.execute(
            """insert into login_attempts (identifier, count, lock_until)
               values ($1, 1, $2)
               on conflict (identifier) do update
               set count = login_attempts.count + 1, lock_until = excluded.lock_until""",
            identifier, now_utc() + timedelta(minutes=LOCKOUT_MIN))
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.execute("delete from login_attempts where identifier = $1", identifier)
    await _attach_pending_invites(user["id"], email)
    set_auth_cookies(response, str(user["id"]), email)
    return await _user_payload(user)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    row = await db.fetchrow("select * from users where id = $1", as_uuid(user["id"]))
    return await _user_payload(row)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    import jwt
    from auth_utils import _secret, JWT_ALGORITHM
    tok = request.cookies.get("refresh_token")
    if not tok:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(tok, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.fetchrow("select * from users where id = $1",
                                 as_uuid(payload.get("sub")))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(str(user["id"]), user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=True,
                            samesite="none", max_age=12 * 3600, path="/")
        return {"ok": True}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.lower().strip()
    user = await db.fetchrow("select * from users where email = $1", email)
    resp = {"ok": True, "message": "If the account exists, a reset link has been generated."}
    if not user:
        return resp
    token = pysecrets.token_urlsafe(32)
    await db.execute(
        """insert into password_reset_tokens (token, user_id, expires_at)
           values ($1, $2, $3)""",
        token, user["id"], now_utc() + timedelta(hours=1))
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    try:
        await email_service.send_reset(email, reset_url)
    except Exception as e:
        print(f"[EMAIL-ERROR] reset send failed for {email}: {e}")
    if not email_service.configured():
        resp["resetUrl"] = reset_url  # dev only — never in production
    return resp


@router.post("/reset-password")
async def reset_password(body: ResetIn):
    rec = await db.fetchrow("select * from password_reset_tokens where token = $1", body.token)
    if not rec or rec.get("used") or rec["expires_at"] < now_utc():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    await db.execute("update users set password_hash = $1 where id = $2",
                     hash_password(body.password), rec["user_id"])
    await db.execute("update password_reset_tokens set used = true where id = $1", rec["id"])
    return {"ok": True}


@router.post("/verify-email")
async def verify_email(body: VerifyIn):
    rec = await db.fetchrow("select * from email_verify_tokens where token = $1", body.token)
    if not rec or rec.get("used") or rec["expires_at"] < now_utc():
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    await db.execute("update users set email_verified = true where id = $1", rec["user_id"])
    await db.execute("update email_verify_tokens set used = true where id = $1", rec["id"])
    return {"ok": True}


@router.post("/resend-verification")
async def resend_verification(user: dict = Depends(get_current_user)):
    token = pysecrets.token_urlsafe(32)
    await db.execute(
        """insert into email_verify_tokens (token, user_id, expires_at)
           values ($1, $2, $3)""",
        token, as_uuid(user["id"]), now_utc() + timedelta(days=2))
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    try:
        await email_service.send_verify(user["email"], verify_url)
    except Exception as e:
        print(f"[EMAIL-ERROR] resend verify failed for {user['email']}: {e}")
        raise HTTPException(status_code=502, detail="Could not send the email. Try again.")
    out = {"ok": True}
    if not email_service.configured():
        out["verifyUrl"] = verify_url  # dev only
    return out
