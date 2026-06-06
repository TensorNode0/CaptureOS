# Auth Testing — GovCon Command Center

Custom JWT email+password auth with httpOnly cookies (SameSite=None; Secure). Test via the
external HTTPS URL (cookies are Secure, so localhost http will not retain them).

## Credentials (also in /app/memory/test_credentials.md)
- Owner/Admin: admin@govcon.io / Admin#2026
- Editor: editor@govcon.io / Editor#2026
- Viewer: viewer@govcon.io / Editor#2026
- Demo org: "Orbital Defense Systems" (12 seeded opportunities + org profile)

## API checks
BASE = https://8d626961-5fb0-4ff9-bfac-7fe303cdef56.preview.emergentagent.com
1. POST {BASE}/api/auth/login {email,password} -c cookies -> returns user + organizations[]
2. GET {BASE}/api/auth/me -b cookies -> same user
3. POST /api/auth/register -> returns user + verifyUrl (email mocked)
4. POST /api/auth/forgot-password -> returns resetUrl (email mocked)
5. POST /api/auth/verify-email {token} ; POST /api/auth/reset-password {token,password}

## RBAC (server-side, enforced on every /api/orgs/{orgId}/... route)
- viewer: cannot POST/PUT/DELETE opportunities, cannot verify/pull, cannot access members/secrets (403)
- editor: can CRUD opportunities + verify + pull, cannot manage members/secrets (403)
- admin/owner: members, secrets, profile, audit
- owner only: transfer-ownership

## Notes
- AI "Verify & Refresh" and "Pull from SAM/Grants" are MOCKED (return realistic data, write audit + refreshJobs).
- Secrets are encrypted (Fernet), returned masked only.
