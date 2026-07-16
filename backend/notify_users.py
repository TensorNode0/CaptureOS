"""Notify each REAL user that their account is ready, via Resend (the app's
proven email channel — not Supabase SMTP). Each gets a "set your password"
link to their Supabase account. Test accounts are skipped.

  docker run --rm --env-file backend/.env -v "${PWD}/backend:/app" -w /app \
    python:3.12-slim bash -c \
    "pip install -q supabase asyncpg httpx && python notify_users.py"

Requires: DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, RESEND_API_KEY,
EMAIL_FROM, FRONTEND_URL. Add --dry-run to list recipients without emailing.
"""
import os
import sys
import asyncio

import asyncpg
from supabase import create_client

import email_service

DRY = "--dry-run" in sys.argv
SKIP_SUFFIXES = ("@testmail.dev",)
SKIP_EMAILS = {"diag-ca-2026@captureagent.us"}


def _is_real(email: str) -> bool:
    e = (email or "").lower()
    return e and e not in SKIP_EMAILS and not any(e.endswith(s) for s in SKIP_SUFFIXES)


async def main():
    db = os.environ["DATABASE_URL"]
    url = os.environ["SUPABASE_URL"].split("/rest/")[0].split("/auth/")[0].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    frontend = os.environ.get("FRONTEND_URL", "https://captureagent.us").rstrip("/")

    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch("select email, name from users order by created_at")
    finally:
        await conn.close()

    real = [r for r in rows if _is_real(r["email"])]
    print(f"{len(real)} real user(s) to notify:")
    for r in real:
        print(f"   - {r['email']}")
    if DRY:
        print("DRY RUN — no emails sent.")
        return

    sb = create_client(url, key)
    sent = failed = 0
    for r in real:
        email = r["email"].lower().strip()
        try:
            link = sb.auth.admin.generate_link({
                "type": "recovery", "email": email,
                "options": {"redirect_to": f"{frontend}/reset-password"}})
            action = getattr(getattr(link, "properties", None), "action_link", None) \
                or getattr(link, "action_link", None)
            if not action:
                raise RuntimeError("no action_link returned")
            await email_service.send_reset(email, action)
            sent += 1
            print(f"  emailed: {email}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAILED {email}: {e}")
    print(f"Done. sent={sent} failed={failed}")


if __name__ == "__main__":
    asyncio.run(main())
