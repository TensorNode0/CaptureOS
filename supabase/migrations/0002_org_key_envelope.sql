-- Per-organization envelope encryption for stored API keys.
--
-- Each org gets its own random data-encryption key (DEK). API-key values are
-- encrypted with the org DEK; the DEK itself is stored wrapped (encrypted) by
-- the master key (SECRETS_ENC_KEY), which lives outside the database. A
-- database dump or Table Editor view alone can never reveal a key, and each
-- org's key material can be rotated independently.

alter table org_secrets add column if not exists dek_wrapped text not null default '';
alter table org_secrets add column if not exists key_version integer not null default 1;
