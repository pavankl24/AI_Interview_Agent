-- Supabase Auth users may read only their own saved reports.
alter table public.interview_sessions enable row level security;

drop policy if exists "Users can read their own interview sessions" on public.interview_sessions;
create policy "Users can read their own interview sessions"
  on public.interview_sessions
  for select
  to authenticated
  using (auth.uid() = client_id);

grant select on public.interview_sessions to authenticated;
