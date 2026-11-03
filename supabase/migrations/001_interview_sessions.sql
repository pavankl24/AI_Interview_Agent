create table if not exists public.interview_sessions (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null,
  topic text not null,
  difficulty text not null check (difficulty in ('Beginner', 'Intermediate', 'Advanced')),
  interview_mode text not null check (interview_mode in ('Balanced', 'Technical conversation', 'Coding & problem solving')),
  max_questions integer not null check (max_questions between 1 and 50),
  overall_score numeric(4, 2),
  report jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists interview_sessions_client_created_idx
  on public.interview_sessions (client_id, created_at desc);

alter table public.interview_sessions enable row level security;
-- The FastAPI server accesses this table with a server-only Supabase secret key.
-- No browser roles receive direct table access. Add Supabase Auth and user-scoped
-- policies before exposing account-based history to multiple users.
