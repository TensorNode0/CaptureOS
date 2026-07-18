-- 0018 — Discovered venture programs persisted from AI scans so the results
-- augment the curated tables in Accelerators / Private Capital pages instead of
-- only living inside a Word doc. jsonb `data` keeps the shape flexible per kind:
--   accelerator: { name, dueDate, duration, terms, attendance, url, source,
--                  fitReason, verified }
--   investor:    { name, checkSize, stage, sector, recentDeal, url, source,
--                  fitReason, verified }
create table if not exists discovered_venture (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    kind            text not null check (kind in ('accelerator', 'investor')),
    name            text not null,
    data            jsonb not null default '{}'::jsonb,
    source_doc_id   uuid references venture_docs(id) on delete set null,
    discovered_at   timestamptz not null default now(),
    unique (organization_id, kind, name)
);

create index if not exists idx_discovered_venture_org_kind
    on discovered_venture (organization_id, kind, discovered_at desc);
