-- Unified AI-job telemetry: every long-running AI action gets a job row with
-- live stage/progress, token usage, metered cost, and cooperative cancellation.
create table if not exists ai_jobs (
  id               uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(id) on delete cascade,
  user_id          uuid references users(id),
  kind             text not null,           -- capability.generate | proposal.draft | ...
  ref_id           text not null default '',-- opp/doc/report id the job belongs to
  status           text not null default 'queued'
                   check (status in ('queued', 'running', 'done', 'error', 'cancelled')),
  stage            text not null default 'Queued',
  progress         integer not null default 0,   -- 0-100
  engine           text not null default 'claude',
  model            text not null default '',
  effort           text not null default 'standard',
  input_tokens     integer not null default 0,
  output_tokens    integer not null default 0,
  cost_usd         numeric(12,6) not null default 0,
  error            text not null default '',
  cancel_requested boolean not null default false,
  created_at       timestamptz not null default now(),
  finished_at      timestamptz
);
create index if not exists idx_ai_jobs_org on ai_jobs (organization_id, created_at desc);
alter table ai_jobs enable row level security;
