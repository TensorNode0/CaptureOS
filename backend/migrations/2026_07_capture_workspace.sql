alter table opportunities
  add column if not exists scope_summary text not null default '',
  add column if not exists tags jsonb not null default '[]'::jsonb,
  add column if not exists opp_type text not null default '',
  add column if not exists acq_stage text not null default '',
  add column if not exists recompete text not null default '',
  add column if not exists due_time text not null default '',
  add column if not exists psc text not null default '',
  add column if not exists naics_title text not null default '',
  add column if not exists size_standard text not null default '',
  add column if not exists value_type text not null default '',
  add column if not exists value_confidence text not null default '',
  add column if not exists addressable_value double precision,
  add column if not exists contract_type text not null default '',
  add column if not exists awards_count text not null default '',
  add column if not exists vehicle_access text not null default '',
  add column if not exists pursuit_role text not null default '',
  add column if not exists incumbent text not null default '',
  add column if not exists competition jsonb not null default '{}'::jsonb,
  add column if not exists capture jsonb not null default '{}'::jsonb,
  add column if not exists watch boolean not null default false,
  add column if not exists amendments jsonb not null default '[]'::jsonb,
  add column if not exists ai_enrichment jsonb;

alter table org_profiles
  add column if not exists vehicles jsonb not null default '[]'::jsonb,
  add column if not exists no_go text not null default '',
  add column if not exists pref_role text not null default '';
