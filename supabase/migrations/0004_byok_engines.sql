-- Two additional bring-your-own-key providers: Emergent (universal LLM key)
-- and AskSage (GovCon-focused AI platform). Same envelope encryption as the
-- existing keys — values are encrypted with the org DEK before storage.

alter table org_secrets add column if not exists emergent_key text not null default '';
alter table org_secrets add column if not exists asksage_key text not null default '';
