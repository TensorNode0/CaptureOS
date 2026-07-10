# Test Credentials — CaptureAgent (captureagent.us)

## Database
- External Supabase PostgreSQL (DATABASE_URL in backend/.env — never print it). SEED_DEMO=0,
  no seeded demo users. PREVIEW AND PRODUCTION SHARE THIS DATABASE — create minimal test data.

## QA accounts (all created by agents; safe to delete)
- qa.captureagent@testmail.dev / CaptureQA#2026 — owner of "QA Verification Org" (email verified)
- aor.check.1783330011@testmail.dev / AorCheck#2026 — owner of "AOR Test Workspace"
- verify.check.1783329822@testmail.dev / VerifyCheck#2026 — no org
- fixcheck.*/apitest.*/repro.check.*@testmail.dev / FixCheck#2026 or Repro#2026x — throwaways

## Notes
- Email is now REAL (Resend). Register/reset responses NO LONGER contain verifyUrl/resetUrl.
  For test accounts on fake domains, pull tokens from email_verify_tokens table via the backend
  DB pool if verification must be completed.
- New-user org creation requires ticking the AOR certification checkbox (aor-certify-checkbox).
- Auth = JWT httpOnly cookies (Secure). Login lockout after repeated failures (per ip:email).
- frontend/.env currently points REACT_APP_BACKEND_URL at https://captureagent.us (production);
  flip to https://govcon-workspace.preview.emergentagent.com before preview auth UI testing.
