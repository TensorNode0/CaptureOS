-- Notice lifecycle status from the source feed (pre-release = presolicitation
-- or sources-sought; open = active solicitation). Closed is derived from the
-- response deadline at read time.
alter table opportunities add column if not exists notice_status text not null default 'open';
