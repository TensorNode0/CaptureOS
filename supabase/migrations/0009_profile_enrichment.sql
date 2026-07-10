-- Richer company profile: sharpens SAM.gov matching (PSC codes, target
-- agencies) and gives the AI real substance for proposals and venture docs
-- (size, locations, key personnel, web presence).
alter table org_profiles add column if not exists psc_codes text[] not null default '{}';
alter table org_profiles add column if not exists target_agencies text[] not null default '{}';
alter table org_profiles add column if not exists employees_count integer;
alter table org_profiles add column if not exists annual_revenue text not null default '';
alter table org_profiles add column if not exists locations text not null default '';
alter table org_profiles add column if not exists key_personnel text not null default '';
alter table org_profiles add column if not exists website text not null default '';
