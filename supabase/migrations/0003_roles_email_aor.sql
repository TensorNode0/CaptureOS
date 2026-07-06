-- Functional roles, AOR certification, domain-based org join, profile edit
-- grants, and proposal submission tracking.

-- Organizations get a company email domain (drives signup routing) and AOR
-- (Authorized Organizational Representative) certification metadata.
alter table organizations add column if not exists domain text not null default '';
create unique index if not exists idx_orgs_domain
  on organizations (lower(domain)) where domain <> '';
alter table organizations add column if not exists aor_certified_by uuid references users(id);
alter table organizations add column if not exists aor_certified_at timestamptz;

-- Memberships: functional roles and the 'pending' status (self-signup with a
-- known company domain waits for admin approval).
alter table memberships add column if not exists title text not null default '';
alter table memberships drop constraint if exists memberships_role_check;
alter table memberships add constraint memberships_role_check
  check (role in ('viewer', 'editor', 'technical_writer', 'proposal_writer',
                  'pi', 'capture_manager', 'admin', 'owner'));
alter table memberships drop constraint if exists memberships_status_check;
alter table memberships add constraint memberships_status_check
  check (status in ('active', 'invited', 'pending'));

-- Proposals gain the 'submitted' state.
alter table proposals drop constraint if exists proposals_status_check;
alter table proposals add constraint proposals_status_check
  check (status in ('draft', 'final', 'submitted'));

-- Capture managers must request admin approval to edit entity (company) info.
create table if not exists profile_edit_requests (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  requested_by    uuid not null references users(id) on delete cascade,
  reason          text not null default '',
  status          text not null default 'pending',  -- pending|approved|denied
  decided_by      uuid references users(id),
  decided_at      timestamptz,
  expires_at      timestamptz,                      -- edit window when approved
  created_at      timestamptz not null default now()
);
create index if not exists idx_edit_requests_org
  on profile_edit_requests (organization_id, status);
alter table profile_edit_requests enable row level security;

-- Proposal submission (admin-only action).
alter table proposals add column if not exists submitted_at timestamptz;
alter table proposals add column if not exists submitted_by uuid references users(id);
