"""One-off: migrate existing public.users into Supabase Auth (force-reset).

For every profile row without an auth_uid, create a Supabase Auth user via the
GoTrue admin API (service-role), link public.users.auth_uid to it, and email a
set-password (recovery) link. Idempotent — rows already linked are skipped, and
a user that already exists in Auth is re-linked rather than duplicated. All of a
user's existing data stays attached because public.users.id never changes.

Run it in Docker so no local Python is needed (from the repo root):

  # 1) DRY RUN — lists who WOULD migrate. Writes nothing. Sends no email:
  docker run --rm --env-file backend/.env -v "${PWD}/backend:/app" -w /app \
    python:3.12-slim bash -c "pip install -q supabase asyncpg && \
    python migrate_to_supabase_auth.py --dry-run"

  # 2) REAL RUN (only after a backup + dry-run review + SMTP configured):
  docker run --rm --env-file backend/.env -v "${PWD}/backend:/app" -w /app \
    python:3.12-slim bash -c "pip install -q supabase asyncpg && \
    python migrate_to_supabase_auth.py"

Requires env (from backend/.env): DATABASE_URL, SUPABASE_URL,
SUPABASE_SERVICE_ROLE_KEY. Recovery emails only actually send once SMTP is
configured in the Supabase dashboard.
"""
import os
import sys
import asyncio

import asyncpg
from supabase import create_client

DRY = "--dry-run" in sys.argv


def _require(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"Missing required env var: {name}")
    return v


async def main():
    database_url = _require("DATABASE_URL")
    # Tolerate a stray REST/Auth path or trailing slash on the project URL.
    supabase_url = _require("SUPABASE_URL").split("/rest/")[0].split("/auth/")[0].rstrip("/")
    service_role = _require("SUPABASE_SERVICE_ROLE_KEY")

    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch(
            "select id, email, name from users where auth_uid is null "
            "order by created_at")
        print(f"{len(rows)} user(s) need migration.")

        if DRY:
            for r in rows:
                print(f"  [dry-run] would migrate: {r['email']}")
            print("DRY RUN complete — nothing was created, linked, or emailed.")
            return

        sb = create_client(supabase_url, service_role)
        migrated = failed = 0
        for r in rows:
            email = (r["email"] or "").lower().strip()
            try:
                # Create the auth user (confirmed so they can reset immediately).
                # If they already exist from a prior partial run, ignore and
                # re-link below.
                try:
                    sb.auth.admin.create_user({
                        "email": email,
                        "email_confirm": True,
                        "user_metadata": {"full_name": r["name"] or ""},
                    })
                except Exception:  # noqa: BLE001 — likely "already registered"
                    pass
                # generate_link returns the user (new or existing) and triggers
                # the recovery email when SMTP is configured.
                link = sb.auth.admin.generate_link({
                    "type": "recovery", "email": email})
                uid = getattr(getattr(link, "user", None), "id", None)
                if not uid:
                    raise RuntimeError("could not resolve Supabase user id")
                await conn.execute(
                    "update users set auth_uid = $1 where id = $2", uid, r["id"])
                migrated += 1
                print(f"  linked + reset email queued: {email}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  FAILED {email}: {e}")
        print(f"Done. migrated={migrated} failed={failed}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
