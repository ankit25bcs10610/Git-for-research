-- Run this in your Supabase project's SQL editor (Dashboard -> SQL Editor)
-- to create the table the landing page's waitlist form writes to.

create table if not exists waitlist (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  source text not null check (source in ('download', 'plan', 'sales')),
  plan text,
  created_at timestamptz not null default now()
);

-- The anon key used by the frontend can only INSERT (sign up), never
-- read back other people's emails, since Row Level Security is on and
-- no select policy is granted to the anon role.
alter table waitlist enable row level security;

create policy "Allow public inserts" on waitlist
  for insert
  to anon
  with check (true);
