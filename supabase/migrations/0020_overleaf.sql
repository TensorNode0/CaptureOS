-- 0020 — Overleaf integration: bidirectional git sync between a Federal
-- Proposal and an Overleaf project.
--
-- Two pieces of state:
--   1. Per-org auth token: added as `overleaf_key` on `org_secrets` (same
--      envelope encryption as the other keys — see 0002_org_key_envelope.sql
--      and org_keys.py). Users create tokens at overleaf.com → Account →
--      Git Integration → New authentication token.
--   2. Per-proposal Overleaf project pointer: two columns on `proposals`:
--        overleaf_project_id  — the {project_id} in https://git.overleaf.com/{project_id}
--        overleaf_last_sync   — informational timestamp of the last successful
--                               push/pull, shown next to the button in the UI.
alter table org_secrets add column if not exists overleaf_key text not null default '';

alter table proposals
    add column if not exists overleaf_project_id text not null default '',
    add column if not exists overleaf_last_sync  timestamptz;
