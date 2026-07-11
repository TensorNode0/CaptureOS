-- Web-search scan reports join the venture doc kinds (AI-tailored investor
-- and accelerator scans rendered on the Private Capital / Accelerators tabs).
alter table venture_docs drop constraint if exists venture_docs_kind_check;
alter table venture_docs add constraint venture_docs_kind_check check (kind in
  ('investor_email', 'pitch_deck', 'business_plan',
   'financials', 'accelerator_application',
   'investor_scan', 'accelerator_scan'));
