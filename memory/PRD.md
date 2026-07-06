# GovCon Command Center — PRD & Build Log

## Original Problem Statement
Multi-tenant SaaS (React + FastAPI + MongoDB) for federal-contracting capture teams. Email auth
with verification; Organizations with server-side RBAC (Owner/Admin/Editor/Viewer); Admin→Members
(invite by email, assign roles); home dashboard (KPI cards + bar/pie/line charts via Recharts over
an org-scoped opportunity pipeline); Opportunities table (search/sort/filter, set-aside eligibility
coloring, Last-Verified) with two Editor-only actions — "Verify & Refresh with AI" (Anthropic
Messages API + web search/fetch) and "Pull from SAM/Grants" (SAM.gov + Grants.gov, dedupe by sol#);
per-opportunity workspace (fit matrix, set-aside eligibility, compliance matrix w/ CMMC no-bid gate,
budget vs ceiling, scorecard keeping Proposal Strength and Capture Probability SEPARATE — never a
fabricated win-rate); org/company profile drives eligibility; Settings stores Anthropic + SAM keys
as encrypted, masked, server-only org secrets; dark space theme. Build in phases; mock external APIs
until the final phase; keep AI cheap.

## User Choices (from kickoff)
- Custom JWT email+password auth.
- Email verification MOCKED (verifyUrl/resetUrl surfaced in-app).
- External integrations (AI verify, SAM/Grants pull) MOCKED this iteration; user will provide
  Anthropic + SAM keys to wire live next.
- Scope: Phases 1–4 MVP. Follow the spec's dark space design system exactly.

## Architecture
- Backend: FastAPI, modular routers (auth, orgs[+profile/members/audit/secrets], opportunities),
  Motor/MongoDB (tz_aware=True), JWT httpOnly cookies (SameSite=None; Secure), bcrypt, Fernet for
  secret encryption, rbac.require_role(orgId) dependency on every org-scoped route.
- Frontend: React 18 (CRA) + Tailwind (CSS-variable tokens) + Recharts + framer-motion +
  lucide-react + sonner. AuthContext + org switcher. Pages per spec.
- Collections: users, organizations, memberships, orgProfile, opportunities, secrets, auditLog,
  refreshJobs, plus password_reset_tokens / email_verify_tokens / login_attempts.

## Implemented (2026-06-06)
- Phase 1: Auth (register/login/logout/refresh/forgot/reset/verify-email — email mocked), Orgs,
  memberships, server-side RBAC, org switcher, onboarding (create org → owner).
- Phase 2: Opportunity schema + org-scoped CRUD; table (search/sort/filter/eligibility coloring/
  Last-Verified); detail workspace tabs (Fit & Overview, Set-Aside, Compliance w/ hard NO-BID gate,
  Budget vs ceiling + donut, Scorecard w/ separate Strength & Pwin + radar, Decision w/ gate logic).
- Phase 3: Dashboard KPIs + bar/pie(toggle setAside↔vehicle)/line/horizontal-bar charts, empty states.
- Phase 4: Full dark space theme (tokens, nebula gradients, starfield, glass cards, IBM Plex Sans /
  JetBrains Mono, motion, skeleton/empty/error states, reduced-motion, focus rings).
- Admin (Members invite/role/remove/transfer + Audit log); Settings (org + encrypted/masked API keys);
  Company Profile (drives eligibility).
- Tested: 28/28 backend pass; all critical frontend flows verified. Fixed Motor tz_aware bug.

## Phase 5 — LIVE integrations wired (2026-06)
- `/app/backend/integrations.py`: `anthropic_verify()` (claude-3-5-haiku + `web_search_20250305`
  tool, max_uses=5, JSON-only, ~10¢/run cap), `fetch_sam()` (SAM.gov v2 search), `fetch_grants()`
  (Grants.gov search2). Keys never logged/stored in source.
- `routers/opportunities.py`: removed mocks. `POST /verify` and `POST /pull` now read the org's
  Fernet-encrypted keys from `db.secrets` (decrypt at call time, server-only), Editor-RBAC gated,
  batch capped to 25 opps for cost. Helper `_new_opp_doc()` reused by pull + AI-discovered opps.
  Dedupe/merge by sol# preserves user fit/compliance/budget/scoring.
- Error UX: 400 "Add it in Settings → API Keys" when unset; 400 "rejected" on invalid key;
  502 on upstream failure. Verified via curl (no-key + invalid-key paths).
- ⚠️ User supplies real keys via Settings → API Keys (anthropic-key / sam-key inputs). Live
  success path validated by user since keys are user-owned.

## Phase 6 — AI Intelligence Scan + Org Join + Responsive Nav (2026-06-10)
- **AI Opportunity Intelligence Scan** (LIVE): `/app/backend/intel.py` runs Claude (Sonnet tiers /
  Haiku lean) + `web_search_20250305` against public federal sources (SAM.gov, SBIR/DSIP,
  AFWERX/SpaceWERX, DARPA, NASA, DIU, xTech…) to discover REAL open SB-eligible solicitations and
  fit-score (1-100 + grade) them against the org capability profile. Background job model
  (`intelJobs`) + saved reports (`intelReports`). Tiers: lean/standard/deep cap web-searches &
  opp count for cost control. Router `/app/backend/routers/intel.py`: scan/jobs/reports/delete/
  add-to-pipeline (Editor-gated, keys from encrypted vault).
- **Frontend Intelligence page** (`pages/Intelligence.js` + `components/IntelSummary.js`,
  `components/IntelTable.js`, `lib/intel.js`): executive summary (KPIs + mission/agency/vehicle/
  color-of-money charts + hot signals + recommended actions + source status), 20-column
  sortable/filterable/searchable table with fit grades, compliance flags, color-of-money dots,
  urgency row borders, CSV + standalone-HTML export, report history, add-to-pipeline. Sample-data
  banner when previewing seeded report.
- **Admin-editable Capability Profile** (Company Profile): capabilities, pastPerformance,
  techFocus[], differentiators, commercialization, clearances — drive the AI Fit Score.
- **Org create/join**: in-app "Create organization" + "Join with code" (Org switcher); shareable
  8-char `joinCode` per org (Admin → Members card; GET/rotate). `POST /api/orgs/join`.
- **Responsive navigation**: Shell now has a mobile hamburger drawer (`lg:hidden`) so Settings/Admin
  are reachable below 1024px (fixes the "no Settings" report). New "Intelligence" nav item.
- Settings copy updated — keys are LIVE (no longer mocked).
- Tested: 12/12 new backend (`/app/backend/tests/test_intel_orgs.py`) + prior 28/28 green; 100% of
  frontend flows verified. LIVE Anthropic/SAM success path validated by user (own keys).

## Prioritized Backlog (updated 2026-06-10)
- P1: Scheduled weekly auto-scan (Mon 3:30 AM MT) + email digest of the report (needs Resend/SendGrid).
- P1: "Test connection" button per key in Settings to validate Anthropic/SAM before a full run.
- P1: Phase 7 Proposal Studio (solicitation summary, requirement extraction, deliverable generation).
- P2: USAspending incumbent recon, per-org rate limiting, auth/refresh rate limits.
- P2: Replace window.confirm (join-code rotate) with Modal; richer source coverage (more portals).

## Test Credentials → /app/memory/test_credentials.md
