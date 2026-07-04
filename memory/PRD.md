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

## Backlog / Next
- P0: User to click **Deploy** on Emergent (50 credits/mo), set env vars in deployment settings
  (DATABASE_URL, JWT_SECRET, SECRETS_ENC_KEY, FRONTEND_URL, SEED_DEMO) outside chat, then
  link custom domain captureagent.us (Link domain → Entri; remove old A records if DNS stalls).
- P1: Real email provider for verify/reset links before enabling public sign-ups (currently mocked).
- P2: Whatever the user develops next in GitHub — re-import via GitHub button when main updates.
