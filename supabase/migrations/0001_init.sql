-- CaptureOS / GovCon Command Center — initial PostgreSQL schema
-- Target: Supabase (PostgreSQL 15+), also works on any vanilla PostgreSQL 13+.
--
-- Apply with:  python backend/apply_migrations.py   (uses DATABASE_URL)
-- or paste into the Supabase SQL editor.
--
-- NOTE ON RLS: every table enables Row Level Security with NO policies.
-- The FastAPI backend connects as the table owner (postgres role), which is
-- not subject to RLS, while Supabase's auto-generated PostgREST API (anon /
-- authenticated keys) is fully locked out. If you ever want browser clients
-- to query Supabase directly, add explicit policies per table first.

-- ─────────────────────────────── users & auth ───────────────────────────────

create table if not exists users (
    id             uuid primary key default gen_random_uuid(),
    email          text not null unique,
    name           text not null default '',
    password_hash  text not null,
    email_verified boolean not null default false,
    created_at     timestamptz not null default now()
);

create table if not exists email_verify_tokens (
    id         uuid primary key default gen_random_uuid(),
    token      text not null unique,
    user_id    uuid not null references users(id) on delete cascade,
    expires_at timestamptz not null,
    used       boolean not null default false
);
create index if not exists email_verify_tokens_expires_idx on email_verify_tokens (expires_at);

create table if not exists password_reset_tokens (
    id         uuid primary key default gen_random_uuid(),
    token      text not null unique,
    user_id    uuid not null references users(id) on delete cascade,
    expires_at timestamptz not null,
    used       boolean not null default false
);
create index if not exists password_reset_tokens_expires_idx on password_reset_tokens (expires_at);

create table if not exists login_attempts (
    identifier text primary key,
    count      integer not null default 0,
    lock_until timestamptz
);

-- ─────────────────────────────── organizations ──────────────────────────────

create table if not exists organizations (
    id         uuid primary key default gen_random_uuid(),
    name       text not null,
    naics      jsonb not null default '[]',
    keywords   jsonb not null default '[]',
    owner_id   uuid references users(id),
    join_code  text,
    created_at timestamptz not null default now()
);
create index if not exists organizations_join_code_idx on organizations (join_code);

create table if not exists memberships (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references users(id) on delete cascade,
    invited_email   text,
    organization_id uuid not null references organizations(id) on delete cascade,
    role            text not null default 'viewer'
                    check (role in ('viewer', 'editor', 'admin', 'owner')),
    invited_by      uuid,
    status          text not null default 'active'
                    check (status in ('active', 'invited')),
    joined_via_code boolean not null default false,
    created_at      timestamptz not null default now()
);
create index if not exists memberships_org_user_idx on memberships (organization_id, user_id);
create index if not exists memberships_invited_email_idx on memberships (invited_email);
create index if not exists memberships_user_idx on memberships (user_id);

create table if not exists org_profiles (
    organization_id   uuid primary key references organizations(id) on delete cascade,
    uei               text not null default '',
    cage              text not null default '',
    sam_active        boolean not null default false,
    is_small          boolean not null default true,
    certs             jsonb not null default '{}',
    cmmc_level        text not null default 'Level 1',
    sprs_score        integer,
    size_note         text not null default '',
    notes             text not null default '',
    capabilities      text not null default '',
    past_performance  text not null default '',
    tech_focus        jsonb not null default '[]',
    differentiators   text not null default '',
    commercialization text not null default '',
    clearances        text not null default ''
);

-- Per-org API keys, encrypted at rest with Fernet (SECRETS_ENC_KEY).
create table if not exists org_secrets (
    organization_id uuid primary key references organizations(id) on delete cascade,
    anthropic_key   text not null default '',
    sam_key         text not null default '',
    openai_key      text not null default '',
    updated_by      uuid,
    updated_at      timestamptz not null default now()
);

-- ─────────────────────────────── opportunities ──────────────────────────────

create table if not exists opportunities (
    id                uuid primary key default gen_random_uuid(),
    organization_id   uuid not null references organizations(id) on delete cascade,
    title             text not null,
    sol_number        text not null default '',
    agency            text not null default '',
    office            text not null default '',
    vehicle           text not null default 'RFP',
    set_aside         text not null default 'None',
    naics             text not null default '',
    ceiling           double precision not null default 0,
    pop               text not null default '',
    due_date          text,
    stage             text not null default 'Identified',
    url               text not null default '',
    win_themes        text not null default '',
    source            text not null default 'manual',
    last_verified     timestamptz,
    verify_report     jsonb,
    links             jsonb not null default '[]',
    fit               jsonb not null default '{}',
    pwin              integer not null default 0,
    proposal_strength double precision not null default 0,
    compliance        jsonb not null default '[]',
    budget            jsonb not null default '{}',
    criteria          jsonb not null default '[]',
    decision          jsonb not null default '{"call": "TBD", "rationale": ""}',
    created_by        uuid,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists opportunities_org_idx on opportunities (organization_id);
create index if not exists opportunities_org_sol_idx on opportunities (organization_id, sol_number);

-- ─────────────────────────────── ops & audit ────────────────────────────────

create table if not exists audit_log (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    user_id         uuid,
    user_email      text,
    user_name       text,
    action          text not null,
    target          text,
    meta            jsonb not null default '{}',
    at              timestamptz not null default now()
);
create index if not exists audit_log_org_at_idx on audit_log (organization_id, at desc);

create table if not exists refresh_jobs (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    type            text not null default '',
    status          text not null default 'queued',
    started_by      uuid,
    started_at      timestamptz not null default now(),
    finished_at     timestamptz,
    summary         text
);

create table if not exists intel_jobs (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    status          text not null default 'queued',
    tier            text not null default 'standard',
    started_by      uuid,
    started_at      timestamptz not null default now(),
    finished_at     timestamptz,
    report_id       uuid,
    summary         text,
    model           text,
    error           text
);

create table if not exists intel_reports (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    created_by      uuid,
    created_at      timestamptz not null default now(),
    tier            text not null default 'standard',
    model           text not null default '',
    usage           jsonb not null default '{}',
    report          jsonb not null default '{}'
);
create index if not exists intel_reports_org_idx on intel_reports (organization_id, created_at desc);

-- ──────────────────────── capability & proposal package ─────────────────────

-- AI-proposed capability for an opportunity: title, abstract, executive
-- summary, keywords, SVG concept rendering, charts/tables, SoW, WBS +
-- schedule, and budget — all inside `content` (jsonb). One live row per
-- opportunity; prior versions are archived in capability_versions.
create table if not exists capabilities (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    opportunity_id  uuid not null unique references opportunities(id) on delete cascade,
    status          text not null default 'draft'
                    check (status in ('draft', 'approved')),
    version         integer not null default 1,
    content         jsonb not null default '{}',
    rendering_png   bytea,
    model           text not null default '',
    generation_status text not null default 'idle'
                    check (generation_status in ('idle', 'generating', 'ready', 'error')),
    generation_error  text not null default '',
    created_by      uuid,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    approved_by     uuid,
    approved_at     timestamptz
);
create index if not exists capabilities_org_idx on capabilities (organization_id);

create table if not exists capability_versions (
    id            uuid primary key default gen_random_uuid(),
    capability_id uuid not null references capabilities(id) on delete cascade,
    version       integer not null,
    status        text not null default 'draft',
    content       jsonb not null default '{}',
    created_by    uuid,
    created_at    timestamptz not null default now()
);
create index if not exists capability_versions_cap_idx on capability_versions (capability_id, version desc);

create table if not exists proposals (
    id              uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    opportunity_id  uuid not null unique references opportunities(id) on delete cascade,
    status          text not null default 'draft'
                    check (status in ('draft', 'final')),
    created_by      uuid,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
create index if not exists proposals_org_idx on proposals (organization_id);

-- One row per volume/document in the proposal package. Narrative volumes are
-- markdown (content_md → .docx export); the cost volume also carries
-- structured rows (content_json → .xlsx export); the briefing deck is
-- generated from capability + volumes (→ .pptx export).
create table if not exists proposal_documents (
    id           uuid primary key default gen_random_uuid(),
    proposal_id  uuid not null references proposals(id) on delete cascade,
    doc_type     text not null,
    title        text not null,
    fmt          text not null default 'docx'
                 check (fmt in ('docx', 'xlsx', 'pptx')),
    content_md   text not null default '',
    content_json jsonb not null default '{}',
    status       text not null default 'empty'
                 check (status in ('empty', 'drafted', 'edited', 'final')),
    draft_status text not null default 'idle'
                 check (draft_status in ('idle', 'drafting', 'error')),
    draft_error  text not null default '',
    model        text not null default '',
    sort_order   integer not null default 0,
    updated_by   uuid,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),
    unique (proposal_id, doc_type)
);

-- ─────────────────────────── RLS lockdown (Supabase) ────────────────────────

alter table users enable row level security;
alter table email_verify_tokens enable row level security;
alter table password_reset_tokens enable row level security;
alter table login_attempts enable row level security;
alter table organizations enable row level security;
alter table memberships enable row level security;
alter table org_profiles enable row level security;
alter table org_secrets enable row level security;
alter table opportunities enable row level security;
alter table audit_log enable row level security;
alter table refresh_jobs enable row level security;
alter table intel_jobs enable row level security;
alter table intel_reports enable row level security;
alter table capabilities enable row level security;
alter table capability_versions enable row level security;
alter table proposals enable row level security;
alter table proposal_documents enable row level security;
