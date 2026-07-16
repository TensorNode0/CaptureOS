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

## QA org extras (2026-07-11)
- QA Verification Org (499e35c6-ca12-4589-aa1a-ae22bdb72c07) has a USER-PROVIDED temp Anthropic
  API key saved in org secrets (used to live-test verify/deep-scan/enrich). User should revoke it
  when done. 8 seed rows titled "QA Test Opp N - Space Robotics IDIQ" remain for UI testing.

## AUTH ARCHITECTURE CHANGE (2026-07-16)
- App now uses SUPABASE AUTH (GoTrue). Login via supabase-js on frontend; backend validates
  Supabase ES256 JWTs. QA account unchanged: qa.captureagent@testmail.dev / CaptureQA#2026
  (works via UI login and via POST {SUPABASE_URL}/auth/v1/token?grant_type=password with anon key).
- SUPABASE_URL/keys are in backend/.env; REACT_APP_SUPABASE_URL/ANON_KEY in frontend/.env.
- frontend/.env REACT_APP_BACKEND_URL is set to https://captureagent.us (deploy convention);
  flip to https://govcon-workspace.preview.emergentagent.com before preview UI testing.
