-- 0019 — Account deletion support: soften `on delete no action` foreign keys
-- referencing `users` so a user can delete their account without violating
-- historical audit references. Historical rows (competitive reports, venture
-- docs, proposal submissions, org-ownership audit trail) keep their content;
-- only the pointer to the deleted user becomes NULL. Orgs the user solely
-- owns are deleted separately at the application layer (cascades everything).
alter table organizations         drop constraint if exists organizations_owner_id_fkey;
alter table organizations         add  constraint organizations_owner_id_fkey
    foreign key (owner_id)        references users(id) on delete set null;

alter table organizations         drop constraint if exists organizations_aor_certified_by_fkey;
alter table organizations         add  constraint organizations_aor_certified_by_fkey
    foreign key (aor_certified_by) references users(id) on delete set null;

alter table competitive_reports   drop constraint if exists competitive_reports_created_by_fkey;
alter table competitive_reports   add  constraint competitive_reports_created_by_fkey
    foreign key (created_by)      references users(id) on delete set null;

alter table venture_docs          drop constraint if exists venture_docs_created_by_fkey;
alter table venture_docs          add  constraint venture_docs_created_by_fkey
    foreign key (created_by)      references users(id) on delete set null;

alter table subcontractor_grants  drop constraint if exists subcontractor_grants_created_by_fkey;
alter table subcontractor_grants  add  constraint subcontractor_grants_created_by_fkey
    foreign key (created_by)      references users(id) on delete set null;

alter table proposals             drop constraint if exists proposals_submitted_by_fkey;
alter table proposals             add  constraint proposals_submitted_by_fkey
    foreign key (submitted_by)    references users(id) on delete set null;

alter table profile_edit_requests drop constraint if exists profile_edit_requests_decided_by_fkey;
alter table profile_edit_requests add  constraint profile_edit_requests_decided_by_fkey
    foreign key (decided_by)      references users(id) on delete set null;

alter table ai_jobs               drop constraint if exists ai_jobs_user_id_fkey;
alter table ai_jobs               add  constraint ai_jobs_user_id_fkey
    foreign key (user_id)         references users(id) on delete set null;

-- Deletion request table lets the "cancel subscription then wipe" flow live
-- through a Stripe webhook when Phase 2 lands: we mark the user as pending
-- deletion, then finalize on Stripe subscription.deleted. Not used yet, kept
-- as an escape hatch for the paid-tier flow described in the roadmap.
create table if not exists account_deletion_requests (
    id             uuid primary key default gen_random_uuid(),
    user_id        uuid not null references users(id) on delete cascade,
    email          text not null,
    reason         text not null default '',
    requested_at   timestamptz not null default now(),
    orgs_deleted   int not null default 0,
    memberships_dropped int not null default 0,
    completed_at   timestamptz,
    status         text not null default 'pending' check (status in ('pending','completed','failed'))
);
