"""Generate a one-time password-recovery link for a user via the Supabase admin
API — no email delivery required. Useful when SMTP isn't sending yet.

  python get_recovery_link.py user@example.com

Prints the action_link; the user opens it, sets a password, and signs in.
Single-use and short-lived. Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.
"""
import os
import sys

from supabase import create_client

if len(sys.argv) < 2:
    sys.exit("usage: python get_recovery_link.py <email>")
email = sys.argv[1].lower().strip()

url = os.environ["SUPABASE_URL"].split("/rest/")[0].split("/auth/")[0].rstrip("/")
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
frontend = os.environ.get("FRONTEND_URL", "").rstrip("/")

sb = create_client(url, key)
res = sb.auth.admin.generate_link({
    "type": "recovery",
    "email": email,
    "options": {"redirect_to": f"{frontend}/reset-password"},
})

link = None
props = getattr(res, "properties", None)
if props is not None:
    link = getattr(props, "action_link", None)
link = link or getattr(res, "action_link", None)
print("RECOVERY LINK:", link or f"<none returned> full response: {res}")
