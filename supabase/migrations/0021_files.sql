-- 0021 — Files & Media Storage feature.
--
-- Two roles for a file:
--   1. ORG-LEVEL organization asset in one of seven curated categories
--      (past_performance, commercialization, capability_statements, quad_charts,
--       resumes, letters_of_support, pitch_decks). Feeds AI at every prompt.
--   2. PER-ITEM attachment linked to an opportunity, proposal, or venture_doc
--      (investor email, accelerator application). Feeds AI only for that item.
--
-- Text extraction happens synchronously on upload for PDF/DOCX/TXT (≤ 50KB
-- of extracted text stored) so AI prompts can splice it in without a round
-- trip to Supabase Storage on every AI call.
--
-- The actual file bytes live in Supabase Storage bucket `captureagent-org-files`
-- (created below with public=false; backend generates signed URLs on demand).
create table if not exists organization_files (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    -- '' when this is a per-item attachment (see entity_* below).
    category        text not null default '',
    -- '' + null when this is an org-level asset (see category above).
    entity_type     text not null default '' check (entity_type in
                        ('', 'opportunity', 'proposal', 'venture_doc')),
    entity_id       uuid,
    filename        text not null,
    mime            text not null default '',
    size_bytes      bigint not null default 0,
    storage_path    text not null,     -- {org_id}/{uuid}-{filename}
    extracted_text  text not null default '',
    uploaded_by     uuid references users(id) on delete set null,
    created_at      timestamptz not null default now()
);

create index if not exists idx_org_files_org_cat
    on organization_files (organization_id, category, created_at desc);
create index if not exists idx_org_files_entity
    on organization_files (organization_id, entity_type, entity_id);

-- Create the private storage bucket if it isn't already present. Public flag
-- is false — every download flows through a short-lived signed URL that only
-- the backend can mint, so RLS on `storage.objects` isn't relied upon.
insert into storage.buckets (id, name, public, created_at, updated_at)
values ('captureagent-org-files', 'captureagent-org-files', false, now(), now())
on conflict (id) do nothing;
