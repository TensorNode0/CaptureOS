-- 0017 — Store Google Gemini API key alongside the other per-org LLM keys.
-- Envelope-encrypted like the others (Fernet under org DEK, wrapped by
-- SECRETS_ENC_KEY). Nullable/empty when the org hasn't configured Gemini yet.
alter table org_secrets add column if not exists gemini_key text not null default '';
