# CaptureAgent (captureagent.us) — PRD & Deployment Log

## Source of Truth
GitHub TensorNode0/CaptureOS `main`. Standing user rule: deploy EXACTLY what's on main — never
rebuild/redesign/regenerate features; if a check fails, show the error instead of rewriting app code.
Repo is usually private; user makes it public briefly (or uses GitHub import) when a pull is needed.

## Architecture
- Backend: FastAPI + asyncpg → EXTERNAL Supabase PostgreSQL via DATABASE_URL. NO MongoDB
  (never add MONGO_URL/motor/pymongo). Supervisor: uvicorn 0.0.0.0:8001, routes under /api.
- Migrations: supabase/migrations/*.sql auto-apply at startup (AUTO_MIGRATE=1), tracked in
  schema_migrations; startup logs "[migrate] applied ..." / "up to date".
- Frontend: CRA. api.js: BASE = REACT_APP_BACKEND_URL || "" (empty → same-origin /api).
  Public marketing site: /home /about /why /features /resources /blog; root → /home (visitors)
  or /dashboard (signed-in).
- Auth: JWT httpOnly cookies (Secure when FRONTEND_URL is https), bcrypt, login lockout.
  REAL email via Resend (email_service.py: Resend primary, SMTP fallback, console mock when
  unconfigured — token links returned in API responses ONLY in mock mode).
- Onboarding requires AOR certification checkbox (server-enforced).
- backend/.env (git-ignored, NEVER display values): DATABASE_URL, JWT_SECRET, SECRETS_ENC_KEY,
  FRONTEND_URL=https://captureagent.us, SEED_DEMO=0, EMAIL_FROM=CaptureAgent <noreply@captureagent.us>,
  RESEND_API_KEY (set by user via code editor).
- frontend/.env (git-ignored): REACT_APP_BACKEND_URL=https://captureagent.us (user-directed for
  prod builds; flip back to the preview URL for preview auth testing),
  WDS_SOCKET_PORT=443, DANGEROUSLY_DISABLE_HOST_CHECK=true (needed because package.json "proxy"
  field breaks CRA host-check behind preview ingress; dev-only, prod builds unaffected).

## Environments
- PREVIEW (this workspace): https://govcon-workspace.preview.emergentagent.com
- PRODUCTION (user-deployed, agent has NO access/deploy control): https://captureagent.us
  (fallback URL govcon-workspace.emergent.host). Deploy button is USER-ONLY.
- Platform env behavior (observed evidence): deploy snapshots workspace backend/.env for secrets,
  force-rewrites URL-type vars (FRONTEND_URL, REACT_APP_BACKEND_URL) to the production URL —
  which is now captureagent.us, so values converge correctly. User's production env panel is
  read-only (support says that's a bug → support@emergent.sh).

## Timeline
- 2026-07-04: Initial import of main @f849235 (PR #3 rebrand). Secrets generated straight into
  backend/.env (never in chat). Deploy verification iteration_4: 100%. User deployed; domain
  linked after Cloudflare 1034 phase (iteration_5). "Can't login on captureagent.us" bug:
  root cause = old bundle baked emergent.host + CORS; fixed then, verified iteration_6.
- 2026-07-06/07: main @20e2266 (PR #6 marketing site, Resend real email, AOR, RBAC v2,
  admin permissions). Migration 0003 pre-applied by user's external dev. Pre-redeploy gate
  iteration_7: 100% pass (real Resend sends accepted, no token-link leaks, AOR gate enforced).
- 2026-07-11: main @b936c85 (PR #25 home screenshots; #24 session idle timeout + proposal customer
  card/PEO directory; #23 venture upgrades). Migrations 0011–0013 auto-applied. 0 app-file diffs
  vs main. Secrets untouched (SECRETS_ENC_KEY immutable per user). AWAITING user Redeploy.
  Note: backend/.env also carries REACT_APP_BACKEND_URL=https://captureagent.us (user-added; harmless).
- 2026-07-10: main @6911b63 (PR #19 hero copy, PRs #7–#19: BYOK engines, notice status,
  proposal evaluation, venture docs, competitive reports, profile enrichment, subcontractor).
  Migrations 0004–0010 auto-applied. Preview smoke OK (new "TurboTax of GovCon" hero, Blog nav,
  cookie banner). AWAITING user Redeploy, then live verification.

## Fix 2026-07-12: AI engine failures + dropdowns everywhere (iteration_8: 100% pass)
- Root causes: (1) repo's genai.py emergent engine called NON-EXISTENT host llm.emergentagent.com
  → "[Errno -2] Name or service not known"; (2) OpenAI 429 = user's OpenAI account rate/quota limit
  (key valid); (3) /opportunities/verify was hardcoded to Anthropic with no engine choice.
- Fixes (WORKSPACE ONLY — user must Save-to-GitHub + redeploy): emergent_generate rewritten to
  emergentintegrations LlmChat (provider by model prefix; catalog claude-sonnet-4-6/gpt-5.4/gpt-4o/
  gemini-3.1-pro-preview); friendly 429 message; verify accepts {engine,model,effort} (claude=live
  web path unchanged, others=offline review, discovered=[]); capabilities/competitive/PEO-check
  engine-agnostic (web_search only on claude); frontend: Opportunities verify uses AIButton with
  dropdowns, lockEngine removed on Capability x2/Competitive/PEO; AIButton renders locked engines
  as visible disabled select + note captions; requirements.txt += emergentintegrations (+extra index).
- Deep Scan (intel) intentionally stays Anthropic-locked (needs live web search) — now visibly labeled.
- Emergent universal key saved on QA org secrets (preview) for future tests; live proxy call verified.
- REMINDER: workspace now DIVERGES from GitHub main — user must push (Save to Github) before next pull.

## Known notes (reported, not fixed — user's codebase)
- Settings API-keys banner "live, server-side" wraps oddly (cosmetic).
- /verify-email page double-fires under React StrictMode in dev (prod builds unaffected).
- email_service failures are logged ([EMAIL-ERROR]) but invisible in register response.
- CRA dev server: curl without Accept: text/html on SPA routes hits the package.json proxy
  (ENOTFOUND) — browsers unaffected.

## QA data in the user's LIVE Supabase (safe to delete)
Accounts: qa.captureagent@testmail.dev, qa.ui.*, fixcheck.*, apitest.*, repro.check.*,
verify.check.*, aor.check.* @testmail.dev. Orgs: 'QA Verification Org', 'QA UI Verification Org',
'AOR Test Workspace'.

## Backlog / Next
- P0: User presses Redeploy → live verification (marketing home on captureagent.us, /api/health,
  register delivers real verification email, login clean).
- P1: Flip frontend/.env REACT_APP_BACKEND_URL back to the preview URL before any preview auth testing.
- P2: Next main sync when user updates GitHub.
