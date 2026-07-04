# Test Credentials — CaptureAgent (captureagent.us)

## Database
- External Supabase PostgreSQL (DATABASE_URL in backend/.env). SEED_DEMO=0 → NO seeded demo users.
- Old GovCon-era accounts (admin@govcon.io etc.) DO NOT exist in this database.

## QA account (created during deployment verification)
- Email: `qa.captureagent@testmail.dev`
- Password: `CaptureQA#2026`
- Org: created via onboarding flow

## Notes
- Email verification is MOCKED: `POST /api/auth/register` returns `verifyUrl` in the JSON payload.
  The link points at FRONTEND_URL (https://captureagent.us) — use only the `token` param:
  either `POST /api/auth/verify-email {"token": ...}` or open `{preview}/verify-email?token=...`.
- Auth uses JWT cookies (set on register/login).
- Preview URL: https://govcon-workspace.preview.emergentagent.com
