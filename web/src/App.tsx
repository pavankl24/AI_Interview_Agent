import { useEffect, useMemo, useState, type FormEvent } from 'react';
import logo from '../cogniv-mark.png';
import { supabase } from './supabase';

type Page = 'home' | 'setup' | 'interview' | 'results' | 'history' | 'profile';
type Topic = { name: string; icon: string; desc: string };
type Report = { interview_type?: string; overall_score?: number; knowledge_score?: number; problem_solving_score?: number | null; strengths?: string[]; weaknesses?: string[]; areas_to_improve?: string[]; overall_feedback?: string };
type Session = { topic: string; score: number; date: string; activityDate?: string; duration: string; report?: Report };
type Message = { role: 'coach' | 'candidate'; text: string };
type Mode = 'Balanced' | 'Technical conversation' | 'Coding & problem solving';
type CompilerLanguage = { id: number; name: string };

const starterLanguages: CompilerLanguage[] = [
  { id: 71, name: 'Python (3.8.1)' }, { id: 63, name: 'JavaScript (Node.js 12.14.0)' },
  { id: 54, name: 'C++ (GCC 9.2.0)' }, { id: 50, name: 'C (GCC 9.2.0)' },
  { id: 62, name: 'Java (OpenJDK 13.0.1)' }, { id: 74, name: 'TypeScript (3.7.4)' },
  { id: 60, name: 'Go (1.13.5)' }, { id: 73, name: 'Rust (1.40.0)' },
  { id: 51, name: 'C# (Mono 6.6.0.161)' }, { id: 72, name: 'Ruby (2.7.0)' },
  { id: 68, name: 'PHP (7.4.1)' }, { id: 78, name: 'Kotlin (1.3.70)' },
];

const topics: Topic[] = [
  { name: 'Python', icon: 'code', desc: 'Core concepts, data types & coding' },
  { name: 'SQL', icon: 'database', desc: 'Queries, joins & databases' },
  { name: 'AI / ML', icon: 'brain', desc: 'Models, fundamentals & use cases' },
  { name: 'Full stack', icon: 'layers', desc: 'Frontend, backend & APIs' },
  { name: 'OOP', icon: 'boxes', desc: 'Classes, design & principles' },
  { name: 'JavaScript', icon: 'braces', desc: 'Language fundamentals & web' },
];
const seed: Session[] = [
  { topic: 'Python', score: 8.2, date: 'Oct 29', duration: '12 min' },
  { topic: 'SQL', score: 7.4, date: 'Oct 27', duration: '9 min' },
  { topic: 'Full stack', score: 6.8, date: 'Oct 24', duration: '15 min' },
];
const modes: { name: Mode; description: string; icon: string }[] = [
  { name: 'Balanced', description: 'A mix of technical discussion and practical questions.', icon: 'compass' },
  { name: 'Technical conversation', description: 'Talk through concepts, tradeoffs, and decisions.', icon: 'messages' },
  { name: 'Coding & problem solving', description: 'Write code, solve problems, and explain your approach.', icon: 'terminal' },
];
const read = <T,>(key: string, fallback: T): T => { try { return JSON.parse(localStorage.getItem(key) || 'null') ?? fallback; } catch { return fallback; } };

async function compressProfilePhoto(file: File) {
  const image = await createImageBitmap(file);
  const side = Math.min(image.width, image.height);
  const canvas = document.createElement('canvas');
  canvas.width = 320; canvas.height = 320;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('This browser cannot process the selected image.');
  context.drawImage(image, (image.width - side) / 2, (image.height - side) / 2, side, side, 0, 0, 320, 320);
  image.close();
  return canvas.toDataURL('image/jpeg', 0.82);
}

function starterCode(language: CompilerLanguage) {
  const name = language.name.toLowerCase();
  if (name.includes('python')) return 'import sys\n\ndef solve():\n    values = sys.stdin.read().split()\n    print(values)\n\nsolve()';
  if (name.includes('javascript')) return "const input = require('fs').readFileSync(0, 'utf8').trim();\nconsole.log(input);";
  if (name.includes('typescript')) return "const input: string = '';\nconsole.log(input);";
  if (name.includes('c++')) return '#include <iostream>\nusing namespace std;\n\nint main() {\n  cout << "Ready" << endl;\n  return 0;\n}';
  if (/\bc \(/.test(name) || name.startsWith('c (')) return '#include <stdio.h>\n\nint main(void) {\n  printf("Ready\\n");\n  return 0;\n}';
  if (name.includes('java')) return 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Ready");\n  }\n}';
  if (name.includes('go')) return 'package main\n\nimport "fmt"\n\nfunc main() {\n  fmt.Println("Ready")\n}';
  if (name.includes('rust')) return 'fn main() {\n    println!("Ready");\n}';
  if (name.includes('c#') || name.includes('csharp')) return 'using System;\n\nclass Program {\n  static void Main() {\n    Console.WriteLine("Ready");\n  }\n}';
  if (name.includes('ruby')) return 'input = STDIN.read.strip\nputs input';
  if (name.includes('php')) return '<?php\n$input = trim(stream_get_contents(STDIN));\necho $input . PHP_EOL;';
  if (name.includes('kotlin')) return 'fun main() {\n    println("Ready")\n}';
  return '';
}

function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function practiceStreak(sessions: Session[]) {
  const activeDates = new Set(sessions.map(session => session.activityDate).filter((date): date is string => Boolean(date)));
  const today = new Date();
  let cursor = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  if (!activeDates.has(dateKey(cursor))) cursor.setDate(cursor.getDate() - 1);
  let count = 0;
  while (activeDates.has(dateKey(cursor))) { count += 1; cursor.setDate(cursor.getDate() - 1); }
  return count;
}

function ActivityHeatmap({ sessions }: { sessions: Session[] }) {
  const [hoveredDay, setHoveredDay] = useState<{ description: string; x: number; y: number } | null>(null);
  const counts = new Map<string, number>();
  sessions.forEach(session => { if (session.activityDate) counts.set(session.activityDate, (counts.get(session.activityDate) || 0) + 1); });
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  start.setDate(start.getDate() - start.getDay() - 52 * 7);
  const days = Array.from({ length: 53 * 7 }, (_, index) => {
    const date = new Date(start); date.setDate(start.getDate() + index);
    const key = dateKey(date);
    return { key, date, count: counts.get(key) || 0 };
  }).filter(day => day.date <= today);
  const weeks: typeof days[] = [];
  days.forEach((day, index) => { const week = Math.floor(index / 7); if (!weeks[week]) weeks[week] = []; weeks[week].push(day); });
  const monthLabels = weeks.map(week => week[0]?.date.getDate() <= 7 ? week[0]?.date.toLocaleString(undefined, { month: 'short' }) : '');
  const activeDays = [...counts.keys()].filter(key => key >= dateKey(start) && key <= dateKey(today)).length;
  return <div className="activity-heatmap-wrap overflow-x-auto pb-1">
    <div className="activity-months mb-1 ml-7 grid grid-cols-[repeat(53,12px)] gap-x-[3px] text-[10px] leading-4 text-stone-400" aria-hidden="true">{monthLabels.map((label, index) => <span key={index}>{label}</span>)}</div>
    <div className="activity-chart-row flex gap-[7px]"><div className="activity-weekdays flex h-[102px] w-[21px] shrink-0 flex-col justify-around text-[9px] leading-none text-stone-400" aria-hidden="true"><span>Mon</span><span>Wed</span><span>Fri</span></div><div className="activity-grid flex min-w-max gap-[3px]" role="img" aria-label={`${activeDays} active practice days in the last year`}>
      {weeks.map((week, weekIndex) => <div className="activity-week grid grid-rows-[repeat(7,12px)] gap-[3px]" key={weekIndex}>{Array.from({ length: 7 }, (_, dayIndex) => {
        const day = week.find(item => item.date.getDay() === dayIndex);
        if (!day) return <i key={dayIndex} className="activity-cell invisible block size-[12px] rounded-[3px] border border-white/10" />;
        const level = day.count === 0 ? 0 : day.count === 1 ? 1 : day.count === 2 ? 2 : 3;
        const description = `${day.count} ${day.count === 1 ? 'practice' : 'practices'} on ${day.date.toLocaleDateString()}`;
        return <i key={dayIndex} className={`activity-cell level-${level} block size-[12px] cursor-help rounded-[3px] border border-white/10 transition-opacity hover:z-10 hover:scale-125 hover:outline hover:outline-1 ${['bg-white/5', 'bg-blue-400/35', 'bg-blue-300/65', 'bg-blue-300'][level]}`} aria-label={description} onMouseEnter={event => setHoveredDay({ description, x: event.clientX, y: event.clientY })} onMouseMove={event => setHoveredDay({ description, x: event.clientX, y: event.clientY })} onMouseLeave={() => setHoveredDay(null)} style={{ display: 'block', width: 12, height: 12, flex: 'none', opacity: day.count ? Math.min(1, 0.28 + day.count * 0.16) : undefined }} />;
      })}</div>)}
    </div></div>
    <div className="activity-legend mt-3 flex items-center justify-between gap-3 text-[10px] text-stone-400"><span>{activeDays} practice days</span><div className="flex items-center gap-1"><span>Less</span>{[0, 1, 2, 3].map(level => <i className={`activity-cell level-${level} block size-[9px] rounded-[2px] border border-white/10 ${['bg-white/5', 'bg-blue-400/35', 'bg-blue-300/65', 'bg-blue-300'][level]}`} key={level} />)}<span>More</span></div></div>
    {hoveredDay && <div className="heatmap-cursor-tip" role="status" style={{ left: Math.min(hoveredDay.x + 12, window.innerWidth - 230), top: hoveredDay.y + 18 }}>{hoveredDay.description}</div>}
  </div>;
}

const dailyQuotes = [
  '“For the things we have to learn before we can do them, we learn by doing them.” — Aristotle, Nicomachean Ethics, II.1',
  '“We become just by doing just acts.” — Aristotle, Nicomachean Ethics, II.1',
  '“We become temperate by doing temperate acts.” — Aristotle, Nicomachean Ethics, II.1',
  '“We become brave by doing brave acts.” — Aristotle, Nicomachean Ethics, II.1',
];

function dailyQuote() {
  const now = new Date();
  const day = Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000);
  return dailyQuotes[((day % dailyQuotes.length) + dailyQuotes.length) % dailyQuotes.length];
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true as const };
  const shapes: Record<string, React.ReactNode> = {
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v12h14V9M9 21v-7h6v7"/></>,
    play: <><circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/></>,
    chart: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 6-7"/></>,
    settings: <><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="m19.4 15 .1.1 1.1.9-1.5 2.6-1.4-.5a8 8 0 0 1-1.6.9l-.3 1.5h-3l-.3-1.5a8 8 0 0 1-1.6-.9l-1.4.5L8 16l1.1-.9a8 8 0 0 1 0-1.9L8 12.3l1.5-2.6 1.4.5a8 8 0 0 1 1.6-.9l.3-1.5h3l.3 1.5a8 8 0 0 1 1.6.9l1.4-.5 1.5 2.6-1.1.9a8 8 0 0 1-.1 1.8Z"/></>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>,
    moon: <path d="M20.8 14.2A8.5 8.5 0 0 1 9.8 3.2 8.5 8.5 0 1 0 20.8 14.2Z"/>,
    code: <><path d="m8 8-4 4 4 4m8-8 4 4-4 4m-2-11-4 14"/></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></>,
    brain: <><path d="M12 5a3 3 0 0 0-5.8-1A3.5 3.5 0 0 0 4 10a3.5 3.5 0 0 0 1 6.5A3.5 3.5 0 0 0 12 19zM12 5a3 3 0 0 1 5.8-1A3.5 3.5 0 0 1 20 10a3.5 3.5 0 0 1-1 6.5A3.5 3.5 0 0 1 12 19zM8 8h.01M16 8h.01M8 14h.01M16 14h.01M12 5v14"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    boxes: <><rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/></>,
    braces: <><path d="M8 4H6a2 2 0 0 0-2 2v3a2 2 0 0 1-2 3 2 2 0 0 1 2 3v3a2 2 0 0 0 2 2h2m8-16h2a2 2 0 0 1 2 2v3a2 2 0 0 0 2 3 2 2 0 0 0-2 3v3a2 2 0 0 1-2 2h-2"/></>,
    compass: <><circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/></>,
    messages: <><path d="M21 11.5a7.5 7.5 0 0 1-7.5 7.5 8 8 0 0 1-3.4-.8L3 20l1.8-5.1a7.3 7.3 0 0 1-.8-3.4A7.5 7.5 0 0 1 11.5 4H13"/><path d="M16 3v6m-3-3h6"/></>,
    terminal: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3m6 0h4"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5zM4 16a2 2 0 0 1 2-2h14"/><path d="M8 7h8"/></>,
  };
  return <svg {...common}>{shapes[name] || shapes.book}</svg>;
}

function AreaChart({ sessions }: { sessions: Session[] }) {
  const data = [...sessions].slice(0, 8).reverse();
  const [point, setPoint] = useState(data.length - 1);
  useEffect(() => setPoint(data.length - 1), [sessions.length]);
  if (!data.length) return <div className="empty-card chart-empty">Complete a practice to start your score trend.</div>;
  const coords = data.map((item, index) => ({ x: data.length === 1 ? 300 : 38 + index * 524 / (data.length - 1), y: 184 - item.score * 15, item }));
  const line = coords.map(p => `${p.x},${p.y}`).join(' ');
  const selected = coords[point] || coords.at(-1)!;
  return <div className="area-chart">
    <div className="chart-tooltip border-white/10 bg-[#181719]/90 text-paper shadow-xl backdrop-blur-lg   " style={{ left: `${Math.max(18, Math.min(82, selected.x / 6))}%` }} role="status"><b>{selected.item.score.toFixed(1)} <small>/ 10</small></b><span>{selected.item.topic} · {selected.item.date}</span></div>
    <svg viewBox="0 0 600 215" role="img" aria-label="Interactive interview score history area chart">
      {[50, 100, 150, 200].map(y => <line key={y} x1="24" x2="576" y1={y} y2={y} className="chart-gridline" />)}
      <polyline points={line} fill="none" stroke="var(--chart-line)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      {coords.map((p, index) => <circle key={`${p.item.date}-${index}`} cx={p.x} cy={p.y} r={point === index ? 6 : 4} className="chart-point" tabIndex={0} role="button" aria-label={`${p.item.topic}: ${p.item.score} out of 10 on ${p.item.date}`} onMouseEnter={() => setPoint(index)} onFocus={() => setPoint(index)} onClick={() => setPoint(index)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') setPoint(index); }} />)}
    </svg>
    <div className="chart-labels">{data.map((item, i) => <button key={`${item.date}-${i}`} className={point === i ? 'selected' : ''} onMouseEnter={() => setPoint(i)} onFocus={() => setPoint(i)} onClick={() => setPoint(i)}>{item.date}</button>)}</div>
  </div>;
}

export default function App() {
  const saved = read('cogniv.practice.preferences.v1', { limit: 5, level: 'Intermediate', focus: 'Balanced' as Mode });
  const [page, setPage] = useState<Page>(() => {
    const route = window.location.hash.slice(1) as Page;
    return ['home', 'setup', 'interview', 'results', 'history', 'profile'].includes(route) ? route : 'home';
  });
  const [authReady, setAuthReady] = useState(!supabase);
  const [user, setUser] = useState<{ id: string; email?: string; user_metadata?: { full_name?: string; name?: string; avatar_url?: string; picture?: string } } | null>(null);
  const [authError, setAuthError] = useState('');
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
  const [compilerLanguages, setCompilerLanguages] = useState<CompilerLanguage[]>(starterLanguages);
  const [compilerLanguage, setCompilerLanguage] = useState(71);
  const [sourceCode, setSourceCode] = useState(starterCode(starterLanguages[0]));
  const [stdin, setStdin] = useState('');
  const [compilerOutput, setCompilerOutput] = useState('Run your code to see output here.');
  const [compilerStatus, setCompilerStatus] = useState('Ready');
  const [compilerBusy, setCompilerBusy] = useState(false);
  const [profilePhoto, setProfilePhoto] = useState<string>('');
  const [profilePhotoOwner, setProfilePhotoOwner] = useState('');
  const name = user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email?.split('@')[0] || 'Alex';
  const accountPhoto = user && profilePhotoOwner === user.id ? profilePhoto : '';
  const avatarSource = accountPhoto || user?.user_metadata?.avatar_url || user?.user_metadata?.picture || '';
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    document.documentElement.dataset.theme = 'dark';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#111112');
    localStorage.removeItem('cogniv.theme');
  }, []);
  useEffect(() => {
    if (!window.location.hash) window.history.replaceState({ page: 'home' }, '', '#home');
    const onPopState = () => {
      const route = window.location.hash.slice(1) as Page;
      if (['home', 'setup', 'interview', 'results', 'history', 'profile'].includes(route)) {
        setPage(route);
        if (route === 'setup') setSetupStep(1);
        window.scrollTo({ top: 0 });
      }
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);
  useEffect(() => { localStorage.setItem('prepwise.sessions.v1', JSON.stringify(sessions)); }, [sessions]);
  useEffect(() => {
    setProfilePhotoOwner(user?.id || '');
    setProfilePhoto(user ? read(`cogniv.profile.photo.v1.${user.id}`, '') : '');
  }, [user?.id]);
  useEffect(() => {
    if (!user || profilePhotoOwner !== user.id) return;
    const key = `cogniv.profile.photo.v1.${user.id}`;
    if (profilePhoto) localStorage.setItem(key, JSON.stringify(profilePhoto));
    else localStorage.removeItem(key);
  }, [profilePhoto, profilePhotoOwner, user?.id]);
  useEffect(() => {
    if (!supabase) return;
    let alive = true;
    supabase.auth.getSession().then(({ data }) => { if (alive) { setUser(data.session?.user || null); setAuthReady(true); } });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => { setUser(session?.user || null); setAuthReady(true); });
    return () => { alive = false; subscription.unsubscribe(); };
  }, []);
  useEffect(() => {
    if (!user || !supabase) { setSessions([]); return; }
    const authClient = supabase;
    void (async () => {
      const { data: sessionData } = await authClient.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) return;
      const response = await fetch('/interview/history', { headers: { Authorization: `Bearer ${token}` } });
      const historyData = response.ok ? await response.json() : null;
        if (!historyData?.configured || !Array.isArray(historyData.sessions)) return;
        const savedSessions: Session[] = historyData.sessions.map((item: { topic: string; overall_score: number | null; created_at: string; max_questions: number; report: Report }) => ({
          topic: item.topic,
          score: Number(item.overall_score ?? item.report?.knowledge_score ?? 0),
          date: new Intl.DateTimeFormat(undefined, { month: 'short', day: '2-digit' }).format(new Date(item.created_at)),
          activityDate: dateKey(new Date(item.created_at)),
          duration: `${item.max_questions} questions`,
          report: item.report,
        }));
        setSessions(savedSessions);
    })().catch(() => undefined);
  }, [user]);
  useEffect(() => {
    if (!user || !supabase) return;
    void (async () => {
      try {
        const { data } = await supabase.auth.getSession();
        const response = await fetch('/compiler/languages', { headers: { Authorization: `Bearer ${data.session?.access_token || ''}` } });
        if (!response.ok) return;
        const languages: CompilerLanguage[] = await response.json();
        if (languages.length) {
          setCompilerLanguages(languages);
          if (!languages.some(language => language.id === compilerLanguage)) {
            const python = languages.find(language => language.name.toLowerCase().includes('python'));
            if (python) setCompilerLanguage(python.id);
          }
        }
      } catch { /* Keep the built-in language list available if the compiler is offline. */ }
    })();
  }, [user]);
  useEffect(() => { localStorage.setItem('cogniv.practice.preferences.v1', JSON.stringify({ limit, level, focus: mode })); }, [limit, level, mode]);
  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(''), 3200); return () => clearTimeout(timer); }, [notice]);

  const average = useMemo(() => sessions.length ? (sessions.reduce((sum, item) => sum + item.score, 0) / sessions.length).toFixed(1) : '—', [sessions]);
  const streak = useMemo(() => practiceStreak(sessions), [sessions]);
  const routeTo = (target: Page) => {
    window.history.pushState({ page: target }, '', `#${target}`);
    setPage(target);
  };
  const navigate = (target: Page) => {
    if (page === 'interview' && target !== 'interview') {
      setNotice('Submit your answer or end the interview before switching pages.');
      return;
    }
    routeTo(target); if (target === 'setup') setSetupStep(1); window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const request = async (path: string, body?: unknown) => {
    const { data: sessionData } = await supabase!.auth.getSession();
    const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${sessionData.session?.access_token || ''}` }, body: body ? JSON.stringify(body) : undefined });
    const responseText = await response.text();
    let responseData: any;
    try { responseData = JSON.parse(responseText); }
    catch { throw new Error(response.ok ? 'The interview service returned an unreadable response.' : `Interview service error (${response.status}). Check the FastAPI terminal for details.`); }
    if (!response.ok) throw new Error(responseData.detail || `Interview service error (${response.status}).`);
    return responseData;
  };
  const runCode = async () => {
    if (compilerBusy || !sourceCode.trim()) return;
    setCompilerBusy(true); setCompilerStatus('Running'); setCompilerOutput('');
    try {
      const result = await request('/compiler/execute', { language_id: compilerLanguage, source_code: sourceCode, stdin });
      const output = result.compile_output || result.stderr || result.stdout || result.message || 'Program finished with no output.';
      setCompilerOutput(output.trimEnd());
      setCompilerStatus(result.status || 'Finished');
    } catch (error) {
      setCompilerOutput(error instanceof Error ? error.message : 'Could not run the code.');
      setCompilerStatus('Unavailable');
    } finally { setCompilerBusy(false); }
  };
  const uploadProfilePhoto = async (file?: File) => {
    if (!file) return;
    if (!user) { setNotice('Sign in to save a profile photo to your account.'); return; }
    if (!file.type.startsWith('image/')) { setNotice('Choose an image file for your profile photo.'); return; }
    try { setProfilePhotoOwner(user.id); setProfilePhoto(await compressProfilePhoto(file)); }
    catch (error) { setNotice(error instanceof Error ? error.message : 'Could not load that image.'); }
  };
  const handleCodeKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Tab') {
      event.preventDefault();
      const editor = event.currentTarget;
      const start = editor.selectionStart; const end = editor.selectionEnd;
      editor.setRangeText('  ', start, end, 'end'); setSourceCode(editor.value); return;
    }
    if (event.key === 'Enter') {
      const editor = event.currentTarget; const start = editor.selectionStart;
      const lineStart = sourceCode.lastIndexOf('\n', start - 1) + 1;
      const line = sourceCode.slice(lineStart, start);
      const currentIndent = line.match(/^\s*/)?.[0] || '';
      const isClause = /^(else|elif|except|finally)\b/.test(line.trimStart());
      const indentation = isClause ? currentIndent.slice(0, Math.max(0, currentIndent.length - 2)) : currentIndent;
      const extra = /(?:[\[{(]|:\s*)$/.test(line.trimEnd()) ? '  ' : '';
      event.preventDefault();
      editor.setRangeText(`\n${indentation}${extra}`, start, editor.selectionEnd, 'end');
      setSourceCode(editor.value);
      return;
    }
    if (['}', ']', ')'].includes(event.key)) {
      const editor = event.currentTarget; const start = editor.selectionStart;
      const lineStart = sourceCode.lastIndexOf('\n', start - 1) + 1;
      const lineEndAt = sourceCode.indexOf('\n', start);
      const lineEnd = lineEndAt < 0 ? sourceCode.length : lineEndAt;
      const before = sourceCode.slice(lineStart, start);
      const after = sourceCode.slice(start, lineEnd);
      if (/^\s*$/.test(before) && /^\s*$/.test(after) && before.length >= 2) {
        event.preventDefault();
        editor.setRangeText(`${before.slice(0, -2)}${event.key}`, lineStart, lineEnd, 'end');
        setSourceCode(editor.value);
      }
    }
  };
  const startInterview = async () => {
    setWorking(true);
    try {
      const result = await request('/interview/start', { interview_type: topic, max_questions: limit, difficulty: level, interview_mode: mode });
      setQuestionNo(result.question_number || 1); setMessages([{ role: 'coach', text: result.question }]); routeTo('interview');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not reach the interview service.'); }
    finally { setWorking(false); }
  };
  const submitResponse = async (text: string) => {
    if (!text.trim() || working) return;
    const submitted = text.trim(); setAnswer(''); setMessages(current => [...current, { role: 'candidate', text: submitted }]); setWorking(true);
    try {
      const result = await request('/interview/answer', { answer: submitted });
      if (result.interview_completed) {
        const finalReport = result.report as Report; setReport(finalReport);
        setSessions(current => [{ topic: finalReport.interview_type || topic, score: Number(finalReport.overall_score ?? finalReport.knowledge_score ?? 0), date: new Intl.DateTimeFormat(undefined, { month: 'short', day: '2-digit' }).format(new Date()), activityDate: dateKey(new Date()), duration: 'Practice', report: finalReport }, ...current]);
        if (result.history_persisted === false) setNotice('Your report is ready, but Supabase could not save it. Check SUPABASE_URL in .env.');
        routeTo('results');
      } else { setQuestionNo(result.question_number); setMessages(current => [...current, { role: 'coach', text: result.question }]); }
    } catch (error) { setMessages(current => current.slice(0, -1)); setAnswer(submitted); setNotice(error instanceof Error ? error.message : 'Could not reach the interview service.'); }
    finally { setWorking(false); }
  };
  const submitAnswer = (event: FormEvent) => { event.preventDefault(); void submitResponse(answer); };
  const submitCodeAnswer = () => { void submitResponse(sourceCode); };
  const endInterview = async () => {
    if (working) return;
    setWorking(true);
    try {
      const result = await request('/interview/finish');
      const finalReport = (result.report || result) as Report;
      setReport(finalReport);
      setSessions(current => [{ topic: finalReport.interview_type || topic, score: Number(finalReport.overall_score ?? finalReport.knowledge_score ?? 0), date: new Intl.DateTimeFormat(undefined, { month: 'short', day: '2-digit' }).format(new Date()), activityDate: dateKey(new Date()), duration: 'Practice', report: finalReport }, ...current]);
      if (result.history_persisted === false) setNotice('Your report is ready, but Supabase could not save it.');
      routeTo('results');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not end the interview.'); }
    finally { setWorking(false); }
  };
  const homeChart = <AreaChart sessions={sessions} />;
  const sessionCards = sessions.slice(0, 3).map((item, index) => <article className="session-card rounded-xl border-white/10 bg-white/5 backdrop-blur-md transition-colors hover:border-wine-400/50 hover:bg-white/10  " key={`${item.date}-${item.topic}-${index}`}><div className="session-title"><span className="topic-icon bg-blue-400/15 text-blue-300"><Icon name={topics.find(t => t.name === item.topic)?.icon || 'book'} /></span><div><b>{item.topic} interview</b><small>{item.date} · {item.duration}</small></div></div><div className="session-score"><strong>{item.score.toFixed(1)}</strong><span>/ 10 overall score</span></div><div className="score-track"><i style={{ width: `${item.score * 10}%` }} /></div></article>);

  const setupContent = <>
    <div className="page-heading"><div className="eyebrow">PRACTICE SETUP · STEP {setupStep} OF 3</div><h1>{setupStep === 1 ? 'Choose your topic' : setupStep === 2 ? 'Set your level' : 'Choose your interview style'}</h1><p>{setupStep === 1 ? 'What would you like to work on today?' : setupStep === 2 ? 'We’ll match question difficulty to your experience.' : 'Choose how you want to practice, then set your question count.'}</p><div className="setup-stepper"><i className={setupStep >= 1 ? 'done' : ''} /><i className={setupStep >= 2 ? 'done' : ''} /><i className={setupStep >= 3 ? 'done' : ''} /></div></div>
    {setupStep === 1 && <div className="choice-grid">{topics.map(item => <button key={item.name} className={`choice-card ${topic === item.name ? 'selected' : ''} rounded-xl border-white/10 bg-white/5 text-paper backdrop-blur-md hover:border-blue-300/40 hover:bg-white/10   `} aria-pressed={topic === item.name} onClick={() => setTopic(item.name)}><div className="choice-icon"><Icon name={item.icon} size={22} /></div><b>{item.name}</b><small>{item.desc}</small></button>)}</div>}
    {setupStep === 2 && <div className="level-grid">{(['Beginner', 'Intermediate', 'Advanced'] as const).map((item, index) => <button key={item} className={`choice-card level-card ${level === item ? 'selected' : ''} rounded-xl border-white/10 bg-white/5 text-paper backdrop-blur-md hover:border-blue-300/40 hover:bg-white/10   `} aria-pressed={level === item} onClick={() => setLevel(item)}><span className="level-number">0{index + 1}</span><b>{item}</b><small>{['Start with fundamentals and build confidence.', 'Practice common interview questions and coding.', 'Take on deeper tradeoffs and harder problems.'][index]}</small></button>)}</div>}
    {setupStep === 3 && <><div className="mode-grid">{modes.map(item => <button key={item.name} className={`choice-card mode-card ${mode === item.name ? 'selected' : ''} rounded-xl border-white/10 bg-white/5 text-paper backdrop-blur-md hover:border-blue-300/40 hover:bg-white/10   `} aria-pressed={mode === item.name} onClick={() => setMode(item.name)}><div className="choice-icon"><Icon name={item.icon} size={22} /></div><b>{item.name}</b><small>{item.description}</small></button>)}</div><div className="choice-label">Question count</div><div className="segmented">{[3, 5, 8, 10].map(value => <button key={value} className={`segment ${limit === value ? 'selected' : ''}`} aria-pressed={limit === value} onClick={() => setLimit(value)}>{value} questions</button>)}</div></>}
    <div className="setup-footer">{setupStep > 1 ? <button className="secondary-btn rounded-lg border border-white/15 bg-white/5 text-paper backdrop-blur-md hover:bg-white/10   " onClick={() => setSetupStep(step => step - 1)}>← Back</button> : <span className="setup-note">Your preferences are saved on this device.</span>}{setupStep < 3 ? <button className="primary-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" onClick={() => setSetupStep(step => step + 1)}>Continue →</button> : <button className="primary-btn start-interview-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" onClick={startInterview} disabled={working}>{working && <span className="button-spinner" aria-hidden="true" />}{working ? 'Starting interview…' : 'Start interview →'}</button>}</div>
  </>;

  if (!authReady) return <div className="auth-screen relative isolate grid min-h-screen place-items-center overflow-hidden bg-none bg-ink px-6 py-12 text-paper"><div className="pointer-events-none absolute left-1/2 top-0 h-96 w-96 -translate-x-1/2 rounded-full bg-wine-600/25 blur-3xl" /><div className="auth-card relative z-10 w-full max-w-md rounded-2xl border border-white/10 bg-white/5 p-10 text-center shadow-2xl backdrop-blur-2xl"><p className="text-paper">Checking your sign-in…</p></div></div>;
  if (!supabase || !user) return <div className="auth-screen relative isolate grid min-h-screen place-items-center overflow-hidden bg-none bg-ink px-6 py-12 text-paper"><div className="pointer-events-none absolute left-1/2 top-0 h-96 w-96 -translate-x-1/2 rounded-full bg-wine-600/25 blur-3xl" /><div className="auth-card relative z-10 w-full max-w-md rounded-2xl border border-white/10 bg-white/5 p-10 text-center shadow-2xl backdrop-blur-2xl">
    <img className="auth-logo mx-auto mb-6 h-16 w-16 object-contain" src={logo} alt="Cogniv AI" />
    <div className="eyebrow mb-2 text-wine-400 ">Interview practice</div><h1 className="mb-3 text-3xl font-medium text-paper">{supabase ? 'Welcome back' : 'Sign-in setup needed'}</h1>
    <p className="mx-auto mb-6 max-w-sm text-stone-300">{supabase ? 'Sign in with Google to save your practice history to your account.' : 'Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to your environment, then rebuild the app.'}</p>
    {authError && <div className="auth-error mb-4 rounded-lg border border-wine-400/30 bg-wine-700/30 px-3 py-2 text-wine-400" role="alert">{authError}</div>}
    {supabase && <button className="google-btn w-full rounded-lg border border-white/15 bg-paper px-5 py-3 text-ink transition-colors hover:bg-white  " onClick={async () => { if (!supabase) return; setAuthError(''); const { error } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } }); if (error) setAuthError(error.message); }}><span className="google-mark">G</span> Continue with Google</button>}
    <small className="mt-5 block text-stone-400">Your interview reports are private to your account.</small>
  </div></div>;

  return <div className="app-shell min-h-screen bg-ink text-paper  ">
    <aside className="sidebar border-white/10 bg-[#0b0b0c]/90 backdrop-blur-xl  "><a className="brand text-paper " href="#home" onClick={event => { event.preventDefault(); navigate('home'); }}><span className="brand-mark"><img src={logo} alt="" /></span><span>COGNIV AI</span></a><div className="side-label">Workspace</div><nav className="side-nav" aria-label="Main navigation"><button disabled={page === 'interview'} className={`nav-link ${page === 'home' ? 'active border-l-2 border-wine-400 bg-wine-700/20 text-paper' : 'text-stone-300'} rounded-lg transition-colors hover:bg-white/5 hover:text-white  ` } onClick={() => navigate('home')}><span className="nav-icon"><Icon name="home" /></span>Home</button><button disabled={page === 'interview'} className={`nav-link ${page === 'setup' ? 'active border-l-2 border-wine-400 bg-wine-700/20 text-paper' : 'text-stone-300'} rounded-lg transition-colors hover:bg-white/5 hover:text-white  ` } onClick={() => navigate('setup')}><span className="nav-icon"><Icon name="play" /></span>Practice</button><button disabled={page === 'interview'} className={`nav-link ${page === 'history' ? 'active border-l-2 border-wine-400 bg-wine-700/20 text-paper' : 'text-stone-300'} rounded-lg transition-colors hover:bg-white/5 hover:text-white  ` } onClick={() => navigate('history')}><span className="nav-icon"><Icon name="chart" /></span>My progress</button></nav><div className="side-bottom"><div className="mentor-mini border-white/10 bg-white/5 backdrop-blur-md  "><div className="mentor-icon bg-wine-700/40 text-wine-400">AI</div><div><b>Your AI coach</b><small>Ready when you are</small></div><span className="online-dot bg-wine-400 shadow-none" /></div><button disabled={page === 'interview'} className={`nav-link ${page === 'profile' ? 'active border-l-2 border-wine-400 bg-wine-700/20 text-paper' : 'text-stone-300'} rounded-lg transition-colors hover:bg-white/5 hover:text-white  ` } onClick={() => navigate('profile')}><span className="nav-icon"><Icon name="settings" /></span>Settings</button></div><div className="sidebar-foot">Practice with purpose.</div></aside>
    <main className="main-area bg-ink text-paper  "><header className="topbar border-white/10 "><button className="mobile-brand" onClick={() => navigate('home')}><span className="brand-mark"><img src={logo} alt="" /></span> COGNIV AI</button><div className="top-spacer" /><span className="streak border-white/10 bg-white/5 text-stone-200 backdrop-blur-md   "><span><Icon name="book" size={15} /></span> <b>{streak}</b> day streak</span><span className="user-email">{user?.email}</span><button className="signout-btn" disabled={page === 'interview'} onClick={() => supabase?.auth.signOut()}>Sign out</button><button className="avatar-button grid overflow-hidden rounded-full border border-white/15 bg-white/10 p-0 text-paper   " onClick={() => navigate('profile')} aria-label="Open profile">{avatarSource ? <img className="h-full w-full rounded-full object-cover" src={avatarSource} alt="" referrerPolicy="no-referrer" /> : name[0]}</button></header>
      {notice && <div className="toast show" role="alert">{notice}</div>}
      {page === 'home' && <section className="page active dashboard-page"><div className="welcome-line"><div><div className="eyebrow">Interview practice</div><h1>Your practice, {name.split(' ')[0]}</h1><p>Build interview confidence with focused practice and feedback.</p></div><button className="link-btn" onClick={() => navigate('history')}>View progress ↗</button></div><div className="hero-card relative isolate overflow-hidden rounded-2xl border border-wine-400/30 bg-gradient-to-br from-wine-700/80 via-wine-600/30 to-surface/90 shadow-[0_0_80px_-36px_rgba(163,69,88,0.8)] backdrop-blur-xl    "><div className="hero-copy relative z-10"><div className="eyebrow">Practice session <span className="eyebrow-separator">/</span> 12 min</div><h2>Practice job interviews with focused feedback.</h2><p>Choose a topic and level, then work through questions with an AI interviewer.</p><button className="primary-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" onClick={() => navigate('setup')}>Set up practice <span>→</span></button></div><div className="hero-art"><div className="path-visual relative h-full w-full rounded-xl border border-white/15 bg-white/10 p-4 backdrop-blur-xl  "><span className="path-caption">Session progress</span><svg className="absolute inset-x-3 top-8 h-24 w-[calc(100%-24px)] overflow-visible" viewBox="0 0 250 150" aria-hidden="true"><path className="path-line fill-none stroke-white/40 stroke-2" d="M18 122 C55 121 51 79 91 86 S132 113 155 61 S202 32 231 24"/><circle cx="18" cy="122" r="7" className="path-node complete fill-wine-400 stroke-surface"/><circle cx="91" cy="86" r="6" className="path-node complete fill-wine-400 stroke-surface"/><circle cx="155" cy="61" r="7" className="path-node current fill-blue-300 stroke-surface"/><circle cx="231" cy="24" r="6" className="path-node future fill-paper stroke-surface"/></svg><div className="path-label absolute bottom-3 right-3 flex flex-col items-end gap-1 text-right"><b className="text-sm font-medium text-paper">5 questions</b><span className="text-xs text-stone-300">One at a time</span></div></div></div></div><div className="stat-grid"><div className="stat-card rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><div className="stat-top">Sessions completed </div><div className="stat-value">{sessions.length}</div><div className="stat-note">Every session is progress</div></div><div className="stat-card rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><div className="stat-top">Average score </div><div className="stat-value">{average}<small> {average !== '—' ? '/ 10' : ''}</small></div><div className="stat-note">Keep your momentum going</div></div><div className="stat-card rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><div className="stat-top">Practice streak </div><div className="stat-value">{streak}<small> days</small></div><div className="stat-note">Consecutive practice days</div></div></div><div className="section-head text-paper "><h2>Recent sessions</h2><button className="link-btn" onClick={() => navigate('history')}>See all →</button></div><div className="session-list">{sessionCards}</div><div className="section-head text-paper "><h2>Your progress</h2><button className="link-btn" onClick={() => navigate('history')}>View progress →</button></div><div className="two-col"><div className="panel rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><h3>Score over time</h3><p>Hover, tap, or focus a point to inspect a practice.</p>{homeChart}</div><div className="panel rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><h3>Skills to grow</h3><p>Your focus areas at a glance</p>{['Communication', 'Technical knowledge', 'Problem solving'].map((item, i) => <div className="skill-row" key={item}><span>{item}</span><div className="skill-track"><i style={{ width: `${Math.max(35, Number(average === '—' ? 6.8 : average) * 10 - i * 7)}%` }} /></div><b>{Math.max(35, Number(average === '—' ? 6.8 : average) * 10 - i * 7)}%</b></div>)}</div></div><div className="panel activity-panel rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><div className="activity-heading mb-5 flex items-center justify-between gap-4 max-sm:flex-col max-sm:items-start"><div><h3>Practice activity</h3><p>Small sessions add up over time</p></div><strong className="whitespace-nowrap text-sm font-medium text-wine-400">{streak} day streak</strong></div><ActivityHeatmap sessions={sessions} /></div></section>}
      {page === 'setup' && <section className="page active">{setupContent}</section>}
      {page === 'interview' && <section className="page active"><div className="interview-shell"><div className="interview-top border-white/10 bg-white/5 backdrop-blur-lg  "><div className="coach-avatar">AI</div><div><b>{topic} practice</b><small>{mode} · {level}</small></div><div className="interview-progress"><b>Question {questionNo} of {limit}</b><div className="progress-track"><i style={{ width: `${questionNo / limit * 100}%` }} /></div></div></div>{mode === 'Coding & problem solving' && <div className="coding-workbench"><div className="coding-heading"><div><h3>Code runner</h3><p>Tab and Enter keep indentation consistent</p></div><label>Language<select value={compilerLanguage} onChange={event => { const id = Number(event.target.value); const language = compilerLanguages.find(item => item.id === id); setCompilerLanguage(id); if (language) setSourceCode(starterCode(language)); }}>{compilerLanguages.map(language => <option key={language.id} value={language.id}>{language.name}</option>)}</select></label></div><label className="code-label" htmlFor="practice-code">Source code</label><textarea id="practice-code" className="code-editor" value={sourceCode} onChange={event => setSourceCode(event.target.value)} onKeyDown={handleCodeKeyDown} spellCheck={false} autoCapitalize="off" autoCorrect="off" aria-label="Source code editor"/><label className="code-label" htmlFor="practice-stdin">Standard input <span>Optional</span></label><textarea id="practice-stdin" className="stdin-editor" value={stdin} onChange={event => setStdin(event.target.value)} placeholder="Input passed to your program"/><div className="coding-actions"><small>Code is sent to Judge0 CE to compile and run</small><button className="primary-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" onClick={runCode} disabled={compilerBusy}>{compilerBusy ? "Running…" : "Run code"}</button></div><div className="compiler-result"><div><b>Output</b><span>{compilerStatus}</span></div><pre>{compilerOutput}</pre><div className="compiler-buttons"><button className="link-btn" onClick={() => setAnswer(current => current ? `${current}\n\n${sourceCode}` : sourceCode)}>Add code to response</button><button className="primary-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" onClick={submitCodeAnswer} disabled={working || compilerBusy}>{working ? 'Submitting…' : 'Submit code answer'}</button></div></div></div>}<div className="chat-box border-white/10 bg-[#151416]/85 backdrop-blur-xl  ">{messages.map((message, index) => <div className={`chat-message ${message.role === 'candidate' ? 'candidate' : ''}`} key={index}><div className="chat-face">{message.role === 'candidate' ? name[0] : 'AI'}</div><div className="bubble-wrap"><small>{message.role === 'candidate' ? name : 'Interviewer'}</small><div className="bubble">{message.text}</div></div></div>)}{working && <div className="chat-message"><div className="chat-face">AI</div><div className="loading-note" role="status"><span className="loading-ring" aria-hidden="true" /><span className="loading-copy"><b>Preparing your next question</b><small>{dailyQuote()}</small></span></div></div>}</div><form className="answer-form" onSubmit={submitAnswer}><textarea value={answer} onChange={event => setAnswer(event.target.value)} placeholder="Take your time. Type your answer here…" aria-label="Your answer" required /><div className="answer-actions"><button className="primary-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" type="submit" disabled={working || !answer.trim()}>{working ? 'Submitting…' : 'Submit answer'}</button><button className="secondary-btn rounded-lg border border-white/15 bg-white/5 text-paper backdrop-blur-md hover:bg-white/10   " type="button" onClick={endInterview} disabled={working}>End interview</button></div></form></div></section>}
      {page === 'results' && report && <section className="page active"><div className="page-heading"><div className="eyebrow">Practice complete</div><h1>Practice report</h1><p>{report.overall_feedback}</p></div><div className="result-hero border-white/10 bg-white/5 backdrop-blur-xl  "><div className="score-ring" style={{ ['--score' as string]: `${Number(report.overall_score ?? 0) * 10}%` }}><div className="score-center"><strong>{Number(report.overall_score ?? 0).toFixed(1)}</strong><small>OUT OF 10</small></div></div><div className="result-copy"><div className="eyebrow">{topic.toUpperCase()} <span className="eyebrow-separator">/</span> {mode.toUpperCase()}</div><h2>Your practice report</h2><p>One clear next step makes all the difference.</p><div className="insight-badges"><span>Knowledge {Number(report.knowledge_score ?? 0).toFixed(1)}</span>{report.problem_solving_score != null && <span>Problem solving {Number(report.problem_solving_score).toFixed(1)}</span>}</div></div></div><div className="feedback-grid"><div className="feedback-card"><h3><span className="feedback-marker good">+</span> What went well</h3><ul>{(report.strengths || []).map(item => <li key={item}>{item}</li>)}</ul></div><div className="feedback-card improve"><h3><span className="feedback-marker grow">↗</span> Room to grow</h3><ul>{(report.areas_to_improve || report.weaknesses || []).map(item => <li key={item}>{item}</li>)}</ul></div></div><div className="result-actions"><button className="primary-btn rounded-lg border border-white/70 bg-paper text-ink shadow-none font-medium transition-colors hover:bg-white hover:text-ink active:scale-[0.98]" onClick={() => navigate('setup')}>Practice again →</button><button className="secondary-btn rounded-lg border border-white/15 bg-white/5 text-paper backdrop-blur-md hover:bg-white/10   " onClick={() => navigate('history')}>See progress</button></div></section>}
      {page === 'history' && <section className="page active"><div className="page-heading"><div className="eyebrow">Practice history</div><h1>Progress</h1><p>Every session adds to your confidence.</p></div><div className="stat-grid"><div className="stat-card rounded-xl border-white/10 border-t-2 border-t-wine-400 bg-white/5 backdrop-blur-lg [&_.stat-value]:text-wine-400    "><div className="stat-top">Sessions completed</div><div className="stat-value">{sessions.length}</div></div><div className="stat-card rounded-xl border-white/10 border-t-2 border-t-blue-300 bg-white/5 backdrop-blur-lg [&_.stat-value]:text-blue-300    "><div className="stat-top">Average score</div><div className="stat-value">{average}</div></div><div className="stat-card rounded-xl border-white/10 border-t-2 border-t-paper/80 bg-white/5 backdrop-blur-lg [&_.stat-value]:text-paper    "><div className="stat-top">Practice topics</div><div className="stat-value">{new Set(sessions.map(item => item.topic)).size}</div></div></div><div className="section-head text-paper "><h2>Score trend</h2></div><div className="panel rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  ">{homeChart}</div><div className="panel activity-panel rounded-xl border-white/10 bg-white/5 backdrop-blur-lg  "><div className="activity-heading"><div><h3>Practice activity</h3><p>Your completed sessions across the year</p></div><strong>{streak} day streak</strong></div><ActivityHeatmap sessions={sessions} /></div><div className="section-head text-paper "><h2>Practice history</h2><button className="link-btn" onClick={() => navigate('setup')}>+ New practice</button></div><div className="filter-row">{['All', ...new Set(sessions.map(item => item.topic))].map(item => <button className={`filter-chip ${filter === item ? 'active' : ''} rounded-lg border-white/10 bg-white/5 text-stone-300 backdrop-blur-md hover:bg-white/10   `} key={item} onClick={() => setFilter(item)}>{item}</button>)}</div><div className="history-list">{sessions.filter(item => filter === 'All' || item.topic === filter).map((item, index) => <div className="history-row" key={`${item.date}-${index}`}><span className="topic-icon bg-blue-400/15 text-blue-300"><Icon name={topics.find(t => t.name === item.topic)?.icon || 'book'} /></span><div className="history-info"><b>{item.topic} interview</b><small>{item.date} · {item.duration}</small></div><div className="history-result">{item.score.toFixed(1)}<small> / 10</small></div></div>)}</div></section>}
      {page === 'profile' && <section className="page active"><div className="page-heading"><div className="eyebrow">PREFERENCES</div><h1>Your practice defaults</h1><p>Keep the next session ready for you.</p></div><div className="panel settings-summary"><h3>Interview setup</h3><div className="setting-row"><div><b>Experience level</b><small>{level}</small></div><button className="secondary-btn small-btn" onClick={() => { routeTo('setup'); setSetupStep(2); }}>Change</button></div><div className="setting-row"><div><b>Interview style</b><small>{mode}</small></div><button className="secondary-btn small-btn" onClick={() => { routeTo('setup'); setSetupStep(3); }}>Change</button></div><div className="setting-row"><div><b>Question count</b><small>{limit} questions</small></div><button className="secondary-btn small-btn" onClick={() => { routeTo('setup'); setSetupStep(3); }}>Change</button></div></div><div className="profile-photo-row mt-4 flex flex-wrap items-center gap-4 rounded-xl border border-white/10 bg-white/5 p-4  "><div className="profile-photo-preview grid size-[52px] shrink-0 place-items-center overflow-hidden rounded-full border border-white/15 bg-white/5  ">{avatarSource ? <img className="h-full w-full rounded-full object-cover" src={avatarSource} alt="Profile photo" referrerPolicy="no-referrer" /> : <span className="grid h-full w-full place-items-center rounded-full text-lg text-paper ">{name[0]}</span>}</div><div className="profile-photo-copy flex min-w-[180px] flex-1 flex-col gap-1"><b>Profile photo</b><small>{accountPhoto ? 'Uploaded to this account' : user?.user_metadata?.avatar_url || user?.user_metadata?.picture ? 'From your Google account' : 'No photo set'}</small></div><label className="secondary-btn small-btn upload-photo-button relative cursor-pointer overflow-hidden rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-paper   " htmlFor="profile-photo-input">Upload photo<input className="absolute inset-0 h-full w-full cursor-pointer opacity-0" id="profile-photo-input" type="file" accept="image/*" onChange={event => { void uploadProfilePhoto(event.currentTarget.files?.[0]); event.currentTarget.value = ''; }} /></label>{accountPhoto && <button className="link-btn" onClick={() => setProfilePhoto('')}>Use Google photo</button>}</div><div className="profile-note mt-4 flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4  "><span className="note-symbol grid size-8 shrink-0 place-items-center rounded-lg bg-wine-700/30 text-wine-400"><Icon name="book" size={18} /></span><div><b>A little practice adds up.</b><p>Your sessions and preferences stay saved on this device.</p></div></div></section>}
    </main>
    <nav className="bottom-nav border-white/10 bg-[#111112]/85 text-paper backdrop-blur-xl   " aria-label="Mobile navigation"><button className={page === 'home' ? 'active' : ''} onClick={() => navigate('home')}><span className="nav-icon"><Icon name="home" /></span>Home</button><button className={page === 'setup' ? 'active' : ''} onClick={() => navigate('setup')}><span className="nav-icon"><Icon name="play" /></span>Practice</button><button className={page === 'history' ? 'active' : ''} onClick={() => navigate('history')}><span className="nav-icon"><Icon name="chart" /></span>Progress</button><button className={page === 'profile' ? 'active' : ''} onClick={() => navigate('profile')}><span className="nav-icon"><Icon name="settings" /></span>Settings</button></nav>
  </div>;
}
