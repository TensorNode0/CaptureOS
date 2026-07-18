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

## BILLING / STRIPE (2026-07-18) — Phase 2 shipped
- Stripe sandbox provisioned (via `python -m setup_stripe`): products
  `captureagent_oi` ($49/mo · $499.80/yr) and `captureagent_full` ($99/mo · $1009.80/yr).
  Lookup keys: `oi_monthly`, `oi_yearly`, `full_monthly`, `full_yearly`.
- backend/.env carries: STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET,
  STRIPE_ACCOUNT_ID, STRIPE_MODE, CAPTUREAGENT_OWNER_EMAILS (comma-separated allowlist for
  the refund approver role), BILLING_TIER_ALLOWLIST (comma-separated email allowlist that
  bypasses tier gating — used for `info@orbitalservicescorporation.com` the platform owner).
- QA (`qa.captureagent@testmail.dev`) IS a `platform_owner` (can access Admin → Refunds tab)
  but is NOT grandfathered on billing — QA gets `tier=free` and IS tier-gated so we can
  test the upgrade flow end-to-end. Sub row is auto-created on first `/api/payments/me`.
- Tier gating enforced server-side (`billing.assert_full_tier`) on: proposal create/draft/
  evaluate, venture doc create/draft/from-program/redraft-form for kinds in
  `FULL_TIER_VENTURE_KINDS` (investor_email, pitch_deck, business_plan, financials,
  accelerator_application). Scans (`investor_scan`, `accelerator_scan`) are NOT gated.
- Tier gating on frontend via `<RequireTier minTier="full">` wrapping /proposals,
  /investment-deals, /accelerator-applications, /opportunities/:id/proposal.
- Refund flow: user submits from Settings → Billing → "Request refund"; platform owner sees
  and approves/denies in Admin → Refunds tab (via `/api/refund-requests`). Approvals fire
  `stripe.Refund.create` against the last payment_intent on file.
