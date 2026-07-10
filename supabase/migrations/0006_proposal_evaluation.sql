-- AI color-team evaluation of the drafted proposal package (SSEB-style
-- scores, strengths/weaknesses/risks, compliance gaps, recommendations).
alter table proposals add column if not exists evaluation jsonb;
alter table proposals add column if not exists evaluated_at timestamptz;
