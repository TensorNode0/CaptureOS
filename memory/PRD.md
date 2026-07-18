# CaptureAgent (captureagent.us) — PRD & Deployment Log


## Phase 2 (Stripe Billing + Tier Gating + Refunds + GDPR Export) ✅ 2026-07-18
- **3 tiers** provisioned in the Emergent Stripe sandbox via `setup_stripe.py`:
  - `oi_monthly` $49/mo / `oi_yearly` $499.80/yr (15% off)  — Opportunity Intelligence
  - `full_monthly` $99/mo / `full_yearly` $1009.80/yr (15% off) — **Recommended**
  - Enterprise = contact-us, no Stripe price.
- Migration 0022 → `user_subscriptions`, `payment_transactions`, `refund_requests`.
- `backend/routers/payments.py`: `/api/payments/{me,checkout,portal,status/{sid}}` +
  `/api/refund-requests` (create/list/approve/deny). Webhook `/api/stripe/webhook`
  updates the subscription tier from `checkout.session.completed`,
  `customer.subscription.{created,updated,deleted}`, `invoice.paid`, and
  `invoice.payment_failed`. Uses `stripe.Refund.create` from the platform-owner
  approval path.
- `backend/billing.py`: `assert_full_tier`/`require_tier` helpers. Grandfather via
  `BILLING_TIER_ALLOWLIST` (env var, comma-sep emails).
- **Tier gating** blocks the $49 (`oi`) and free tiers from:
  - Federal Proposals — `create_proposal`, `draft_document`, `evaluate_proposal`.
  - Investment Deals — venture-docs create/draft where kind ∈ `{investor_email,
    pitch_deck, business_plan, financials}`.
  - Accelerator Applications — venture-docs where kind = `accelerator_application`,
    plus `from-program` and `redraft-form` endpoints.
  - Scans (`investor_scan`, `accelerator_scan`) remain OPEN on all tiers.
- Frontend:
  - `pages/marketing/Pricing.js` — public `/pricing` with monthly/yearly toggle
    (Save 15% pill), Recommended ribbon on Full, "Contact us" on Enterprise.
  - `lib/billing.js` → `SubscriptionProvider` + `useSubscription` + `hasTier`.
  - `components/RequireTier.js` → wraps `/proposals`, `/investment-deals`,
    `/accelerator-applications`, `/opportunities/:id/proposal`.
  - `components/BillingCard.js` in Settings — shows tier, status, period end,
    Manage-in-Stripe portal button, and "Request refund" modal.
  - `components/RefundQueue.js` in Admin (`/admin` → Refunds tab, gated to
    `platform_owner`) with Approve (with optional partial refund cents) and Deny.
  - Sidebar lock icons on gated tabs when user tier < full.
  - `/billing/success?session_id=…` polls `/api/payments/status/{sid}` for 30s.
- New env vars (all in `backend/.env`): `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`,
  `STRIPE_WEBHOOK_SECRET`, `STRIPE_ACCOUNT_ID`, `STRIPE_MODE`,
  `CAPTUREAGENT_OWNER_EMAILS`, `BILLING_TIER_ALLOWLIST`.
- Data-testids: `plan-card-{oi,full,enterprise}`, `plan-cta-{oi,full,enterprise}`,
  `plan-price-{oi,full,enterprise}`, `pricing-interval-{month,year}`,
  `billing-card`, `billing-tier-name`, `billing-upgrade-btn`, `billing-portal-btn`,
  `billing-refund-btn`, `refund-modal`, `refund-submit`, `refund-cancel`,
  `refund-reason`, `tier-gate`, `tier-gate-upgrade`, `nav-proposals-lock`,
  `nav-deals-lock`, `nav-accel-apps-lock`, `tab-refunds`, `refund-queue`,
  `refunds-table`, `refund-row-*`, `refund-approve-*`, `refund-deny-*`,
  `refund-decision-modal`, `refund-amount-cents`, `refund-admin-notes`,
  `refund-decision-submit`, `billing-success`, `billing-success-cta`.
- **Testing**: `/app/backend/tests/test_phase2_billing.py` (17) +
  `/app/backend/tests/test_iter13_regression.py` (6) — all 23 pass.


## Account Deletion + GDPR Export ✅ 2026-07-18 (updated Phase 2)
- `DELETE /api/auth/me` now **cancels the active Stripe subscription** before
  wiping the profile.
- New `GET /api/auth/me/export` — returns a ZIP with `README.txt`,
  `account/{profile,subscription,memberships}.json`, and per-org folders
  containing `organization.json`, `profile.json`, `members.json`,
  `opportunities.json`, `proposals.json`, `proposal_documents.json`,
  `capabilities.json`, `competitive_reports.json`, `venture_docs.json`,
  `org_files.json`, `audit_log.json`. `password_hash`/`passwordHash` redacted.
  Data-testid: `export-data-btn` in Settings → Danger Zone.


## Phase 5 (Files & Media Storage + AI RAG) ✅ 2026-07-18
- Migration 0021 → `organization_files` table (org_id, category, entity_type,
  entity_id, filename, mime, size_bytes, storage_path, extracted_text, uploaded_by)
  and provisions the private Supabase Storage bucket `captureagent-org-files`.
- **Simplified RAG (per credit-saving lever)**: no pgvector. On upload we
  synchronously extract up to 50 KB of text from PDF (pypdf), DOCX (python-docx),
  and TXT/MD; the text is stored on the row and spliced into AI prompts by
  `files_storage.gather_org_file_context()`.
- `backend/files_storage.py`: httpx wrapper over Supabase Storage API using
  SERVICE_ROLE_KEY (upload / delete / signed_url) + text extraction dispatcher.
- `backend/routers/files.py`: POST (multipart upload), GET (list w/ category or
  entity filters), GET `/{fileId}/url` (short-lived signed URL), DELETE. Max
  25 MB per file. 7 valid categories, 3 valid entity types.
- AI integration:
    - `venture_ai._org_context(org, profile, files_context)` now splices in
      the extracted text; `draft()` and `form_from_program()` gained an
      optional `files_context` parameter; router callsites pass in
      `files_router.gather_org_file_context(...)` for org-level + entity-level files.
    - `routers/opportunities._enrich_prompt` gained `files_context`, wired in.
- Frontend:
    - `components/FilesPanel.js` — reusable upload/list/download/delete panel
      with `mode="category"` (org-level) or `mode="entity"` (attachment).
    - 7 category folders on `pages/Profile.js` (Past Performance,
      Commercialization Reports, Capability Statements, Quad Charts, Resumes
      of Key Personnel, Letters of Support, Pitch Decks).
    - Attachment section on OppDrawer, ProposalWorkspace, and Venture
      accelerator-application editor.
    - New `pages/DiskStorage.js` — unified browser (search + scope + category
      filters) linked from the sidebar between Accelerator Applications and Admin.
- Data-testids: `files-panel`, `files-panel-upload`, `files-panel-row-*`,
  `files-panel-download-*`, `files-panel-delete-*`, `disk-search`, `disk-scope`,
  `disk-category`, `disk-table`, `disk-row-*`, `disk-delete-*`, `nav-disk`.



## Phase 9 (Overleaf full git bidirectional sync) ✅ 2026-07-18
- Migration 0020 adds `overleaf_key` to `org_secrets` and `overleaf_project_id` + `overleaf_last_sync` to `proposals`.
- New `backend/overleaf.py` module wraps the `git` CLI via `asyncio.subprocess` in a
  tempdir, cloning `https://git:{token}@git.overleaf.com/{project_id}`. Pushes every
  volume as `.md` (round-trippable), plus a first-time-only `main.tex` wrapper using
  the LaTeX `markdown` package so `Compile` in Overleaf still produces a real PDF.
  Redacts the token from any surfaced git stderr.
- Router endpoints on `proposals.py`: link, unlink, push, pull. Auth uses the org's
  encrypted `overleaf_key` (KEY_COLUMNS updated in `org_keys.py`, Settings.js UI +
  save flow updated).
- New `OverleafPanel` component dropped into `ProposalWorkspace.js` — link input,
  push/pull/change/unlink buttons, last-sync timestamp, Open-in-Overleaf link.
- Startup guard: `overleaf.py` raises at import if `git` CLI is missing so deploy
  failures surface immediately, not on first user click.

## Phase 3 rest (AI chat drawer) ✅ 2026-07-18
- Backend `POST /api/orgs/{orgId}/ai/chat` — stateless (client re-sends full
  transcript), supports Claude/OpenAI/Gemini/Emergent/AskSage via `genai.generate`,
  merges optional `contextText` + `contextTitle` for doc-grounded answers, respects
  org's own API keys (no Emergent fallback), 400 on missing key / invalid message chain.
- Also fixed `/ai/options` to skip SAM + Overleaf keys when listing engines.
- New `AIChatButton` component: floating trigger + slide-in drawer with engine
  dropdown (driven by /ai/options), suggestion chips, per-org last-engine persistence
  in localStorage, error-safe (rolls back user bubble on send failure).
- Wired into: Federal Opportunities (context = visible pipeline summary), Federal
  Proposals workspace (context = all volumes concatenated), Investment Deals &
  Accelerator Applications (via VentureWorkspace — context = current docs).
- Data-testids: `ai-chat-open`, `ai-chat-drawer`, `ai-chat-engine`, `ai-chat-input`,
  `ai-chat-send`, `ai-chat-suggest-*`, `ai-chat-msg-*`, `ai-chat-close`, `ai-chat-reset`.

## Phase 8 (Structured fillable accelerator applications) ✅ 2026-07-18
- `venture_ai.form_from_program()` now returns `(content_md, content_json, model)` where
  `content_json = { kind: "acceleratorApplication", programName, keyFacts, questions:[
   {id, label, type: short|long|number|url, answer, tip} ] }`. Falls back to a
  `GENERIC_QUESTIONS` set when no key or no page text.
- The router `create_from_program` persists both to `venture_docs.content_md` (for
  export/download compatibility) and `content_json` (the source of truth for the form).
- New endpoint `POST /orgs/{orgId}/venture-docs/{docId}/redraft-form` — regenerates
  the schema while PRESERVING any answers the founder already typed (mapped by
  question `id`). New questions get their AI-drafted answers; obsolete questions
  are dropped.
- New `AcceleratorForm` component renders each question as a labeled input/textarea
  (short/long/number/url types) with the AI-generated tip below and a per-doc save
  button. `VentureWorkspace.EditModal` detects accelerator_application docs with a
  schema and swaps in the form (falls back to markdown textarea for legacy docs).
- Data-testids: `accelerator-form`, `accel-form-save`, `accel-form-redraft`,
  `accel-form-q-*`, `accel-form-input-*`.

## OUT-OF-PLAN reminder (deferred by user)
- "Export my data" feature: postpone until after ALL phases complete (per user
  message on 2026-07-18). Backend endpoint was drafted and reverted to avoid dead code.



## Phase 7 (Discovered accelerators/investors) ✅ 2026-07-18
- Migration 0018 → `discovered_venture` table (org-scoped; kind ∈ {'accelerator','investor'}; jsonb `data`).
- `venture_ai.py`: both scan prompts now append a fenced ```json``` block listing the programs
  they identified. `routers/venture.py::_extract_discovered_block` parses & strips it out of the
  markdown so users still see the same doc.
- `_persist_discovered()` upserts each program into `discovered_venture` on
  (organization_id, kind, name).
- New endpoints: GET `/orgs/{orgId}/venture/discovered/{accelerator|investor}`,
  DELETE `.../{itemId}`.
- Frontend: `Accelerators.js` and `PrivateCapital.js` fetch discovered rows on mount and after
  `ScanPanel.onDone`, merge them with the curated seed list (curated names win on dupe), and mark
  the AI-discovered rows with a small cyan **AI ✨** pill on the name column.
- ScanPanel gained an `onDone` prop so pages can refresh in-place after a scan completes.

## Account Deletion feature ✅ 2026-07-18 (added out-of-plan by user request)
- Migration 0019: softens the `on delete no action` foreign keys referencing `users`
  (organizations.owner_id, aor_certified_by, competitive_reports.created_by, venture_docs.created_by,
  subcontractor_grants.created_by, proposals.submitted_by, profile_edit_requests.decided_by,
  ai_jobs.user_id) → **SET NULL** so a user can delete themselves without leaving orphans.
  Also creates `account_deletion_requests` table for the Stripe-cancellation queue (Phase 2 hook).
- `DELETE /api/auth/me` (backend/routers/auth.py::delete_account):
  - Requires body `{ confirmEmail: <user's email>, reason?: str }`; email must match caller's own.
  - Wipes any org where the user is the ONLY active member (cascades opportunities, proposals,
    secrets, venture docs, files → everything).
  - For shared orgs: drops membership; if the user was owner, transfers ownership to the oldest
    remaining active owner → admin → editor (guaranteed non-null owner).
  - Deletes `public.users` row → all remaining pointers (`created_by`, `submitted_by`, etc.) become NULL.
  - Calls Supabase Admin API `DELETE /auth/v1/admin/users/{auth_uid}` with SUPABASE_SERVICE_ROLE_KEY
    to release the email; 404 treated as idempotent success.
  - Persists a row in `account_deletion_requests` (pending → completed/failed).
  - TODO(phase-2): call `stripe.Subscription.delete` before finalizing when Stripe lands.
- Frontend Settings.js gains a "Danger zone — delete account" card + confirmation Modal.
  User must type their exact email; textarea for optional reason; logs out and returns to /home
  on success. Tone: red-tinted borders, `data-testid`s: `danger-zone`, `delete-account-open`,
  `delete-account-modal`, `delete-account-confirm-email`, `delete-account-reason`,
  `delete-account-cancel`, `delete-account-confirm`.



## TERMINOLOGY LOCK — 2026-07-18
- User is the platform owner. **Never** use "Platform Creator", "Super Admin", or "Admin"
  in any user-facing UI text to describe them. In UI/marketing they = **CaptureAgent (the
  platform itself)**. Internal DB/code role can be `super_admin`, but display strings
  must not surface this. Org-level admins (customers running teams) remain "Admin".

## Phase 3 partial (Gemini engine) ✅ 2026-07-18
Gemini is now a first-class engine, callable via the same `genai.generate(engine, ...)` interface.
- Backend: `google-genai==2.12.1` installed; new `gemini_generate` in genai.py (Sync SDK
  called via `asyncio.to_thread` to keep FastAPI's loop free). Handles 401/403 → PermissionError,
  429 → RuntimeError. Models: gemini-2.5-flash (default), gemini-2.5-pro, gemini-2.5-flash-lite.
- Migration 0017_gemini_key.sql adds `gemini_key text default ''` to `org_secrets`.
- KEY_COLUMNS + all store/rotate/read code paths in org_keys.py + orgs.py Secrets endpoints
  now include gemini. `/ai/options` returns gemini as an available engine.
- All routers' local AI_ENGINES dicts (opportunities, competitive, capabilities) include gemini.
- Frontend Settings.js has a new "Google Gemini API key" input + status pill.
- The AI chat assistant UI (rest of Phase 3) is NOT built yet — awaiting continuation.



## PRODUCT EXPANSION IN PROGRESS 2026-07-18 (this session)
Massive feature plan approved by user across 9 phases. Batched in size-first order to
stay within a tight credit budget. Login/auth is CONFIRMED FIXED (do not touch).

### Phase 1 — Sidebar UX + Tab Reorder + Rename ✅ DONE
- New sidebar structure: aside is sticky h-screen; nav is scrollable; UserFooter (name/email/
  Sign out) is pinned and NEVER scrolls off-screen. Email truncates within sidebar boundary.
- New `sidebar-mode-toggle` button (top-left icon in header): switches between "persistent"
  and "drawer" mode. Persists in localStorage.
- Tab order updated to: Dashboard, Company Profile, Federal Opportunities, Federal Proposals,
  Competitive Analysis, Private Capital, Investment Deals, Accelerators, Accelerator Applications,
  Admin (admin-only), Settings.
- "Proposals" → "Federal Proposals" everywhere (sidebar label + page H1).
- Files: /app/frontend/src/components/Shell.js, /app/frontend/src/pages/Proposals.js.
- Verified via screenshot + automated toggle test.

### Phase 4 — Opportunity Summary + Points of Contact ✅ DONE
- SAM.gov fetch (integrations.py fetch_sam) now parses each notice's `pointOfContact` list into
  a compact `pocs: [{name, role: 'PoC'|'TPoC', title, email, phone}]` and stores the source
  description alongside it. Populated at pull time — no AI required to see contacts.
- New endpoint `POST /api/orgs/{orgId}/opportunities/{oppId}/summary` (opportunities router)
  generates a 3-5-paragraph AI narrative and merges any additional PoCs the AI extracted from
  the source description (deduped by name+email). Stores in `ai_enrichment` jsonb.
- OppDrawer now shows: "Opportunity Summary" section (paragraph text) + "Points of Contact"
  section (per-contact card with mailto/tel links). New "Summary & PoCs" AI button in the
  drawer actions row runs the endpoint.
- Files: backend/integrations.py, backend/routers/opportunities.py, frontend/OppDrawer.js.

### Phase 6 — Competitive Analysis: AI direct-competitor shortlist ✅ DONE
- USASpending pool expanded to top 30 primes + top 30 subs (was 10 each) — the raw pool the
  AI ranks from.
- New backend endpoint `POST /api/orgs/{orgId}/competitive/market/shortlist` runs an AI
  scoring pass over the pool using the org's own capability profile. Returns ranked list
  (0-100 overlapScore, rationale, confidence). Anti-hallucination guard: filters out any
  name not present in the actual USASpending pool.
- New Competitive Analysis page section: "Likely direct competitors — AI shortlist" appears
  when the user clicks "Shortlist direct competitors" in the market panel.
- Files: backend/competitive.py, backend/routers/competitive.py, frontend/CompetitiveAnalysis.js.

### Phases 2, 3, 5, 7, 8, 9 — QUEUED (approved, not yet started this batch)
See original message. In credit-efficient smallest-first order:
- Phase 9: Overleaf integration (git + Open in Overleaf; NOT embeddable — Overleaf sets
  X-Frame-Options DENY; user was informed).
- Phase 7: Accelerator + Private Capital AI scans that persist discovered rows.
- Phase 3: AI chat assistant (OpenAI/Anthropic/Gemini) attached to proposals/deals/apps/opps.
- Phase 8: Structured (fillable-form) accelerator applications tailored per program.
- Phase 5: Supabase Storage — Org files (7 subfolders) + per-item attachments + Disk Storage
  tab + AI RAG on uploads (pgvector).
- Phase 2: Stripe — 3 tiers ($49 / $99 / Enterprise), 15% annual off, admin-owned promo codes,
  admin refund workflow, per-tier feature gating.

### Product decisions locked with user this session
- Stripe country: US.
- Downgrade/cancel behavior: keep access to end of billing period (grace).
- Refunds: users request → super admin (user) approves in /admin.
- Files/RAG: full RAG (pgvector on Supabase) once Phase 5 begins.
- Overleaf: git-based integration only (embedding is impossible).
- Tab order + rename: applied as-specified.


## AUTH MIGRATION RESCUE 2026-07-16 (latest session)
- User's dev team migrated auth to SUPABASE AUTH (GoTrue) via GitHub sync ("Reconcile: Supabase
  auth onto Emergent's live code"). Old custom-JWT endpoints removed; frontend now uses
  supabase-js (signInWithPassword/signUp/resetPasswordForEmail); backend validates Supabase
  ES256 tokens via JWKS (auth_utils.py), auto-provisions/links public.users by auth_uid/email.
- USERS COULDN'T SIGN IN OR RESET. Three root causes found & fixed:
  1. auth.users.encrypted_password held WRONG bcrypt hashes ($2a$10 placeholders) — migration
     script never copied real hashes. FIX: copied public.users.password_hash ($2b$12, all intact)
     → auth.users.encrypted_password for all 15 users (joined on auth_uid). Original passwords
     work again. NO DATA LOST.
  2. frontend/.env was missing REACT_APP_SUPABASE_URL + REACT_APP_SUPABASE_ANON_KEY → supabase-js
     hit http://localhost → the users' "Failed to fetch". FIX: added both to frontend/.env.
  3. PRODUCTION BUILD FAILURE: package.json had ^2.47.10 for @supabase/supabase-js → resolved to
     2.110.6 requiring Node>=22 (env has Node 20) AND yarn.lock was missing. FIX: pinned exact
     2.47.10, regenerated yarn.lock; `yarn build` passes; deployment_agent scan = deployable.
- VERIFIED E2E in preview: GoTrue password login (original pw) → backend /auth/me (ES256/JWKS) →
  UI login lands on dashboard; forgot-password submits (GoTrue /recover 200, recovery_sent_at set).
- USER MUST CONFIGURE (Supabase dashboard, agent has no access): Auth → URL Configuration →
  Site URL https://captureagent.us + Redirect URLs must include https://captureagent.us/reset-password;
  built-in mailer is rate-limited (~2-4/hr) — recommend custom SMTP (Resend) for reliable reset emails.
- frontend/.env REACT_APP_BACKEND_URL restored to https://captureagent.us for deploy (flip to
  https://govcon-workspace.preview.emergentagent.com for preview UI testing).


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
