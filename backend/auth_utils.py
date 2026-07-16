"""Authentication against Supabase Auth (GoTrue).

Identity, passwords, email confirmation, and password reset are owned by
Supabase Auth. The frontend authenticates with supabase-js and sends the
Supabase access token as `Authorization: Bearer <jwt>`. This module validates
that JWT (HS256, signed with the project's SUPABASE_JWT_SECRET) and resolves it
to the app's `public.users` profile row via `auth_uid`.

`public.users` is a profile mirror: the app's canonical id for every foreign
key stays in `public.users(id)`, while `auth_uid` links to `auth.users(id)`.
On first sight of a new `auth_uid`, the profile row is provisioned and any
pending org invites addressed to that email are activated.

bcrypt helpers remain for the one-off migration window only.
"""
import os
import uuid
import jwt
import bcrypt
from fastapi import Request, HTTPException

import database as db
from utils import serialize, as_uuid, now_utc

JWT_ALGORITHM = "HS256"

# Supabase signs user JWTs with the project JWT secret. In tests this is any
# local value shared between the test-token minter and this validator.
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
# Project URL is used to reach the JWKS endpoint when the project signs tokens
# with asymmetric keys (RS256/ES256) instead of the shared HS256 secret.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Supabase anon key is sent as `apikey` on JWKS fetches. The JWKS endpoint is
# public, but Supabase's Cloudflare edge may 401 requests from certain egress
# IPs without this header — presenting the anon key marks the caller as a
# legitimate Supabase project client and bypasses that edge policy.
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
# Test/demo convenience: when on, /auth/test-login can mint tokens and
# auto-provision profiles without a live Supabase project. Never set in prod.
AUTH_TEST_MODE = os.environ.get("AUTH_TEST_MODE", "0") == "1"


# ── bcrypt (migration window only) ────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), (hashed or "").encode("utf-8"))
    except Exception:
        return False


# ── Supabase JWT handling ─────────────────────────────────────────────────────
def _secret() -> str:
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500,
                            detail="Auth is not configured (SUPABASE_JWT_SECRET missing).")
    return SUPABASE_JWT_SECRET


_jwks_cache = None      # cached JWK set (dict from Supabase JWKS endpoint)
_jwks_fetched_at = 0.0  # unix ts of last successful fetch


def _fetch_jwks() -> dict | None:
    """Fetch (and cache) the Supabase project JWK set.

    We fetch with httpx directly instead of PyJWKClient's built-in urllib
    because Supabase's Cloudflare edge is picky: it 401s bare requests from
    some cloud egress IPs and 404s certain header combinations. Sending only
    the `apikey` header + a normal User-Agent is what actually works in prod.
    Cached for 1 hour — signing keys rotate rarely, and this keeps auth fast."""
    import time, httpx
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache and (time.time() - _jwks_fetched_at) < 3600:
        return _jwks_cache
    if not SUPABASE_URL:
        return None
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    headers = {"User-Agent": "captureagent-backend/1.0",
               "Accept": "application/json"}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
    resp = httpx.get(url, headers=headers, timeout=10.0)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_fetched_at = time.time()
    return _jwks_cache


def _jwk_for_kid(kid: str):
    """Resolve a signing key from the cached JWK set by `kid`."""
    from jwt import PyJWK
    jwks = _fetch_jwks() or {}
    for entry in jwks.get("keys", []):
        if entry.get("kid") == kid:
            return PyJWK.from_dict(entry).key
    # kid not found → force a cache refresh once
    global _jwks_cache, _jwks_fetched_at
    _jwks_cache = None
    _jwks_fetched_at = 0.0
    jwks = _fetch_jwks() or {}
    for entry in jwks.get("keys", []):
        if entry.get("kid") == kid:
            return PyJWK.from_dict(entry).key
    return None


def decode_supabase_token(token: str) -> dict:
    """Validate a Supabase access token, supporting BOTH signing schemes:
    the legacy shared HS256 secret and asymmetric (RS256/ES256) signing keys
    via the project's JWKS endpoint — so it works whichever the project uses,
    now or after a future migration. Audience is not enforced (Supabase uses
    aud='authenticated'); signature + expiry are."""
    opts = {"verify_aud": False}
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")
    if alg == "HS256" and SUPABASE_JWT_SECRET:
        try:
            return jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"],
                              options=opts)
        except jwt.InvalidTokenError:
            pass  # project may have switched to asymmetric signers — try JWKS
    # Token is asymmetrically signed (RS256/ES256): must use JWKS.
    if alg in ("RS256", "ES256"):
        if not SUPABASE_URL:
            raise HTTPException(status_code=500, detail=(
                f"Auth is not configured: token uses {alg} but SUPABASE_URL is "
                f"not set in the backend environment (needed to fetch JWKS)."))
        kid = header.get("kid")
        key = _jwk_for_kid(kid)
        if key is None:
            raise HTTPException(status_code=401, detail=(
                f"Signing key kid={kid!r} not found in Supabase JWKS"))
        return jwt.decode(token, key, algorithms=["RS256", "ES256"], options=opts)
    return jwt.decode(token, _secret(), algorithms=["HS256"], options=opts)


def mint_supabase_token(auth_uid: str, email: str) -> str:
    """Mint a Supabase-shaped access token. Test/demo only — real tokens come
    from GoTrue. Signed with the same secret this module validates against."""
    from datetime import datetime, timezone, timedelta
    payload = {
        "sub": str(auth_uid),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def _bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    # transitional: also accept a token placed in the access_token cookie
    return request.cookies.get("access_token", "")


async def provision_profile(auth_uid: str, email: str, name: str = "") -> dict:
    """Get-or-create the profile row for a Supabase user, activating any org
    invites addressed to this email on first creation."""
    email = (email or "").lower().strip()
    row = await db.fetchrow("select * from users where auth_uid = $1", as_uuid(auth_uid))
    if row:
        return row
    # An older row may exist by email (e.g. migrated) without auth_uid linked yet.
    row = await db.fetchrow("select * from users where email = $1", email)
    if row:
        row = await db.fetchrow(
            "update users set auth_uid = $2, email_verified = true where id = $1 returning *",
            row["id"], as_uuid(auth_uid))
        return row
    row = await db.fetchrow(
        """insert into users (email, name, auth_uid, email_verified)
           values ($1, $2, $3, true) returning *""",
        email, (name or email.split("@")[0]).strip(), as_uuid(auth_uid))
    await db.execute(
        """update memberships set user_id = $1, status = 'active'
           where invited_email = $2 and status = 'invited'""",
        row["id"], email)
    return row


async def get_current_user(request: Request) -> dict:
    token = _bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = decode_supabase_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except HTTPException:
        raise
    except jwt.PyJWTError as e:
        # Surface enough context to diagnose prod misconfig without dumping the
        # full token. Includes the JWT alg (so we know which verification path
        # should apply) and whether SUPABASE_URL/SUPABASE_JWT_SECRET are set.
        try:
            alg = jwt.get_unverified_header(token).get("alg", "?")
        except Exception:
            alg = "?"
        raise HTTPException(status_code=401, detail=(
            f"Invalid token (alg={alg}, jwt_err={type(e).__name__}: {e}; "
            f"supabase_url_set={bool(SUPABASE_URL)}, "
            f"jwt_secret_set={bool(SUPABASE_JWT_SECRET)})"
        ))
    auth_uid = claims.get("sub")
    if not as_uuid(auth_uid):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    name = ((claims.get("user_metadata") or {}).get("full_name")
            or (claims.get("user_metadata") or {}).get("name") or "")
    user = await provision_profile(auth_uid, claims.get("email", ""), name)
    out = serialize(user)
    out.pop("passwordHash", None)
    return out
