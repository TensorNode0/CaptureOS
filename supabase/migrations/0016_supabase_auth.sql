-- Move authentication to Supabase Auth (GoTrue). public.users becomes a
-- profile mirror linked to auth.users by auth_uid; all existing foreign keys
-- to public.users(id) are unchanged. Passwords/email are owned by GoTrue, so
-- password_hash is no longer required (kept nullable for the migration window).
alter table users add column if not exists auth_uid uuid unique;
alter table users alter column password_hash drop not null;
