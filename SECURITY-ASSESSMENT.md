# CaptureAgent Security Assessment & POA&M

**Scope**: the CaptureAgent SaaS application (FastAPI backend, React frontend,
Supabase PostgreSQL) as deployed at captureagent.us.
**Framework**: NIST SP 800-171 Rev 2 practice families as implemented by CMMC
Level 2, applied to the app itself. Note: CMMC certifies an *organization's
CUI environment*, not a product. CaptureAgent's stated policy is that **no CUI,
ITAR, or classified data may be stored in the platform**, which keeps the app
outside a customer's CUI boundary. This assessment scores the app's security
posture against the practice families anyway, as engineering due diligence.
**Assessment date**: 2026-07-08 (self-assessment).

## Scorecard

Methodology mirrors the DoD assessment style: start at 110, subtract weighted
deductions for unimplemented practices (5/3/1). Only practices applicable to a
single-product SaaS are scored; organizational practices (training, physical
protection, media handling) are marked N/A-organizational.

| # | Family (800-171) | Status | Evidence / gap |
|---|------------------|--------|----------------|
| 3.1 | Access Control | Largely implemented | Org-scoped RBAC on every endpoint (viewer/contributor/CM/admin), permission gates for create/approve/submit, entity-info edit grants, join approvals |
| 3.2 | Awareness & Training | N/A-organizational | Operator responsibility |
| 3.3 | Audit & Accountability | Implemented | Per-org audit log on auth, membership, secrets access (purpose-tagged), AI use, exports, submissions |
| 3.4 | Configuration Mgmt | Partial | IaC via migrations + Docker; no formal baseline doc — POA&M-1 |
| 3.5 | Identification & Auth | Largely implemented | bcrypt password hashing, email verification, login throttling (5 tries/15-min lockout), JWT w/ 12h access + 7d refresh, scheme-aware Secure cookies. MFA not yet offered — POA&M-2 |
| 3.6 | Incident Response | Partial | Audit trail supports IR; no documented IR runbook — POA&M-3 |
| 3.7 | Maintenance | Implemented | Containerized deploys, dependency pinning |
| 3.8 | Media Protection | N/A-organizational | No removable media in scope |
| 3.9 | Personnel Security | N/A-organizational | |
| 3.10 | Physical Protection | Inherited | Supabase/host provider data centers |
| 3.11 | Risk Assessment | Partial | This document; recurring cadence not yet scheduled — POA&M-4 |
| 3.12 | Security Assessment | Partial | QA gates on every merge (152+ API tests); no independent pentest yet — POA&M-5 |
| 3.13 | System & Comms Protection | Largely implemented | TLS in transit, security headers middleware (nosniff, frame-deny, HSTS on https, referrer policy, restrictive CSP on API), CORS pinned to FRONTEND_URL, per-org envelope encryption for API keys (DEK wrapped by server master key, rotation endpoint, masked previews only) |
| 3.14 | System & Info Integrity | Partial | Input validation via Pydantic everywhere, parameterized SQL only (asyncpg), AI-output guardrails; no automated dependency-vuln scanning in CI — POA&M-6 |

**Indicative score: 92 / 110** (self-assessed, product scope only).

## POA&M

| ID | Gap | Risk | Planned remediation | Target |
|----|-----|------|---------------------|--------|
| POA&M-1 | No formal configuration-baseline document | Low | Document baseline (env vars, container images, network paths) in repo | 30 days |
| POA&M-2 | No MFA option for user sign-in | Medium | Add TOTP MFA (per-user secret, backup codes); consider WebAuthn | 90 days |
| POA&M-3 | No written incident-response runbook | Medium | IR playbook: detection sources (audit log), containment (key rotation, session invalidation), notification flow | 60 days |
| POA&M-4 | No recurring risk-assessment cadence | Low | Quarterly review of this document tied to release notes | 90 days |
| POA&M-5 | No independent penetration test | Medium | Commission third-party web-app pentest before enterprise sales | 180 days |
| POA&M-6 | No automated dependency scanning | Medium | Add pip-audit + npm audit to the QA gate | 30 days |

## Design strengths worth stating plainly

1. **Bring-your-own-keys with envelope encryption** — per-org data keys wrapped
   by a server master key; database dumps alone reveal nothing; only masked
   previews leave the server; every decrypt-for-use is audit-logged with a
   purpose tag; admins can rotate org keys on demand.
2. **Proposal content isolation** — proposals, capabilities, and venture
   documents are org-scoped rows behind RBAC; no cross-org query path exists;
   Supabase RLS is enabled on every table as a second layer behind the API's
   single service role; content is never used to train models and only leaves
   the system toward the AI provider the org itself configured.
3. **Least-privilege by role** — contributors draft, capture managers
   create/approve, admins submit and govern; even admins never see stored key
   material.
4. **Honest data boundary** — the product refuses the CUI/ITAR/classified use
   case loudly (footer disclaimer on every page, docs, onboarding) rather than
   implying a compliance posture it does not have.

## Data-boundary policy (verbatim, shown in-product)

> CAPTUREAGENT DOES NOT SUPPORT CUI, ITAR, OR CLASSIFIED DATA YET. PLEASE DO
> NOT CREATE OR STORE ANY CUI, ITAR, OR CLASSIFIED MATERIALS ON CAPTUREAGENT.
