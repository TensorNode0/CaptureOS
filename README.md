# CaptureAgent

**Production: [captureagent.us](https://captureagent.us)**

An AI-powered capture & proposal manager for U.S. government contractors.
Track opportunities, verify them against live sources, score fit and
eligibility, let the AI capture manager design a **proposed capability**
(title, abstract, executive summary, concept rendering, SoW, WBS + schedule,
budget), then draft the full **proposal package** volume-by-volume with Claude
or ChatGPT — review, edit, and export to Word/Excel/PowerPoint or a single zip.

## Architecture

| Layer     | Tech                                                              |
|-----------|-------------------------------------------------------------------|
| Frontend  | React 18 (CRA), Tailwind, Recharts, Framer Motion — dark console UI |
| Backend   | FastAPI (Python 3.12), asyncpg                                    |
| Database  | **Supabase** (PostgreSQL 15+) — works with any Postgres            |
| AI        | Anthropic Claude (research, compliance, generation) + optional OpenAI |
| Data feeds| SAM.gov Opportunities v2, Grants.gov search2, Claude web search (SBIR/DSIP, AFWERX/SpaceWERX, DIU, DARPA, NASA, NSF/NSIN, GSA…) |

All org data (company profile, solicitations, capabilities, proposals) lives in
Postgres. Per-org API keys are encrypted at rest (Fernet) and only ever used
server-side. Every table ships with Row Level Security enabled so Supabase's
auto-generated REST API exposes nothing.

## Features

- **Auth & multi-tenant orgs** — JWT cookie auth, email verify / password reset
  flows, org join codes, RBAC (viewer / editor / admin / owner), audit log.
- **Company profile** — UEI/CAGE, SBA certifications (8(a), HUBZone, SDVOSB,
  WOSB…), CMMC level, SPRS, capabilities, past performance, differentiators.
- **Opportunity pipeline** — stages Identified → Won/Lost/No-Bid, fit factor
  scoring, PWin, compliance checklist with CMMC no-bid gate, budget, evaluation
  criteria, bid/no-bid decision.
- **Live pulls** — SAM.gov + Grants.gov by NAICS/keywords, deduped by
  solicitation number.
- **AI Verify & Refresh** — Claude + web search confirms each opportunity is
  still live, flags due-date changes, discovers new matches.
- **AI Intelligence scan** — weekly-style report of real open, SB-eligible
  solicitations across SAM/SBIR/DSIP/AFWERX/DIU/DARPA/NASA and more, fit-scored
  against your profile, one-click add to pipeline.
- **Proposed Capability (AI capture manager)** — one click generates title,
  abstract, executive summary, keywords, SVG concept rendering, charts/tables,
  Statement of Work, WBS with schedule bars, and a budget with basis of
  estimate. Human edits, approves, and versions are kept.
- **Proposal package** — volume set adapts to the vehicle (RFP / SBIR / STTR /
  BAA / CSO / Grant). Each volume has a *Draft with AI* button (Claude or
  ChatGPT), an in-app editor, finalize, per-document download (.docx / .xlsx /
  .pptx) and a full-package .zip.

## Quick start (Docker only — no local Python/Node needed)

```bash
cp backend/.env.example backend/.env    # fill in DATABASE_URL, JWT_SECRET, SECRETS_ENC_KEY
cp frontend/.env.example frontend/.env
docker compose -f docker-compose.dev.yml up
```

Then open http://localhost:3000 (API at http://localhost:8000). To try the app
without a Supabase project, use the bundled local database instead:

```bash
# in backend/.env:  DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres
docker compose -f docker-compose.dev.yml --profile localdb up
```

## Setup

### 1. Database (Supabase)

1. Create a project at [supabase.com](https://supabase.com) (free tier works).
2. Project Settings → Database → Connection string → copy the **Session
   pooler** URI (port 5432).
3. Put it in `backend/.env` as `DATABASE_URL` (see `backend/.env.example`).

Migrations in `supabase/migrations/` are applied automatically at server
startup (`AUTO_MIGRATE=1`, the default), or manually:

```bash
cd backend && python apply_migrations.py
```

Any vanilla PostgreSQL also works (local dev, Docker, RDS).

### 2. Backend

```bash
cd backend
cp .env.example .env        # fill in DATABASE_URL, JWT_SECRET, SECRETS_ENC_KEY
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Set `SEED_DEMO=1` to create the demo org (admin@govcon.io / Admin#2026) with
12 sample opportunities.

### 3. Frontend

```bash
cd frontend
cp .env.example .env        # REACT_APP_BACKEND_URL=http://localhost:8000
npm install
npm start
```

### 4. API keys (per organization, in-app)

Settings → API Keys (admin role required). Keys are encrypted at rest and
never returned to the browser in full.

- **Anthropic** — console.anthropic.com → powers Verify & Refresh, the
  Intelligence scan, capability generation, and proposal drafting.
- **SAM.gov** — sam.gov → Account Details → API Key → powers the SAM pull.
- **OpenAI** (optional) — platform.openai.com → enables the ChatGPT drafting
  engine.

### 5. Email delivery (verification, password reset, invites, approvals)

Set `RESEND_API_KEY` (from [resend.com](https://resend.com), free tier) and
`EMAIL_FROM` in `backend/.env`, and verify your sending domain with the DNS
records Resend provides. Any SMTP server works as a fallback (`SMTP_HOST`,
`SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`). With neither configured, the app runs
in dev mode: emails print to the server log and verification/reset links are
surfaced in API responses — never deploy production that way.

## Roles & governance

Signup is domain-aware: the **first user from a company domain must certify
they are the Authorized Organizational Representative (AOR)** and becomes the
workspace **admin**; later signups from that domain request access, which the
admin approves with a role. Members can also be invited by email or join via
code.

| Role | Can |
|------|-----|
| `admin` | Everything below, plus: entity info, members/roles, API keys, **submit / mark proposals submitted** |
| `capture_manager` | **Create and approve** capabilities and proposal packages; dashboards; request a 24-h entity-info edit grant |
| `pi`, `proposal_writer`, `technical_writer`, `editor` | Edit opportunities, capability content, and proposal volumes; run AI drafting on volumes |
| `viewer` | Read-only |

Strict by design: an admin cannot create proposal packages (assign a
capture manager), and a capture manager cannot submit (the admin does).

## QA (no local Python/Node needed — Docker only)

```bash
./qa/run_backend_tests.sh    # Postgres 16 + API in containers, full pytest suite
./qa/run_frontend_build.sh   # production CRA build in a Node 20 container
```

## Security notes

See [SECURITY.md](SECURITY.md) for the full architecture (per-org envelope
encryption, key rotation, access auditing, CMMC positioning).

- Per-org API keys: envelope-encrypted at rest (per-org data key wrapped by a
  server-side master key), masked in every API response, rotatable per org,
  with every access audit-logged.
- RLS enabled on all tables — Supabase PostgREST exposes nothing by default.
- Login lockout (5 attempts / 15 min), bcrypt password hashing, httpOnly
  cookies.
- This workspace is for **unclassified** pipeline metadata. Do not store CUI
  or ITAR-controlled technical data.

## Roadmap

- Stripe subscription billing (monetization)
- Microsoft 365 embedded co-editing (Word/Excel/PowerPoint via Graph API)
- Compliance matrix auto-extraction from full solicitation PDFs
- Teaming partner search & past-performance library
