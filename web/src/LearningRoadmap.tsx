import { useCallback, useEffect, useMemo, useState } from 'react';
import { supabase } from './supabase';

type Exercise = { title: string; problem: string; difficulty: string; input_example: string; output_example: string; constraints: string[]; concepts: string[]; accuracy?: number; completed?: boolean };
type Task = { id: string; topic: string; description: string; stage: string; priority: string; understanding: string; difficulty: string; estimated_minutes: number; prerequisites: string[]; completion_criteria: string; exercises: Exercise[]; status: 'Not Started' | 'In Progress' | 'Completed'; latest_reassessment?: { score: number; prior_score: number | null; outcome: string } };
type LearningData = { roadmap: { id: string; goal?: string; source: string } | null; tasks: Task[]; gaps: { concept: string; status: string; evidence_count: number; average_score: number | null }[] };

export default function LearningRoadmap() {
  const [data, setData] = useState<LearningData>({ roadmap: null, tasks: [], gaps: [] });
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [hints, setHints] = useState<Record<string, string>>({});
  const [questions, setQuestions] = useState<Record<string, string>>({});
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [assessments, setAssessments] = useState<Record<string, { score: number; feedback: string; outcome: string }>>({});
  const [code, setCode] = useState<Record<string, string>>({});
  const [exerciseResults, setExerciseResults] = useState<Record<string, { passed: number; total: number; accuracy: number; complete: boolean }>>({});
  const [taskSearch, setTaskSearch] = useState('');
  const [taskFilter, setTaskFilter] = useState<'All' | Task['status']>('All');
  const load = useCallback(async () => {
    const session = await supabase?.auth.getSession();
    const token = session?.data.session?.access_token;
    if (!token) { setError('Sign in to view your learning roadmap.'); setLoading(false); return; }
    try {
      const response = await fetch('/learning', { headers: { Authorization: `Bearer ${token}` } });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Could not load your learning roadmap.');
      setData(body);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load your learning roadmap.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const progress = data.tasks.length ? Math.round(data.tasks.filter(task => task.status === 'Completed').length / data.tasks.length * 100) : 0;
  const update = async (task: Task, status: Task['status']) => {
    setWorking(true); setError('');
    try {
      const token = (await supabase?.auth.getSession())?.data.session?.access_token;
      const response = await fetch(`/learning/tasks/${task.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}` }, body: JSON.stringify({ status }) });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Could not update task.'); setData(body);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not update task.'); }
    finally { setWorking(false); }
  };
  const generate = async (event: React.FormEvent) => {
    event.preventDefault(); setWorking(true); setError('');
    try {
      const token = (await supabase?.auth.getSession())?.data.session?.access_token;
      const response = await fetch('/learning', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}` }, body: JSON.stringify({ goal: goal.trim() || null }) });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Could not create a roadmap.'); setData(body);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create a roadmap.'); }
    finally { setWorking(false); }
  };
  const hint = async (task: Task, exercise: Exercise) => {
    const key = `${task.id}:${exercise.title}`; setWorking(true); setError('');
    try {
      const token = (await supabase?.auth.getSession())?.data.session?.access_token;
      const response = await fetch(`/learning/tasks/${task.id}/hint`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}` }, body: JSON.stringify({ exercise_id: exercise.title }) });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Could not get a hint.'); setHints(current => ({ ...current, [key]: body.hint }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not get a hint.'); }
    finally { setWorking(false); }
  };
  const reassess = async (task: Task, submit = false) => {
    setWorking(true); setError('');
    try {
      const token = (await supabase?.auth.getSession())?.data.session?.access_token;
      const response = await fetch(`/learning/tasks/${task.id}/reassess`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}` }, body: JSON.stringify(submit ? { question: questions[task.id], answer: answers[task.id] } : {}) });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Could not assess this topic.');
      if (submit) setAssessments(current => ({ ...current, [task.id]: body })); else setQuestions(current => ({ ...current, [task.id]: body.question }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not assess this topic.'); }
    finally { setWorking(false); }
  };
  const submitExercise = async (task: Task, exercise: Exercise) => {
    const key = `${task.id}:${exercise.title}`; setWorking(true); setError('');
    try {
      const token = (await supabase?.auth.getSession())?.data.session?.access_token;
      const response = await fetch(`/learning/tasks/${task.id}/exercises/submit`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}` }, body: JSON.stringify({ exercise_id: exercise.title, language_id: 71, source_code: code[key] || '' }) });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Could not run exercise tests.'); setExerciseResults(current => ({ ...current, [key]: body })); if (body.complete) await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not run exercise tests.'); }
    finally { setWorking(false); }
  };
  const next = useMemo(() => data.tasks.find(task => task.status !== 'Completed'), [data.tasks]);
  const visibleTasks = useMemo(() => {
    const query = taskSearch.trim().toLocaleLowerCase();
    return data.tasks.map((task, index) => ({ task, index })).filter(({ task }) =>
      (taskFilter === 'All' || task.status === taskFilter) &&
      (!query || `${task.topic} ${task.description} ${task.stage} ${task.prerequisites.join(' ')}`.toLocaleLowerCase().includes(query))
    );
  }, [data.tasks, taskFilter, taskSearch]);
  if (loading) return <section className="page active"><div className="empty-card">Loading your learning roadmap…</div></section>;
  return <section className="page active">
    <div className="page-heading"><div className="eyebrow">PERSONAL LEARNING</div><h1>Learning roadmap</h1><p>Build on your interview feedback with a focused, step by step plan.</p></div>
    {error && <div className="empty-card" role="alert">{error}</div>}
    {!data.roadmap ? <div className="panel"><h3>Start with a learning goal</h3><p>{data.gaps.length ? `We found ${data.gaps.length} specific concepts in your interview reports.` : 'No specific knowledge gaps are available yet. Choose a goal for a starter roadmap, or complete an interview first.'}</p>{data.gaps.length > 0 && <div className="insight-badges">{data.gaps.slice(0, 8).map(gap => <span key={gap.concept}>{gap.concept} · {gap.status}</span>)}</div>}<form className="answer-form" onSubmit={generate}><label className="code-label" htmlFor="learning-goal">Optional learning goal</label><input id="learning-goal" className="stdin-editor" maxLength={200} value={goal} onChange={event => setGoal(event.target.value)} placeholder="e.g. Prepare for intermediate Python interviews"/><button className="primary-btn" disabled={working}>{working ? 'Building roadmap…' : data.gaps.length ? 'Build my roadmap' : 'Create starter roadmap'}</button></form></div> : <>
      <div className="stat-grid"><div className="stat-card"><div className="stat-top">Overall progress</div><div className="stat-value">{progress}<small>%</small></div><div className="skill-track"><i style={{ width: `${progress}%` }}/></div></div><div className="stat-card"><div className="stat-top">Topics</div><div className="stat-value">{data.tasks.length}</div></div><div className="stat-card"><div className="stat-top">Completed</div><div className="stat-value">{data.tasks.filter(t => t.status === 'Completed').length}</div></div></div>
      <div className="panel"><h3>Next recommended activity</h3><p>{next ? `${next.topic}: ${next.description}` : 'Roadmap complete. Revisit interview practice to find your next learning priorities.'}</p>{next && <button className="primary-btn" onClick={() => { document.getElementById(`task-${next.id}`)?.scrollIntoView({ behavior: 'smooth' }); void update(next, 'In Progress'); }}>Continue · {next.estimated_minutes} min</button>}</div>
      <div className="panel"><h3>Focus on a new learning goal</h3><p>Enter a goal such as “learn machine learning” to add a sequenced curriculum while keeping your completed progress.</p><form className="answer-form" onSubmit={generate}><label className="code-label" htmlFor="learning-goal">Learning goal</label><input id="learning-goal" className="stdin-editor" maxLength={200} value={goal} onChange={event => setGoal(event.target.value)} placeholder="e.g. Learn machine learning from the foundations"/><button className="primary-btn" disabled={working || !goal.trim()}>{working ? 'Building roadmap…' : 'Build goal roadmap'}</button></form></div>
      <div className="section-head"><h2>My learning roadmap</h2><span>{data.roadmap.source === 'interview' ? 'Based on interview history' : 'Based on your selected goal'}</span></div>
      <div className="roadmap-filters"><label className="sr-only" htmlFor="roadmap-search">Search roadmap topics</label><input id="roadmap-search" className="stdin-editor" type="search" value={taskSearch} onChange={event => setTaskSearch(event.target.value)} placeholder="Search topics, stages, or prerequisites"/><label className="sr-only" htmlFor="roadmap-status">Filter by status</label><select id="roadmap-status" className="stdin-editor" value={taskFilter} onChange={event => setTaskFilter(event.target.value as typeof taskFilter)}><option value="All">All statuses</option><option value="Not Started">Not started</option><option value="In Progress">In progress</option><option value="Completed">Completed</option></select><span>{visibleTasks.length} of {data.tasks.length} topics</span></div>
      <div className="history-list">{visibleTasks.map(({ task, index }) => <article className="panel" id={`task-${task.id}`} key={task.id}><div className="eyebrow">STAGE {index + 1} · {task.stage}</div><div className="activity-heading"><div><h3>{task.topic}</h3><p>{task.description}</p></div><span className="filter-chip">{task.status}</span></div><div className="insight-badges"><span>{task.priority} priority</span><span>{task.difficulty}</span><span>~{task.estimated_minutes} min</span><span>{task.understanding}</span></div>{task.latest_reassessment && <p>Assessment: {task.latest_reassessment.prior_score == null ? 'No prior score' : `${task.latest_reassessment.prior_score}/10`} → {task.latest_reassessment.score}/10 · {task.latest_reassessment.outcome}</p>}{task.prerequisites.length > 0 && <p>Prerequisites: {task.prerequisites.join(', ')}</p>}<p><b>Completion criteria:</b> {task.completion_criteria}</p>{task.exercises?.length > 0 && <><h3>Practice exercises</h3>{task.exercises.map(exercise => { const key = `${task.id}:${exercise.title}`; return <div className="feedback-card" key={exercise.title}><h4>{exercise.title} · {exercise.difficulty}{exercise.completed ? ' · Completed' : ''}</h4><p>{exercise.problem}</p><p><b>Sample input:</b> <code>{exercise.input_example}</code> &nbsp; <b>Output:</b> <code>{exercise.output_example}</code></p>{exercise.constraints.length > 0 && <small>Constraints: {exercise.constraints.join(' · ')}</small>}<label className="code-label" htmlFor={`code-${key}`}>Python solution</label><textarea id={`code-${key}`} className="code-editor" value={code[key] || ''} onChange={event => setCode(current => ({ ...current, [key]: event.target.value }))} spellCheck={false} placeholder={'# Write your solution\n'} /><div className="result-actions"><button className="secondary-btn small-btn" disabled={working} onClick={() => void hint(task, exercise)}>Request hint</button><button className="primary-btn" disabled={working || !code[key]?.trim()} onClick={() => void submitExercise(task, exercise)}>{working ? 'Running tests…' : 'Run private tests'}</button></div>{exerciseResults[key] && <p role="status">{exerciseResults[key].passed}/{exerciseResults[key].total} tests passed · {exerciseResults[key].accuracy}%{exerciseResults[key].complete ? ' · Exercise completed' : ''}</p>}{hints[key] && <p role="status"><b>Hint:</b> {hints[key]}</p>}</div>; })}</>}
      <div className="result-actions">{task.status !== 'In Progress' && task.status !== 'Completed' && <button className="secondary-btn" disabled={working} onClick={() => void update(task, 'In Progress')}>Start topic</button>}{task.status !== 'Completed' && <button className="primary-btn" disabled={working} onClick={() => void update(task, 'Completed')}>Mark topic complete</button>}{task.status === 'Completed' && <button className="secondary-btn" disabled={working} onClick={() => void reassess(task)}>Start AI reassessment</button>}</div>{questions[task.id] && <div className="feedback-card"><h4>Targeted assessment</h4><p>{questions[task.id]}</p><textarea className="stdin-editor" aria-label="Your reassessment answer" value={answers[task.id] || ''} onChange={event => setAnswers(current => ({ ...current, [task.id]: event.target.value }))} placeholder="Explain your answer…"/><button className="primary-btn" disabled={working || !answers[task.id]?.trim()} onClick={() => void reassess(task, true)}>Submit assessment</button></div>}{assessments[task.id] && <div className="feedback-card" role="status"><b>{assessments[task.id].outcome} · {assessments[task.id].score}/10</b><p>{assessments[task.id].feedback}</p></div>}</article>)}</div>
      {!visibleTasks.length && <div className="panel" role="status">No topics match these filters. Try another search or status.</div>}
      <div className="panel"><h3>Performance improvement</h3><p>Topic outcomes are updated by targeted AI reassessment and saved interview evidence.</p>{data.gaps.length ? data.gaps.map(gap => <div className="skill-row" key={gap.concept}><span>{gap.concept} · {gap.status}</span><div className="skill-track"><i style={{ width: `${gap.average_score == null ? 0 : gap.average_score * 10}%` }}/></div><b>{gap.average_score == null ? '—' : `${gap.average_score}/10`}</b></div>) : <p>Complete more interviews to build a performance comparison.</p>}</div>
    </>}
  </section>;
}
