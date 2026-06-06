import os
import secrets as pysecrets
from datetime import timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

from database import db
from utils import now_utc, serialize
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


async def _attach_pending_invites(user):
    """Activate any memberships invited by this user's email."""
    await db.memberships.update_many(
        {"invitedEmail": user["email"], "status": "invited"},
        {"$set": {"userId": ObjectId(user["id"]), "status": "active"}},
    )


async def _user_payload(user_doc):
    u = serialize(user_doc)
    u.pop("password_hash", None)
    memberships = await db.memberships.find(
        {"userId": ObjectId(u["id"]), "status": "active"}).to_list(100)
    orgs = []
    for m in memberships:
        org = await db.organizations.find_one({"_id": m["organizationId"]})
        if org:
            orgs.append({"id": str(org["_id"]), "name": org["name"], "role": m["role"]})
    u["organizations"] = orgs
    return u


@router.post("/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    doc = {
        "email": email,
        "name": body.name.strip(),
        "password_hash": hash_password(body.password),
        "emailVerified": False,
        "created_at": now_utc(),
    }
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    await _attach_pending_invites({"id": str(res.inserted_id), "email": email})
    # email verification (mocked: link surfaced in response)
    token = pysecrets.token_urlsafe(32)
    await db.email_verify_tokens.insert_one({
        "token": token, "userId": res.inserted_id,
        "expires_at": now_utc() + timedelta(days=2), "used": False,
    })
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    print(f"[EMAIL-MOCK] Verify link for {email}: {verify_url}")
    set_auth_cookies(response, str(res.inserted_id), email)
    payload = await _user_payload(doc)
    payload["verifyUrl"] = verify_url
    return payload


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if rec and rec.get("count", 0) >= MAX_ATTEMPTS:
        if rec.get("lock_until") and rec["lock_until"] > now_utc():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1},
             "$set": {"lock_until": now_utc() + timedelta(minutes=LOCKOUT_MIN)}},
            upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    await _attach_pending_invites({"id": str(user["_id"]), "email": email})
    set_auth_cookies(response, str(user["_id"]), email)
    return await _user_payload(user)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    return await _user_payload(doc)


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
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(str(user["_id"]), user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=True,
                            samesite="none", max_age=12 * 3600, path="/")
        return {"ok": True}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    resp = {"ok": True, "message": "If the account exists, a reset link has been generated."}
    if not user:
        return resp
    token = pysecrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "token": token, "userId": user["_id"],
        "expires_at": now_utc() + timedelta(hours=1), "used": False,
    })
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    print(f"[EMAIL-MOCK] Reset link for {email}: {reset_url}")
    resp["resetUrl"] = reset_url  # surfaced in-app while email is mocked
    return resp


@router.post("/reset-password")
async def reset_password(body: ResetIn):
    rec = await db.password_reset_tokens.find_one({"token": body.token})
    if not rec or rec.get("used") or rec["expires_at"] < now_utc():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    await db.users.update_one({"_id": rec["userId"]},
                              {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
    return {"ok": True}


@router.post("/verify-email")
async def verify_email(body: VerifyIn):
    rec = await db.email_verify_tokens.find_one({"token": body.token})
    if not rec or rec.get("used") or rec["expires_at"] < now_utc():
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    await db.users.update_one({"_id": rec["userId"]}, {"$set": {"emailVerified": True}})
    await db.email_verify_tokens.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
    return {"ok": True}


@router.post("/resend-verification")
async def resend_verification(user: dict = Depends(get_current_user)):
    token = pysecrets.token_urlsafe(32)
    await db.email_verify_tokens.insert_one({
        "token": token, "userId": ObjectId(user["id"]),
        "expires_at": now_utc() + timedelta(days=2), "used": False,
    })
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    print(f"[EMAIL-MOCK] Resend verify for {user['email']}: {verify_url}")
    return {"ok": True, "verifyUrl": verify_url}
