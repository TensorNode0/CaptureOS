-- Venture workspace documents: investor outreach, pitch decks, business
-- plans, financial models, and accelerator applications — drafted by AI,
-- edited by humans, exported to Office formats.
create table if not exists venture_docs (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  kind            text not null check (kind in
                    ('investor_email', 'pitch_deck', 'business_plan',
                     'financials', 'accelerator_application')),
  target          text not null default '',   -- investor / program name
  title           text not null default '',
  content_md      text not null default '',
  content_json    jsonb not null default '{}'::jsonb,
  status          text not null default 'draft' check (status in ('draft', 'final')),
  draft_status    text not null default 'idle' check (draft_status in ('idle', 'drafting', 'error')),
  draft_error     text not null default '',
  model           text not null default '',
  created_by      uuid references users(id),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists idx_venture_docs_org on venture_docs (organization_id, kind);
alter table venture_docs enable row level security;
