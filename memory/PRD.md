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
- MOCKED: "Verify & Refresh with AI" (verifyReport accept/dismiss diffs + link freshness),
  "Pull from SAM/Grants" (add/merge by sol#). Both write auditLog + refreshJobs.
- Tested: 28/28 backend pass; all critical frontend flows verified. Fixed Motor tz_aware bug.

## Prioritized Backlog
- P0 (next): Phase 5 — wire REAL integrations. Anthropic Messages API (web search + web fetch,
  Haiku-class, capped tokens, batched, JSON-only) for Verify & Refresh; SAM.gov v2 + Grants.gov
  search2 pull (port govcon_pull.py), dedupe/merge by sol#. Use the org's stored encrypted keys.
- P1: Phase 7 Proposal Studio (solicitation summary, requirement extraction, tabbed deliverable
  generation via python-docx/pptx/openpyxl, final evaluation scoring, ZIP package).
- P1: Real email provider (SendGrid/Resend) for verification + invites.
- P2: Weekly scheduled verify, per-org rate limiting, USAspending incumbent recon, CSV/JSON export.
- P2: Phase 6 hardening — auth/refresh rate limits, deeper validation, deploy health check.

## Test Credentials → /app/memory/test_credentials.md
