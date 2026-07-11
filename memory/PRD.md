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

## Fix 2026-07-11 (this session): Anthropic always "(no key)" in every AI dropdown — ROOT CAUSE FOUND
- User report (3rd time): saved org Anthropic key in Settings, all AI buttons still list
  "Anthropic (no key)" → buttons disabled → core feature dead. Previous fixes (frontend cache
  invalidation) were treating a symptom; keys were ALWAYS saving fine (anthropicSet:true).
- REAL bug: backend routers/ai.py ai_options built configured list by KEY NAME ("anthropic")
  but flagged engines by ENGINE ID ("claude") → "claude" in ["anthropic"] always False.
  Anthropic engine could NEVER show configured regardless of DB state. Other engines matched
  by name coincidence. One-line fix: engine_key = {"claude": "anthropic"} mapping.
- Verified: curl PUT fake key on QA org → /ai/options now returns claude:True; UI screenshot
  shows "Anthropic" enabled + selected by default on Opportunities page.
- STATUS: fixed in PREVIEW ONLY. User must Save-to-GitHub + Redeploy for captureagent.us.

## Fix + Feature 2026-07-11 (later same session): "unparseable response" fix + Federal Opportunities overhaul (iteration_9: 100% pass)
- BUG (user's 3rd report, production): AI Deep Scan / Verify buttons ran then failed with
  "AI returned an unparsable response". Evidence from shared-DB job logs (intel_jobs, refresh_jobs).
  ROOT CAUSES: (1) integrations.anthropic_verify max_tokens=2600 while verifying 25-opp batches →
  output truncated mid-JSON (org has 65 opps; worked when pipeline was small); (2) intel.py tiers
  8-12K tokens too small + web-search "pause_turn" stop reason never continued; (3) retired model
  claude-3-5-haiku-20241022 in lean tier (404 in logs); (4) no JSON salvage.
- FIXES: genai._anthropic_call_sync rewritten (pause_turn continuation loop, stopReason/webSearches
  telemetry, models param); genai.extract_json + repair_json (truncated-JSON salvage, unit-tested);
  genai.anthropic_json_salvage_sync (one no-tools retry when model replies prose instead of JSON);
  intel tiers → 12K/24K/32K tokens + current models (sonnet-4-5/haiku-4-5); verify → 16K tokens;
  actionable error messages incl. stop reason. LIVE-VERIFIED with user's temp Anthropic key on QA org:
  verify 200 (8 verified, haiku-4-5), deep scan lean job "done", enrich 200.
- OVERHAUL (user's full spec): Federal Opportunities tab → capture qualification workspace.
  - NEW /app/backend/scoring.py: deterministic engine — eligibility hard gates (set-aside, SAM,
    NAICS size, vehicle access, CMMC, clearances, ITAR, deadline) → Eligible/Conditional/Ineligible/
    Unknown (gates can NEVER be hidden by scores); weighted Fit 0-100 (30/20/15/10/10/10/5 model,
    evidence per category, AI requirementMatches when present, manual override requires rationale);
    PWin banded Low/Med/High separate from Fit (no fake calibrated %); financials (stated vs
    addressable value, shared-IDIQ-ceiling never shown as revenue, weighted pipeline = addressable
    × PWin); Priority A/B/C/Watch/Pass; red flags. Derived on every GET (reacts to profile changes).
  - DB migration (migrations/2026_07_capture_workspace.sql, applied): 23 new opportunity columns
    (scope_summary, tags, opp_type, acq_stage, recompete, due_time, psc, naics_title, size_standard,
    value_type, value_confidence, addressable_value, contract_type, awards_count, vehicle_access,
    pursuit_role, incumbent, competition, capture, watch, amendments, ai_enrichment) + org_profiles
    vehicles/no_go/pref_role.
  - NEW POST /opportunities/{id}/enrich (AI Qualify): fills ONLY empty fields, never overwrites user
    data, "Unknown" stays unknown, stores requirementMatches/gaps/sources/confidence in ai_enrichment.
  - Frontend: Opportunities.js rebuilt — 19-column registry (lib/oppColumns.js), column chooser +
    saved views (localStorage), multi-sort (shift-click), 13 filters + watchlist, bulk actions
    (stage/owner/watch/delete/export), CSV export, sticky header; NEW components/OppDrawer.js
    30-second qualification drawer (sections: overview, fit breakdown, eligibility gates, AI
    requirements, competition, financials, capture w/ owner+next action+bid decision, sources);
    Profile.js + vehicles/prefRole/noGo fields. SAM pull now maps PSC, due time+tz, acq stage.
  - Testing agent iteration_9: backend 10/10 pytest, full frontend playwright pass, no critical issues.
- NOTE: user's temp Anthropic key was saved on QA org secrets (preview testing) — advise user to
  revoke/rotate it after redeploy. 8 "QA Test Opp" rows remain on QA Verification Org.
- STATUS: fixed/built in PREVIEW. User must Save-to-GitHub + Redeploy for captureagent.us.

## Marketing site additions 2026-07-11 (same session, pre-deploy)
- Home: /marketing/opportunities.png replaced with fresh 1440x900 screenshot of the NEW capture
  qualification table (seeded realistic demo data on QA org; org temporarily renamed for the shot,
  restored after).
- NEW public pages + top-nav links: /reviews and /contact (marketing/Reviews.js, Contact.js,
  formData.js shared lists; routes in App.js; NAV in MarketingLayout.js).
- NEW backend routers/public.py (no auth): GET/POST /api/public/reviews, POST /api/public/contact.
  Honeypot anti-spam, size limits, email regex. Reviews support show-initials ("T. S.") and
  anonymous-company display; email never exposed. Optional headshot (JPEG/PNG/WEBP ≤2MB) moderated
  via EMERGENT_LLM_KEY + gpt-4o-mini vision (emergentintegrations LlmChat/ImageContent) — APPROVE
  and REJECT paths both live-tested. Contact submissions stored in marketing_contacts and forwarded
  via Resend to info@orbitalservicescorporation.com (verified forwarded=true). HubSpot CRM NOT wired
  (needs user's HubSpot private-app token — offered as follow-up).
- Migrations: supabase/migrations/0014_capture_workspace.sql (idempotent, mirrors earlier manual
  migration) + 0015_marketing_pages.sql (marketing_reviews, marketing_contacts) — auto-applied.
- backend/.env += EMERGENT_LLM_KEY. Test reviews/contacts deleted from shared DB before deploy.

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
