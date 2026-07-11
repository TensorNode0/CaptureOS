-- Proposal customer targeting: commercial market + government customer
-- (sector / branch / PEO / TPOC / contracting officer) plus the AI
-- directory-currency check result under customer.aiCheck.
alter table proposals add column if not exists customer jsonb;
