-- Subcontractor role: rank-0 members who see ONLY the specific proposal
-- documents / capability sections an admin grants them, read or write.

alter table memberships drop constraint if exists memberships_role_check;
alter table memberships add constraint memberships_role_check
  check (role in ('viewer', 'editor', 'technical_writer', 'proposal_writer',
                  'pi', 'capture_manager', 'admin', 'owner', 'subcontractor'));

create table if not exists subcontractor_grants (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  membership_id   uuid not null references memberships(id) on delete cascade,
  opportunity_id  uuid not null references opportunities(id) on delete cascade,
  resource_type   text not null check (resource_type in ('proposal_doc', 'capability_section')),
  resource_id     text not null,   -- proposal_documents.id or section key (summary|sow|wbs|budget)
  access          text not null check (access in ('read', 'write')),
  created_by      uuid references users(id),
  created_at      timestamptz not null default now(),
  unique (membership_id, resource_type, resource_id)
);
create index if not exists idx_sub_grants_org on subcontractor_grants (organization_id);
create index if not exists idx_sub_grants_membership on subcontractor_grants (membership_id);
alter table subcontractor_grants enable row level security;
