"""Migrate / repair Supabase Auth accounts for existing public.users rows.

Every mode links public.users.auth_uid to the Supabase Auth account so all of a
user's data stays attached (public.users.id never changes).

Modes:
  --dry-run        list who would be processed; write nothing, email nothing.
  (default)        create + link only users that were never migrated.
  --repair         reprocess EVERY user (re-create deleted accounts, re-link).
  --set-password   IMMEDIATE ACCESS, NO EMAIL: set env TEMP_PASSWORD on every
                   account (create if missing) so users can sign in right now
                   and change it afterward.

Run in Docker (from repo root), e.g. immediate access for everyone:
  docker run --rm --env-file backend/.env -e TEMP_PASSWORD="ChangeMe#2026!" \
    -v "${PWD}/backend:/app" -w /app python:3.12-slim bash -c \
    "pip install -q supabase asyncpg && python migrate_to_supabase_auth.py --set-password"

Requires env: DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
(+ TEMP_PASSWORD for --set-password).
"""
import os
import sys
import asyncio

import asyncpg
from supabase import create_client

DRY = "--dry-run" in sys.argv
REPAIR = "--repair" in sys.argv
SET_PW = "--set-password" in sys.argv


def _require(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"Missing required env var: {name}")
    return v


def _find_uid(sb, email):
    """Find an existing auth user's id by email (list is small)."""
    try:
        res = sb.auth.admin.list_users()
        items = res if isinstance(res, list) else (getattr(res, "users", None) or [])
        for u in items:
            if (getattr(u, "email", "") or "").lower() == email:
                return u.id
    except Exception:  # noqa: BLE001
        pass
    return None


async def main():
    database_url = _require("DATABASE_URL")
    supabase_url = _require("SUPABASE_URL").split("/rest/")[0].split("/auth/")[0].rstrip("/")
    service_role = _require("SUPABASE_SERVICE_ROLE_KEY")
    temp_pw = os.environ.get("TEMP_PASSWORD", "").strip()
    if SET_PW and len(temp_pw) < 8:
        sys.exit("--set-password needs env TEMP_PASSWORD (>= 8 chars).")

    conn = await asyncpg.connect(database_url)
    try:
        where = "" if (REPAIR or SET_PW) else "where auth_uid is null"
        rows = await conn.fetch(
            f"select id, email, name from users {where} order by created_at")
        print(f"{len(rows)} user(s) to process.")

        if DRY:
            for r in rows:
                print(f"  [dry-run] would process: {r['email']}")
            print("DRY RUN complete — nothing was created, linked, or emailed.")
            return

        sb = create_client(supabase_url, service_role)
        ok = failed = 0
        for r in rows:
            email = (r["email"] or "").lower().strip()
            meta = {"full_name": r["name"] or ""}
            try:
                uid = None
                if SET_PW:
                    try:
                        resp = sb.auth.admin.create_user({
                            "email": email, "password": temp_pw,
                            "email_confirm": True, "user_metadata": meta})
                        uid = resp.user.id
                    except Exception:  # exists → set its password + confirm email
                        uid = _find_uid(sb, email)
                        if uid:
                            sb.auth.admin.update_user_by_id(
                                uid, {"password": temp_pw, "email_confirm": True})
                    if not uid:
                        raise RuntimeError("could not create or find the auth user")
                    note = "password set"
                else:
                    try:
                        sb.auth.admin.create_user({
                            "email": email, "email_confirm": True,
                            "user_metadata": meta})
                    except Exception:  # already exists
                        pass
                    link = sb.auth.admin.generate_link({
                        "type": "recovery", "email": email})
                    uid = getattr(getattr(link, "user", None), "id", None) \
                        or _find_uid(sb, email)
                    if not uid:
                        raise RuntimeError("could not resolve Supabase user id")
                    note = "linked (use Forgot-password to set a password)"
                await conn.execute(
                    "update users set auth_uid = $1 where id = $2", uid, r["id"])
                ok += 1
                print(f"  OK [{note}]: {email}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  FAILED {email}: {e}")
        print(f"Done. ok={ok} failed={failed}")
        if SET_PW and ok:
            print("\nAll processed users can now sign in with the TEMP_PASSWORD "
                  "you supplied. Tell them to change it after logging in.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
