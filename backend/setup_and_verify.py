"""Set ONE password for every real user and PROVE each can sign in — no guessing.

For each real user (test accounts skipped):
  1. (re)create the Supabase Auth account, set USER_PASSWORD, confirm the email
     (service-role admin API);
  2. immediately SIGN IN with that email+password using the anon key — the exact
     same call the website makes — and report VERIFIED or the precise error.

Run (from repo root; pick an 8+ char letters-and-numbers-only password):
  docker run --rm --env-file backend/.env -e USER_PASSWORD="Captureagent2026" \
    -v "${PWD}/backend:/app" -w /app python:3.12-slim bash -c \
    "pip install -q supabase asyncpg && python setup_and_verify.py"

Requires env: DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
SUPABASE_ANON_KEY, USER_PASSWORD.
"""
import os
import sys
import asyncio

import asyncpg
from supabase import create_client

SKIP_SUFFIXES = ("@testmail.dev",)
SKIP_EMAILS = {"diag-ca-2026@captureagent.us"}


def _real(email: str) -> bool:
    e = (email or "").lower()
    return bool(e) and e not in SKIP_EMAILS and not any(e.endswith(s) for s in SKIP_SUFFIXES)


def _find_uid(admin, email):
    try:
        res = admin.auth.admin.list_users()
        items = res if isinstance(res, list) else (getattr(res, "users", None) or [])
        for u in items:
            if (getattr(u, "email", "") or "").lower() == email:
                return u.id
    except Exception:  # noqa: BLE001
        pass
    return None


async def main():
    pw = os.environ.get("USER_PASSWORD", "").strip()
    if len(pw) < 8 or not pw.isalnum():
        sys.exit("Set env USER_PASSWORD to an 8+ character LETTERS-AND-NUMBERS-only value.")

    db = os.environ["DATABASE_URL"]
    url = os.environ["SUPABASE_URL"].split("/rest/")[0].split("/auth/")[0].rstrip("/")
    service = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    anon = os.environ["SUPABASE_ANON_KEY"]

    admin = create_client(url, service)
    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch("select id, email, name from users order by created_at")
        users = [r for r in rows if _real(r["email"])]
        print(f"Processing {len(users)} real users...\n")
        verified = failed = 0
        for r in users:
            email = r["email"].lower().strip()
            uid = None
            # 1) ensure the account exists with this password, email confirmed
            try:
                resp = admin.auth.admin.create_user({
                    "email": email, "password": pw, "email_confirm": True,
                    "user_metadata": {"full_name": r["name"] or ""}})
                uid = resp.user.id
            except Exception:  # already exists → set password + confirm
                uid = _find_uid(admin, email)
                if uid:
                    admin.auth.admin.update_user_by_id(
                        uid, {"password": pw, "email_confirm": True})
            if uid:
                await conn.execute(
                    "update users set auth_uid = $1 where id = $2", uid, r["id"])

            # 2) PROVE sign-in works — same path as the website
            try:
                res = create_client(url, anon).auth.sign_in_with_password(
                    {"email": email, "password": pw})
                if getattr(res, "session", None):
                    verified += 1
                    print(f"  VERIFIED  can sign in: {email}")
                else:
                    failed += 1
                    print(f"  NO SESSION (unexpected): {email}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  LOGIN FAILED: {email}: {e}")
        print(f"\nDone. verified={verified} failed={failed}")
        if verified and not failed:
            print("\nPROVEN: every real user can sign in at captureagent.us with "
                  "their email and the password you set above.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
