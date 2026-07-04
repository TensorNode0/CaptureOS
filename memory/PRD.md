# CaptureAgent (captureagent.us) — PRD & Deployment Log

## Current Source of Truth
GitHub repo **TensorNode0/CaptureOS**, branch `main`, HEAD `f849235` (PR #3 "Rebrand to CaptureAgent",
on top of PR #2 "Per-organization envelope encryption"). The codebase was developed OUTSIDE Emergent;
the user's standing instruction is to deploy it exactly as-is — **no rebuilding, redesigning, or
regenerating features, and no database-layer changes**. If a check fails, show the error instead of
rewriting app code.

## Architecture (post-migration — replaces the old GovCon/MongoDB build)
- Backend: FastAPI + **asyncpg → external Supabase PostgreSQL** via `DATABASE_URL` (backend/.env).
  NO MongoDB (no MONGO_URL/motor/pymongo). Runs under supervisor: uvicorn on 0.0.0.0:8001, routes under /api.
- Migrations: `supabase/migrations/*.sql`, auto-applied at startup (`AUTO_MIGRATE=1` default),
  tracked in `schema_migrations`. Startup log prints `[migrate] applied ...` / `[migrate] up to date`.
- Frontend: CRA in frontend/, `REACT_APP_BACKEND_URL` (frontend/.env) = preview URL; code appends /api.
- Auth: JWT httpOnly cookies (access+refresh, SameSite=None Secure), bcrypt, mocked email
  (register/reset return verifyUrl/resetUrl in JSON; links point at FRONTEND_URL).
- Secrets: per-org API keys envelope-encrypted (master `SECRETS_ENC_KEY` Fernet in backend/.env),
  key rotation + access audit endpoints. Keys masked server-side; never sent to browser.
- backend/.env (git-ignored, values never shown in chat): DATABASE_URL (user's Supabase session-pooler URI),
  JWT_SECRET (openssl rand -hex 32), SECRETS_ENC_KEY (Fernet), FRONTEND_URL=https://captureagent.us, SEED_DEMO=0.

## Implemented / Verified (2026-07-04)
- Repo pulled (public window) and mirrored into /app; repo may be private again now.
- Deps installed exactly from backend/requirements.txt + frontend package.json (yarn).
- Secrets generated directly into backend/.env without display; user supplied DATABASE_URL out-of-chat
  (initially pasted into docker-compose.dev.yml by mistake — value moved to backend/.env programmatically,
  file restored byte-identical before any auto-commit; `git log -S` confirms secret never entered history).
- Verification (test_reports/iteration_4.json — 100% pass, backend 7/7 + full Playwright UI flow):
  1. GET /api/health → {"status":"ok","service":"captureagent"} ✅
  2. Startup log shows `[migrate] up to date` ✅
  3. Register → verify(token) → login → onboarding org creation → Settings→API Keys masked fields ✅
- QA data in live Supabase: qa.captureagent@testmail.dev / org "QA Verification Org" (see test_credentials.md).
- Testing agent added /app/backend/tests/test_deploy_verification.py (regression harness; not app code).

## Known findings (reported, intentionally NOT fixed per user constraint)
- Cosmetic: Settings → API Keys info banner wraps "live, server-side" oddly (flex/word-break).
- CORS allow_origins = [FRONTEND_URL, localhost:3000]; preview works because frontend/backend are
  same-origin behind ingress. Fine for production at captureagent.us.
- Preview pod's supervisor also runs an unused platform-managed mongod ([readonly config) — harmless.
- deployment_agent "fail" findings assessed as false positives / platform-managed / intentional (.env gitignored).

## Production (deployed 2026-07-04)
- LIVE at https://govcon-workspace.emergent.host — verified by testing_agent (iteration_5, read-only):
  health JSON exact match, login page renders, external Supabase connected (startup = pool + migrations).
- captureagent.us: DNS on Cloudflare, valid cert issued 2026-07-04 (user started Entri flow), but
  Cloudflare error 1034 = origin route to the deployment not configured/propagated yet. User must
  finish Link domain → Entri in deployment settings; remove old A/AAAA records at registrar if stuck;
  escalate to support@emergent.sh with job ID if it persists. NOT an app bug — no code changes made.

## Bug fix 2026-07-04: "can't register/login" on captureagent.us
- Domain link completed by user (captureagent.us now serves the app; error 1034 gone).
- Root cause: prod bundle baked REACT_APP_BACKEND_URL=https://govcon-workspace.emergent.host →
  cross-origin calls from captureagent.us → CORS preflight 400 (no ACAO) → browser blocked all auth.
- Fix (only authorized code change, frontend/src/lib/api.js): BASE = NODE_ENV==='production'
  ? window.location.origin : REACT_APP_BACKEND_URL. Same-origin on any prod host, first-party cookies,
  dev/preview unchanged. Verified by testing_agent iteration_6 (100%): preview auth e2e green,
  new bundle has 0 govcon-workspace refs, live-domain failure reproduced pre-redeploy.
- AWAITING: user redeploy to ship the fixed bundle to production.
- Pre-existing LOW issue (reported, not fixed): /verify-email page double-fires API under React
  StrictMode in dev/preview → shows "Invalid or expired token" though verification succeeded.
  Prod builds unaffected. Fix requires user approval (their codebase).
- QA accounts created in the SHARED live Supabase during testing: fixcheck.*/apitest.*@testmail.dev
  (cleanup: delete from users where email like 'fixcheck.%' or email like 'apitest.%' or email like 'repro.check.%').

## Backlog / Next
- P0: USER REDEPLOY to push fixed bundle live, then retest register/login at captureagent.us.
- P0 (done by user): captureagent.us domain linking.
- P0: Resend email integration — user said "yes to improvements"; awaiting answers to 4 scope questions
  (direct edits vs patch, drop URLs-in-response when key set, sender address, which flows).
  Playbook obtained: resend pip pkg, RESEND_API_KEY + SENDER_EMAIL in backend/.env,
  asyncio.to_thread(resend.Emails.send, params). 4 mocked spots: auth.py:82/161/195, orgs.py:266.
- P1: Real email provider for verify/reset links before enabling public sign-ups (currently mocked).
- P2: Whatever the user develops next in GitHub — re-import via GitHub button when main updates.
