create table if not exists public.learning_roadmaps (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  goal text check (goal is null or char_length(goal) <= 200),
  source text not null check (source in ('interview', 'goal')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists learning_roadmaps_user_created_idx on public.learning_roadmaps(user_id, created_at desc);

create table if not exists public.learning_tasks (
  id uuid primary key default gen_random_uuid(),
  roadmap_id uuid not null references public.learning_roadmaps(id) on delete cascade,
  sequence integer not null check (sequence >= 0),
  topic text not null,
  description text not null,
  stage text not null check (stage in ('Foundation','Improvement','Practice','Advanced','Assessment')),
  priority text not null,
  understanding text not null,
  difficulty text not null,
  estimated_minutes integer not null check (estimated_minutes between 5 and 600),
  prerequisites jsonb not null default '[]'::jsonb,
  completion_criteria text not null,
  exercises jsonb not null default '[]'::jsonb,
  status text not null default 'Not Started' check (status in ('Not Started','In Progress','Completed')),
  started_at timestamptz,
  completed_at timestamptz,
  updated_at timestamptz not null default now(),
  unique(roadmap_id, sequence)
);
create index if not exists learning_tasks_roadmap_sequence_idx on public.learning_tasks(roadmap_id, sequence);

create table if not exists public.learning_reassessments (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.learning_tasks(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  question text not null,
  response text not null,
  score numeric(4,2) check(score between 0 and 10),
  outcome text not null check(outcome in ('Mastered','Improving','Needs Improvement')),
  prior_score numeric(4,2),
  created_at timestamptz not null default now()
);
create table if not exists public.exercise_submissions (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.learning_tasks(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  exercise_title text not null,
  language_id integer,
  source_code text not null,
  passed integer not null default 0 check(passed >= 0),
  total_tests integer not null default 0 check(total_tests >= passed),
  accuracy numeric(5,2) not null default 0 check(accuracy between 0 and 100),
  created_at timestamptz not null default now()
);

alter table public.learning_roadmaps enable row level security;
alter table public.learning_tasks enable row level security;
alter table public.learning_reassessments enable row level security;
alter table public.exercise_submissions enable row level security;
drop policy if exists "Users manage own learning roadmaps" on public.learning_roadmaps;
create policy "Users manage own learning roadmaps" on public.learning_roadmaps for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users manage own learning tasks" on public.learning_tasks;
create policy "Users manage own learning tasks" on public.learning_tasks for all to authenticated using (exists (select 1 from public.learning_roadmaps r where r.id = roadmap_id and r.user_id = auth.uid())) with check (exists (select 1 from public.learning_roadmaps r where r.id = roadmap_id and r.user_id = auth.uid()));
drop policy if exists "Users manage own learning reassessments" on public.learning_reassessments;
create policy "Users manage own learning reassessments" on public.learning_reassessments for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id and exists (select 1 from public.learning_tasks t join public.learning_roadmaps r on r.id = t.roadmap_id where t.id = task_id and r.user_id = auth.uid()));
drop policy if exists "Users manage own exercise submissions" on public.exercise_submissions;
create policy "Users manage own exercise submissions" on public.exercise_submissions for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id and exists (select 1 from public.learning_tasks t join public.learning_roadmaps r on r.id = t.roadmap_id where t.id = task_id and r.user_id = auth.uid()));
grant select, insert, update, delete on public.learning_roadmaps, public.learning_tasks, public.learning_reassessments, public.exercise_submissions to authenticated;
