create table if not exists public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null check (char_length(filename) <= 255),
  content_type text not null check (content_type in ('application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/zip')),
  extracted_text text not null,
  profile jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists resumes_user_created_idx on public.resumes(user_id, created_at desc);
alter table public.resumes enable row level security;
drop policy if exists "Users manage own resumes" on public.resumes;
create policy "Users manage own resumes" on public.resumes for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
grant select, insert, update, delete on public.resumes to authenticated;

create table if not exists public.resume_interview_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  resume_id uuid not null references public.resumes(id) on delete cascade,
  state jsonb not null,
  status text not null default 'active' check (status in ('active','completed')),
  report jsonb,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);
create index if not exists resume_interviews_user_created_idx on public.resume_interview_sessions(user_id, created_at desc);
alter table public.resume_interview_sessions enable row level security;
drop policy if exists "Users manage own resume interviews" on public.resume_interview_sessions;
create policy "Users manage own resume interviews" on public.resume_interview_sessions for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id and exists (select 1 from public.resumes r where r.id = resume_id and r.user_id = auth.uid()));
grant select, insert, update, delete on public.resume_interview_sessions to authenticated;
