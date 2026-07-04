# CaptureAgent Security Architecture

## Per-organization API keys (SAM.gov, Anthropic, OpenAI)

**Who can do what**

| Role            | Use the keys (AI drafting, SAM pulls) | See masked previews / edit keys | Rotate encryption key |
|-----------------|:---:|:---:|:---:|
| viewer          | read-only app access, no key use | — | — |
| editor          | ✔ (keys used server-side, never shown) | — | — |
| admin / owner   | ✔ | ✔ (masked only, e.g. `sk-…4f2a`) | ✔ |

Full key values are **never** returned to any browser, including the org
admin's — the UI only ever receives a masked preview. Members *use* the keys
by pressing feature buttons; the server decrypts in memory, makes the outbound
call, and discards the plaintext.

**Envelope encryption (how keys are stored)**

1. Each organization gets its own random 256-bit **data-encryption key (DEK)**.
2. API-key values are encrypted with the org's DEK (Fernet: AES-128-CBC +
   HMAC-SHA256) before they are written to Supabase.
3. The DEK itself is stored **wrapped** — encrypted by the master key
   (`SECRETS_ENC_KEY`), which exists only in the server environment. It is
   never in the database, the repository, or any API response.
4. Admins can **rotate** an org's DEK at any time (Settings → API Keys →
   Rotate encryption key): secrets are re-encrypted under a fresh key and the
   version counter increments.

Consequences:

- A database dump, a Supabase Table Editor view, or a stolen backup reveals
  **only ciphertext** — useless without the server-side master key.
- Compromise of one org's DEK never exposes another org's keys.
- Every decrypt-for-use writes a `secrets.access` event into the org's own
  audit log with a purpose tag (`intel.scan`, `capability.generate`,
  `proposal.draft`, `pull.sam_grants`, `ai.verify_refresh`,
  `admin.view_masked`), so orgs can verify exactly when and why their keys
  were touched.

**Honest limits (read this)**

The server must briefly decrypt a key in memory to call SAM/Anthropic/OpenAI
on the org's behalf. That means an operator with full control of the running
server can never be *mathematically* prevented from accessing keys the server
itself uses — this is true of every SaaS product that makes API calls for its
customers. The design goal is therefore: no plaintext at rest anywhere, no
plaintext to any client, per-org blast radius, rotation, and a tamper-evident
audit trail. For a stronger operator-separation story in production, move the
master key from the environment into a managed KMS (AWS KMS, GCP KMS, or
Supabase Vault) so every unwrap is itself logged by the cloud provider outside
the operator's reach.

## Other controls

- **Transport**: HTTPS/TLS in production (Supabase connections are TLS).
- **Passwords**: bcrypt with per-password salt; login lockout (5 attempts /
  15 minutes per IP+email).
- **Sessions**: httpOnly, Secure cookies (12h access / 7d refresh JWTs).
- **RBAC**: viewer < editor < admin < owner enforced on every org route.
- **Row Level Security**: enabled on every table with no policies, so
  Supabase's auto-generated PostgREST API exposes nothing.
- **Audit log**: per-org, append-style log of org changes, member changes,
  AI/pull activity, and key access.

## CMMC / NIST 800-171 positioning

CMMC certification is an **organizational** assessment (the NIST SP 800-171
control set, an SSP, and scoping of where CUI lives) — no single application
feature makes a company "CMMC compliant." CaptureAgent supports the relevant
practice families for the data it holds: access control (RBAC, least
privilege), identification & authentication (unique accounts, lockout),
audit & accountability (per-org audit log incl. key access), and protection
of data at rest and in transit (envelope encryption, TLS).

**Policy**: CaptureAgent workspaces are for *unclassified pipeline metadata*.
Do not store CUI or ITAR-controlled technical data in the app; that belongs
in a separately scoped, controlled environment.

## Reporting a vulnerability

Open a private GitHub security advisory on this repository, or contact the
repository owner directly. Please do not open public issues for security
reports.
