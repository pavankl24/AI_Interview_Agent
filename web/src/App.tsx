import { useEffect, useMemo, useState, type FormEvent } from 'react';
import logo from '../cogniv-mark.png';
import lightLogo from '../cogniv-light-logo.png';

type Page = 'home' | 'setup' | 'interview' | 'results' | 'history' | 'profile';
type Topic = { name: string; icon: string; desc: string };
type Report = { interview_type?: string; overall_score?: number; knowledge_score?: number; problem_solving_score?: number | null; strengths?: string[]; weaknesses?: string[]; areas_to_improve?: string[]; overall_feedback?: string };
type Session = { topic: string; score: number; date: string; duration: string; report?: Report };
type Message = { role: 'coach' | 'candidate'; text: string };
type Mode = 'Balanced' | 'Technical conversation' | 'Coding & problem solving';

const topics: Topic[] = [
  { name: 'Python', icon: '⌘', desc: 'Core concepts, data types & coding' },
  { name: 'SQL', icon: '▤', desc: 'Queries, joins & databases' },
  { name: 'AI / ML', icon: '✧', desc: 'Models, fundamentals & use cases' },
  { name: 'Full stack', icon: '⌘', desc: 'Frontend, backend & APIs' },
  { name: 'OOP', icon: '◈', desc: 'Classes, design & principles' },
  { name: 'JavaScript', icon: 'JS', desc: 'Language fundamentals & web' },
];
const seed: Session[] = [
  { topic: 'Python', score: 8.2, date: 'Oct 29', duration: '12 min' },
  { topic: 'SQL', score: 7.4, date: 'Oct 27', duration: '9 min' },
  { topic: 'Full stack', score: 6.8, date: 'Oct 24', duration: '15 min' },
];
const modes: { name: Mode; description: string; icon: string }[] = [
  { name: 'Balanced', description: 'A mix of technical discussion and practical questions.', icon: '◈' },
  { name: 'Technical conversation', description: 'Talk through concepts, tradeoffs, and decisions.', icon: '☷' },
  { name: 'Coding & problem solving', description: 'Write code, solve problems, and explain your approach.', icon: '⌘' },
];
const read = <T,>(key: string, fallback: T): T => { try { return JSON.parse(localStorage.getItem(key) || 'null') ?? fallback; } catch { return fallback; } };
const getClientId = () => { let id = localStorage.getItem('cogniv.client-id'); if (!id) { id = crypto.randomUUID(); localStorage.setItem('cogniv.client-id', id); } return id; };

function AreaChart({ sessions }: { sessions: Session[] }) {
  const data = [...sessions].slice(0, 8).reverse();
  const [point, setPoint] = useState(data.length - 1);
  useEffect(() => setPoint(data.length - 1), [sessions.length]);
  if (!data.length) return <div className="empty-card chart-empty">Complete a practice to start your score trend.</div>;
  const coords = data.map((item, index) => ({ x: data.length === 1 ? 300 : 38 + index * 524 / (data.length - 1), y: 184 - item.score * 15, item }));
  const line = coords.map(p => `${p.x},${p.y}`).join(' ');
  const area = `M ${coords[0].x},200 L ${coords.map(p => `${p.x},${p.y}`).join(' L ')} L ${coords.at(-1)!.x},200 Z`;
  const selected = coords[point] || coords.at(-1)!;
  return <div className="area-chart">
    <div className="chart-tooltip" style={{ left: `${Math.max(18, Math.min(82, selected.x / 6))}%` }} role="status"><b>{selected.item.score.toFixed(1)} <small>/ 10</small></b><span>{selected.item.topic} · {selected.item.date}</span></div>
    <svg viewBox="0 0 600 215" role="img" aria-label="Interactive interview score history area chart">
      <defs><linearGradient id="scoreFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--chart-fill)" stopOpacity=".48"/><stop offset="100%" stopColor="var(--chart-fill)" stopOpacity=".015"/></linearGradient></defs>
      {[50, 100, 150, 200].map(y => <line key={y} x1="24" x2="576" y1={y} y2={y} className="chart-gridline" />)}
      <path d={area} fill="url(#scoreFill)" />
      <polyline points={line} fill="none" stroke="var(--chart-line)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      {coords.map((p, index) => <circle key={`${p.item.date}-${index}`} cx={p.x} cy={p.y} r={point === index ? 6 : 4} className="chart-point" tabIndex={0} role="button" aria-label={`${p.item.topic}: ${p.item.score} out of 10 on ${p.item.date}`} onMouseEnter={() => setPoint(index)} onFocus={() => setPoint(index)} onClick={() => setPoint(index)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') setPoint(index); }} />)}
    </svg>
    <div className="chart-labels">{data.map((item, i) => <button key={`${item.date}-${i}`} className={point === i ? 'selected' : ''} onMouseEnter={() => setPoint(i)} onFocus={() => setPoint(i)} onClick={() => setPoint(i)}>{item.date}</button>)}</div>
  </div>;
}

export default function App() {
  const saved = read('cogniv.practice.preferences.v1', { limit: 5, level: 'Intermediate', focus: 'Balanced' as Mode });
  const [page, setPage] = useState<Page>('home');
  const [clientId] = useState(getClientId);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('cogniv.theme') === 'dark' ? 'dark' : 'light');
  const [setupStep, setSetupStep] = useState(1);
  const [topic, setTopic] = useState('Python');
  const [level, setLevel] = useState(saved.level);
  const [mode, setMode] = useState<Mode>(saved.focus);
  const [limit, setLimit] = useState(saved.limit);
  const [sessions, setSessions] = useState<Session[]>(() => read('prepwise.sessions.v1', seed));
  const [messages, setMessages] = useState<Message[]>([]);
  const [questionNo, setQuestionNo] = useState(1);
  const [working, setWorking] = useState(false);
  const [answer, setAnswer] = useState('');
  const [report, setReport] = useState<Report | null>(null);
  const [notice, setNotice] = useState('');
  const [name] = useState(() => read('prepwise.profile.v1', { name: 'Alex' }).name || 'Alex');
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#080d1a' : '#f4f1e8');
    localStorage.setItem('cogniv.theme', theme);
  }, [theme]);
  useEffect(() => { localStorage.setItem('prepwise.sessions.v1', JSON.stringify(sessions)); }, [sessions]);
  useEffect(() => {
    fetch(`/interview/history?client_id=${encodeURIComponent(clientId)}`)
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (!data?.configured || !Array.isArray(data.sessions)) return;
        const savedSessions: Session[] = data.sessions.map((item: { topic: string; overall_score: number | null; created_at: string; max_questions: number; report: Report }) => ({
          topic: item.topic,
          score: Number(item.overall_score ?? item.report?.knowledge_score ?? 0),
          date: new Intl.DateTimeFormat(undefined, { month: 'short', day: '2-digit' }).format(new Date(item.created_at)),
          duration: `${item.max_questions} questions`,
          report: item.report,
        }));
        setSessions(savedSessions);
      }).catch(() => undefined);
  }, [clientId]);
  useEffect(() => { localStorage.setItem('cogniv.practice.preferences.v1', JSON.stringify({ limit, level, focus: mode })); }, [limit, level, mode]);
  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(''), 3200); return () => clearTimeout(timer); }, [notice]);

  const average = useMemo(() => sessions.length ? (sessions.reduce((sum, item) => sum + item.score, 0) / sessions.length).toFixed(1) : '—', [sessions]);
  const navigate = (target: Page) => { setPage(target); if (target === 'setup') setSetupStep(1); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const request = async (path: string, body?: unknown) => {
    const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'The interview service returned an error.'); return data;
  };
  const startInterview = async () => {
    setWorking(true);
    try {
      const result = await request('/interview/start', { client_id: clientId, interview_type: topic, max_questions: limit, difficulty: level, interview_mode: mode });
      setQuestionNo(result.question_number || 1); setMessages([{ role: 'coach', text: result.question }]); setPage('interview');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not reach the interview service.'); }
    finally { setWorking(false); }
  };
  const submitAnswer = async (event: FormEvent) => {
    event.preventDefault(); if (!answer.trim() || working) return;
    const submitted = answer.trim(); setAnswer(''); setMessages(current => [...current, { role: 'candidate', text: submitted }]); setWorking(true);
    try {
      const result = await request('/interview/answer', { answer: submitted });
      if (result.interview_completed) {
        const finalReport = result.report as Report; setReport(finalReport);
        setSessions(current => [{ topic: finalReport.interview_type || topic, score: Number(finalReport.overall_score ?? finalReport.knowledge_score ?? 0), date: new Intl.DateTimeFormat(undefined, { month: 'short', day: '2-digit' }).format(new Date()), duration: 'Practice', report: finalReport }, ...current]);
        setPage('results');
      } else { setQuestionNo(result.question_number); setMessages(current => [...current, { role: 'coach', text: result.question }]); }
    } catch (error) { setMessages(current => current.slice(0, -1)); setAnswer(submitted); setNotice(error instanceof Error ? error.message : 'Could not reach the interview service.'); }
    finally { setWorking(false); }
  };
  const homeChart = <AreaChart sessions={sessions} />;
  const sessionCards = sessions.slice(0, 3).map((item, index) => <article className="session-card" key={`${item.date}-${item.topic}-${index}`}><div className="session-title"><span className="topic-icon">{topics.find(t => t.name === item.topic)?.icon || '✦'}</span><div><b>{item.topic} interview</b><small>{item.date} · {item.duration}</small></div></div><div className="session-score"><strong>{item.score.toFixed(1)}</strong><span>/ 10 overall score</span></div><div className="score-track"><i style={{ width: `${item.score * 10}%` }} /></div></article>);

  const setupContent = <>
    <div className="page-heading"><div className="eyebrow">PRACTICE SETUP · STEP {setupStep} OF 3</div><h1>{setupStep === 1 ? 'Choose your topic' : setupStep === 2 ? 'Set your level' : 'Choose your interview style'}</h1><p>{setupStep === 1 ? 'What would you like to work on today?' : setupStep === 2 ? 'We’ll match question difficulty to your experience.' : 'Choose how you want to practice, then set your question count.'}</p><div className="setup-stepper"><i className={setupStep >= 1 ? 'done' : ''} /><i className={setupStep >= 2 ? 'done' : ''} /><i className={setupStep >= 3 ? 'done' : ''} /></div></div>
    {setupStep === 1 && <div className="choice-grid">{topics.map(item => <button key={item.name} className={`choice-card ${topic === item.name ? 'selected' : ''}`} aria-pressed={topic === item.name} onClick={() => setTopic(item.name)}><div className="choice-icon">{item.icon}</div><b>{item.name}</b><small>{item.desc}</small></button>)}</div>}
    {setupStep === 2 && <div className="level-grid">{(['Beginner', 'Intermediate', 'Advanced'] as const).map((item, index) => <button key={item} className={`choice-card level-card ${level === item ? 'selected' : ''}`} aria-pressed={level === item} onClick={() => setLevel(item)}><span className="level-number">0{index + 1}</span><b>{item}</b><small>{['Start with fundamentals and build confidence.', 'Practice common interview questions and coding.', 'Take on deeper tradeoffs and harder problems.'][index]}</small></button>)}</div>}
    {setupStep === 3 && <><div className="mode-grid">{modes.map(item => <button key={item.name} className={`choice-card mode-card ${mode === item.name ? 'selected' : ''}`} aria-pressed={mode === item.name} onClick={() => setMode(item.name)}><div className="choice-icon">{item.icon}</div><b>{item.name}</b><small>{item.description}</small></button>)}</div><div className="choice-label">Question count</div><div className="segmented">{[3, 5, 8, 10].map(value => <button key={value} className={`segment ${limit === value ? 'selected' : ''}`} aria-pressed={limit === value} onClick={() => setLimit(value)}>{value} questions</button>)}</div></>}
    <div className="setup-footer">{setupStep > 1 ? <button className="secondary-btn" onClick={() => setSetupStep(step => step - 1)}>← Back</button> : <span className="setup-note">Your preferences are saved on this device.</span>}{setupStep < 3 ? <button className="primary-btn" onClick={() => setSetupStep(step => step + 1)}>Continue →</button> : <button className="primary-btn" onClick={startInterview} disabled={working}>{working ? 'Getting ready…' : 'Start interview →'}</button>}</div>
  </>;

  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#home" onClick={event => { event.preventDefault(); navigate('home'); }}><span className="brand-mark"><img src={theme === 'light' ? lightLogo : logo} alt="" /></span><span>COGNIV AI</span></a><div className="side-label">WORKSPACE</div><nav className="side-nav" aria-label="Main navigation"><button className={`nav-link ${page === 'home' ? 'active' : ''}`} onClick={() => navigate('home')}><span>⌂</span>Home</button><button className={`nav-link ${page === 'setup' ? 'active' : ''}`} onClick={() => navigate('setup')}><span>✦</span>Practice</button><button className={`nav-link ${page === 'history' ? 'active' : ''}`} onClick={() => navigate('history')}><span>◷</span>My progress</button></nav><div className="side-bottom"><div className="mentor-mini"><div className="mentor-icon">AI</div><div><b>Your AI coach</b><small>Ready when you are</small></div><span className="online-dot" /></div><button className={`nav-link ${page === 'profile' ? 'active' : ''}`} onClick={() => navigate('profile')}><span>⚙</span>Settings</button></div><div className="sidebar-foot">Practice with purpose.</div></aside>
    <main className="main-area"><header className="topbar"><button className="mobile-brand" onClick={() => navigate('home')}><span className="brand-mark"><img src={logo} alt="" /></span> COGNIV AI</button><div className="top-spacer" /><span className="streak"><span>✦</span> <b>{Math.min(7, sessions.length)}</b> day streak</span><button className="theme-toggle" type="button" aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} aria-pressed={theme === 'dark'} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} onClick={() => setTheme(current => current === 'light' ? 'dark' : 'light')}><span className={theme === 'light' ? 'theme-icon active' : 'theme-icon'} aria-hidden="true">☀</span><span className={theme === 'dark' ? 'theme-icon active' : 'theme-icon'} aria-hidden="true">☾</span></button><button className="avatar-button" onClick={() => navigate('profile')} aria-label="Open profile">{name[0]}</button></header>
      {notice && <div className="toast show" role="alert">{notice}</div>}
      {page === 'home' && <section className="page active"><div className="welcome-line"><div><div className="eyebrow">YOUR COACHING SPACE</div><h1>Hey, {name.split(' ')[0]} <span>✦</span></h1><p>Good practice turns into quiet confidence.</p></div><button className="link-btn" onClick={() => navigate('history')}>View progress ↗</button></div><div className="hero-card"><div className="hero-copy"><div className="eyebrow">YOUR NEXT PRACTICE <span className="eyebrow-separator">/</span> 12 MIN</div><h2>Make your next answer your strongest.</h2><p>Choose a topic, find your level, and practice the way that works for you.</p><button className="primary-btn" onClick={() => navigate('setup')}>Set up practice <span>→</span></button></div><div className="hero-art"><div className="path-visual"><span className="path-caption">YOUR CAREER PATH</span><svg viewBox="0 0 250 150" aria-hidden="true"><path className="path-line" d="M18 122 C55 121 51 79 91 86 S132 113 155 61 S202 32 231 24"/><circle cx="18" cy="122" r="7" className="path-node complete"/><circle cx="91" cy="86" r="6" className="path-node complete"/><circle cx="155" cy="61" r="7" className="path-node current"/><circle cx="231" cy="24" r="6" className="path-node future"/></svg><div className="path-label"><b>Next stop</b><span>Interview ready</span></div></div></div></div><div className="stat-grid"><div className="stat-card"><div className="stat-top">Sessions completed <span className="stat-icon">◷</span></div><div className="stat-value">{sessions.length}</div><div className="stat-note">Every session is progress</div></div><div className="stat-card"><div className="stat-top">Average score <span className="stat-icon">✧</span></div><div className="stat-value">{average}<small> {average !== '—' ? '/ 10' : ''}</small></div><div className="stat-note">Keep your momentum going</div></div><div className="stat-card"><div className="stat-top">Practice streak <span className="stat-icon">✦</span></div><div className="stat-value">{Math.min(7, sessions.length)}<small> days</small></div><div className="stat-note">Consistency builds confidence</div></div></div><div className="section-head"><h2>Recent sessions</h2><button className="link-btn" onClick={() => navigate('history')}>See all →</button></div><div className="session-list">{sessionCards}</div><div className="section-head"><h2>Your progress</h2><button className="link-btn" onClick={() => navigate('history')}>View progress →</button></div><div className="two-col"><div className="panel"><h3>Score over time</h3><p>Hover, tap, or focus a point to inspect a practice.</p>{homeChart}</div><div className="panel"><h3>Skills to grow</h3><p>Your focus areas at a glance</p>{['Communication', 'Technical knowledge', 'Problem solving'].map((item, i) => <div className="skill-row" key={item}><span>{item}</span><div className="skill-track"><i style={{ width: `${Math.max(35, Number(average === '—' ? 6.8 : average) * 10 - i * 7)}%` }} /></div><b>{Math.max(35, Number(average === '—' ? 6.8 : average) * 10 - i * 7)}%</b></div>)}</div></div></section>}
      {page === 'setup' && <section className="page active">{setupContent}</section>}
      {page === 'interview' && <section className="page active"><div className="interview-shell"><div className="interview-top"><div className="coach-avatar">AI</div><div><b>{topic} practice</b><small>{mode} · {level}</small></div><div className="interview-progress"><b>Question {questionNo} of {limit}</b><div className="progress-track"><i style={{ width: `${questionNo / limit * 100}%` }} /></div></div></div><div className="chat-box">{messages.map((message, index) => <div className={`chat-message ${message.role === 'candidate' ? 'candidate' : ''}`} key={index}><div className="chat-face">{message.role === 'candidate' ? name[0] : 'AI'}</div><div className="bubble-wrap"><small>{message.role === 'candidate' ? name : 'Interviewer'}</small><div className="bubble">{message.text}</div></div></div>)}{working && <div className="chat-message"><div className="chat-face">AI</div><div className="bubble typing"><i /><i /><i /></div></div>}</div><form className="answer-form" onSubmit={submitAnswer}><textarea value={answer} onChange={event => setAnswer(event.target.value)} placeholder="Take your time. Type your answer here…" aria-label="Your answer" required /><button className="send-btn" aria-label="Send answer" disabled={working}>↑</button></form></div></section>}
      {page === 'results' && report && <section className="page active"><div className="page-heading"><div className="eyebrow">PRACTICE COMPLETE</div><h1>Progress looks good on you.</h1><p>{report.overall_feedback}</p></div><div className="result-hero"><div className="score-ring" style={{ ['--score' as string]: `${Number(report.overall_score ?? 0) * 10}%` }}><div className="score-center"><strong>{Number(report.overall_score ?? 0).toFixed(1)}</strong><small>OUT OF 10</small></div></div><div className="result-copy"><div className="eyebrow">{topic.toUpperCase()} <span className="eyebrow-separator">/</span> {mode.toUpperCase()}</div><h2>Your practice report</h2><p>One clear next step makes all the difference.</p><div className="insight-badges"><span>Knowledge {Number(report.knowledge_score ?? 0).toFixed(1)}</span>{report.problem_solving_score != null && <span>Problem solving {Number(report.problem_solving_score).toFixed(1)}</span>}</div></div></div><div className="feedback-grid"><div className="feedback-card"><h3><span className="feedback-marker good">+</span> What went well</h3><ul>{(report.strengths || []).map(item => <li key={item}>{item}</li>)}</ul></div><div className="feedback-card improve"><h3><span className="feedback-marker grow">↗</span> Room to grow</h3><ul>{(report.areas_to_improve || report.weaknesses || []).map(item => <li key={item}>{item}</li>)}</ul></div></div><div className="result-actions"><button className="primary-btn" onClick={() => navigate('setup')}>Practice again →</button><button className="secondary-btn" onClick={() => navigate('history')}>See progress</button></div></section>}
      {page === 'history' && <section className="page active"><div className="page-heading"><div className="eyebrow">YOUR PRACTICE, OVER TIME</div><h1>Progress</h1><p>Every session adds to your confidence.</p></div><div className="stat-grid"><div className="stat-card"><div className="stat-top">Sessions completed</div><div className="stat-value">{sessions.length}</div></div><div className="stat-card"><div className="stat-top">Average score</div><div className="stat-value">{average}</div></div><div className="stat-card"><div className="stat-top">Practice topics</div><div className="stat-value">{new Set(sessions.map(item => item.topic)).size}</div></div></div><div className="section-head"><h2>Score trend</h2></div><div className="panel">{homeChart}</div><div className="section-head"><h2>Practice history</h2><button className="link-btn" onClick={() => navigate('setup')}>+ New practice</button></div><div className="filter-row">{['All', ...new Set(sessions.map(item => item.topic))].map(item => <button className={`filter-chip ${filter === item ? 'active' : ''}`} key={item} onClick={() => setFilter(item)}>{item}</button>)}</div><div className="history-list">{sessions.filter(item => filter === 'All' || item.topic === filter).map((item, index) => <div className="history-row" key={`${item.date}-${index}`}><span className="topic-icon">{topics.find(t => t.name === item.topic)?.icon}</span><div className="history-info"><b>{item.topic} interview</b><small>{item.date} · {item.duration}</small></div><div className="history-result">{item.score.toFixed(1)}<small> / 10</small></div></div>)}</div></section>}
      {page === 'profile' && <section className="page active"><div className="page-heading"><div className="eyebrow">PREFERENCES</div><h1>Your practice defaults</h1><p>Keep the next session ready for you.</p></div><div className="panel settings-summary"><h3>Interview setup</h3><div className="setting-row"><div><b>Experience level</b><small>{level}</small></div><button className="secondary-btn small-btn" onClick={() => { setPage('setup'); setSetupStep(2); }}>Change</button></div><div className="setting-row"><div><b>Interview style</b><small>{mode}</small></div><button className="secondary-btn small-btn" onClick={() => { setPage('setup'); setSetupStep(3); }}>Change</button></div><div className="setting-row"><div><b>Question count</b><small>{limit} questions</small></div><button className="secondary-btn small-btn" onClick={() => { setPage('setup'); setSetupStep(3); }}>Change</button></div></div><div className="profile-note"><span className="note-symbol">✳</span><div><b>A little practice adds up.</b><p>Your sessions and preferences stay saved on this device.</p></div></div></section>}
    </main>
    <nav className="bottom-nav" aria-label="Mobile navigation"><button className={page === 'home' ? 'active' : ''} onClick={() => navigate('home')}><span>⌂</span>Home</button><button className={page === 'setup' ? 'active' : ''} onClick={() => navigate('setup')}><span>✦</span>Practice</button><button className={page === 'history' ? 'active' : ''} onClick={() => navigate('history')}><span>◷</span>Progress</button><button className={page === 'profile' ? 'active' : ''} onClick={() => navigate('profile')}><span>⚙</span>Settings</button></nav>
  </div>;
}
