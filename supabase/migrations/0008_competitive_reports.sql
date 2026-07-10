-- Competitive-analysis reports: verified USASpending award data plus AI OSINT
-- synthesis (BLUF, insights, strategies, recompete watch) per competitor.
create table if not exists competitive_reports (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  competitor      text not null,
  naics           text not null default '',
  status          text not null default 'running' check (status in ('running', 'done', 'error')),
  error           text not null default '',
  usaspending     jsonb not null default '{}'::jsonb,
  analysis        jsonb not null default '{}'::jsonb,
  model           text not null default '',
  created_by      uuid references users(id),
  created_at      timestamptz not null default now(),
  finished_at     timestamptz
);
create index if not exists idx_competitive_org on competitive_reports (organization_id, created_at desc);
alter table competitive_reports enable row level security;
