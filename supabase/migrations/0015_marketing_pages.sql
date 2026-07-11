-- Public marketing pages: reviews wall + contact submissions.
create table if not exists marketing_reviews (
  id uuid primary key default gen_random_uuid(),
  first_name text not null,
  last_name text not null,
  show_full_name boolean not null default true,
  company text not null default '',
  company_anonymous boolean not null default false,
  email text not null,
  sector text not null default '',
  industry text not null default '',
  inquiry_type text not null default '',
  message text not null default '',
  headshot text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists marketing_contacts (
  id uuid primary key default gen_random_uuid(),
  first_name text not null,
  last_name text not null,
  company text not null default '',
  email text not null,
  sector text not null default '',
  industry text not null default '',
  inquiry_type text not null default '',
  message text not null default '',
  forwarded boolean not null default false,
  created_at timestamptz not null default now()
);
