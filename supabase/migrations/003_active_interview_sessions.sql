create table if not exists public.active_interview_sessions (
  client_id uuid primary key references auth.users(id) on delete cascade,
  session_id uuid not null unique,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create index if not exists active_interview_sessions_expires_idx
  on public.active_interview_sessions (expires_at);

alter table public.active_interview_sessions enable row level security;
-- Active interview state is accessed only by FastAPI with the server-only key.
