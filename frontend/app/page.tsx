"use client";
import { useEffect, useRef, useState } from "react";
import { API, get, post } from "../lib/api";

const TABS = ["Library", "Notes", "Feynman", "Flashcards", "Mock Exam", "Syllabus", "War Room", "Focus"] as const;
type Tab = typeof TABS[number];

export default function Home() {
  const [uid, setUid] = useState(""); const [email, setEmail] = useState("");
  const [tab, setTab] = useState<Tab>("Library");
  useEffect(() => { const u = localStorage.getItem("uid"); if (u) setUid(u); }, []);
  async function login() { const u = await post("/api/users", { email }); localStorage.setItem("uid", u.id); setUid(u.id); }
  if (!uid) return (
    <main className="mx-auto max-w-md p-8 space-y-4">
      <h1 className="text-3xl font-bold">OmniPrep</h1><p className="text-slate-400">AI Academic Operating System</p>
      <input className="inp" placeholder="you@college.edu" value={email} onChange={e => setEmail(e.target.value)} />
      <button className="btn w-full" onClick={login}>Start studying</button>
    </main>);
  return (
    <main className="mx-auto max-w-4xl p-4 space-y-4">
      <header className="flex items-center justify-between"><h1 className="text-2xl font-bold">OmniPrep</h1>
        <button className="text-xs text-slate-500" onClick={() => { localStorage.removeItem("uid"); setUid(""); }}>log out</button></header>
      <nav className="flex flex-wrap gap-2">{TABS.map(t => <button key={t} onClick={() => setTab(t)} className={`rounded-full px-3 py-1 text-sm ${tab === t ? "bg-indigo-600" : "bg-slate-800"}`}>{t}</button>)}</nav>
      {tab === "Library" && <Library uid={uid} />}
      {tab === "Notes" && <Notes uid={uid} />}
      {tab === "Feynman" && <Feynman uid={uid} />}
      {tab === "Flashcards" && <Cards uid={uid} />}
      {tab === "Mock Exam" && <MockExam uid={uid} />}
      {tab === "Syllabus" && <Syllabus />}
      {tab === "War Room" && <WarRoom uid={uid} />}
      {tab === "Focus" && <Focus />}
    </main>);
}

const Out = ({ t }: { t: any }) => t ? <pre className="card whitespace-pre-wrap text-sm">{typeof t === "string" ? t : JSON.stringify(t, null, 2)}</pre> : null;

function Library({ uid }: { uid: string }) {
  const [src, setSrc] = useState<any[]>([]); const [yt, setYt] = useState("");
  const load = () => get(`/api/sources?user_id=${uid}`).then(setSrc);
  useEffect(() => { load(); const i = setInterval(load, 3000); return () => clearInterval(i); }, []);
  async function up(e: any) { const f = new FormData(); f.append("user_id", uid); f.append("file", e.target.files[0]); await fetch(API + "/api/sources/upload", { method: "POST", body: f }); load(); }
  return <div className="space-y-3">
    <div className="card space-y-2"><p className="text-sm text-slate-400">PDF, .ipynb, MP3/WAV lectures, handwritten-note images, text</p><input type="file" onChange={up} />
      <div className="flex gap-2"><input className="inp" placeholder="YouTube URL" value={yt} onChange={e => setYt(e.target.value)} />
        <button className="btn" onClick={async () => { await post("/api/sources/youtube", { user_id: uid, url: yt }); setYt(""); load(); }}>Add</button></div></div>
    {src.map(s => <div key={s.id} className="card flex justify-between text-sm"><span>{s.name} <i className="text-slate-500">({s.kind})</i></span><span>{s.status} {s.detail}</span></div>)}
  </div>;
}

function Notes({ uid }: { uid: string }) {
  const [topic, setTopic] = useState(""); const [p, setP] = useState("grace"); const [o, setO] = useState<any>(""); const [busy, setBusy] = useState(false);
  const run = async (path: string) => { setBusy(true); try { const r = await post(path, { user_id: uid, topic, persona: p }); setO(r.notes || r.cheatsheet); } catch (e: any) { setO(e.message); } setBusy(false); };
  return <div className="space-y-3"><input className="inp" placeholder="Topic" value={topic} onChange={e => setTopic(e.target.value)} />
    <select className="inp" value={p} onChange={e => setP(e.target.value)}><option value="dr_socratic">Dr. Socratic – rigorous proofs</option><option value="grace">Grace – 80/20 emergency cram</option><option value="architect_alex">Architect Alex – trade-offs & code</option></select>
    <div className="flex gap-2"><button className="btn" onClick={() => run("/api/notes")}>Generate notes</button><button className="btn" onClick={() => run("/api/cheatsheet")}>Panic Crammer sheet</button></div>{busy && "Thinking…"}<Out t={o} /></div>;
}

function Feynman({ uid }: { uid: string }) {
  const [topic, setTopic] = useState(""); const [x, setX] = useState(""); const [log, setLog] = useState<string[]>([]);
  const speak = (t: string) => { if ("speechSynthesis" in window) speechSynthesis.speak(new SpeechSynthesisUtterance(t)); };
  function dictate() { const R = (window as any).webkitSpeechRecognition; if (!R) return alert("Voice input needs Chrome/Edge"); const r = new R(); r.onresult = (e: any) => setX(e.results[0][0].transcript); r.start(); }
  async function send() { const r = await post("/api/feynman", { user_id: uid, topic, explanation: x }); setLog([...log, "You: " + x, "Prof: " + r.reply]); speak(r.reply); setX(""); }
  return <div className="space-y-3"><input className="inp" placeholder="Topic" value={topic} onChange={e => setTopic(e.target.value)} />
    <textarea className="inp" rows={4} placeholder="Explain it like I'm 12…" value={x} onChange={e => setX(e.target.value)} />
    <div className="flex gap-2"><button className="btn" onClick={send}>Submit</button><button className="btn" onClick={dictate}>🎤 Speak</button></div>{log.map((l, i) => <div key={i} className="card text-sm">{l}</div>)}</div>;
}

function Cards({ uid }: { uid: string }) {
  const [topic, setTopic] = useState(""); const [due, setDue] = useState<any[]>([]); const [flip, setFlip] = useState(false);
  const load = () => get(`/api/flashcards/due?user_id=${uid}`).then(setDue); useEffect(() => { load(); }, []);
  const c = due[0];
  return <div className="space-y-3"><div className="flex gap-2"><input className="inp" placeholder="Topic to generate cards from" value={topic} onChange={e => setTopic(e.target.value)} />
    <button className="btn" onClick={async () => { await post("/api/flashcards/generate", { user_id: uid, topic }); load(); }}>Generate</button></div>
    {c ? <div className="card space-y-3"><p className="text-xs text-slate-500">{due.length} due</p><p onClick={() => setFlip(!flip)} className="cursor-pointer text-lg">{flip ? c.back : c.front}</p>
      {flip && <div className="flex gap-2">{[["Again", 1], ["Hard", 3], ["Good", 4], ["Easy", 5]].map(([l, q]: any) => <button key={l} className="btn" onClick={async () => { await post(`/api/flashcards/${c.id}/review`, { quality: q }); setFlip(false); load(); }}>{l}</button>)}</div>}</div> : <p className="text-slate-400">Nothing due 🎉</p>}</div>;
}

function MockExam({ uid }: { uid: string }) {
  const [topic, setTopic] = useState(""); const [ex, setEx] = useState<any>(null); const [ans, setAns] = useState<string[]>([]);
  const t0 = useRef(Date.now()); const secs = useRef<number[]>([]); const [i, setI] = useState(0); const [rep, setRep] = useState<any>(null);
  async function start() { const e = await post("/api/exams", { user_id: uid, topic, n: 5 }); setEx(e); setAns([]); secs.current = []; setI(0); setRep(null); t0.current = Date.now(); }
  async function next(a: string) { secs.current[i] = (Date.now() - t0.current) / 1000; t0.current = Date.now(); const na = [...ans]; na[i] = a; setAns(na);
    if (i + 1 < ex.questions.length) setI(i + 1); else setRep(await post(`/api/exams/${ex.id}/submit`, { total_minutes: 10, answers: na.map((x, k) => ({ index: k, answer: x || "", seconds: secs.current[k] || 0 })) })); }
  if (rep) return <Out t={rep} />;
  if (!ex) return <div className="flex gap-2"><input className="inp" placeholder="Topic" value={topic} onChange={e => setTopic(e.target.value)} /><button className="btn" onClick={start}>Start 10-min exam</button></div>;
  return <Q key={i} q={ex.questions[i]} n={i + 1} of={ex.questions.length} onNext={next} />;
}
function Q({ q, n, of, onNext }: any) { const [a, setA] = useState(""); return <div className="card space-y-2"><p className="text-xs text-slate-500">Q{n}/{of} · {q.marks} marks</p><p>{q.q}</p><input className="inp" value={a} onChange={e => setA(e.target.value)} /><button className="btn" onClick={() => onNext(a)}>Next</button></div>; }

function Syllabus() {
  const [topics, setT] = useState(""); const [papers, setP] = useState(""); const [o, setO] = useState<any>(null);
  return <div className="space-y-3"><textarea className="inp" rows={3} placeholder="Syllabus topics, one per line" value={topics} onChange={e => setT(e.target.value)} />
    <textarea className="inp" rows={6} placeholder="Past paper text (separate papers with ====)" value={papers} onChange={e => setP(e.target.value)} />
    <button className="btn" onClick={async () => setO(await post("/api/syllabus/map", { topics: topics.split("\n").filter(Boolean), past_papers: papers.split("====") }))}>Map weightage</button>
    {o && <div className="space-y-1">{o.map((r: any) => <div key={r.topic} className="card"><div className="flex justify-between text-sm"><span>{r.topic}</span><span>{r.mark_weight_pct}% · p={r.exam_probability}</span></div><div className="mt-1 h-2 rounded bg-slate-800"><div className="h-2 rounded bg-indigo-500" style={{ width: `${r.mark_weight_pct}%` }} /></div></div>)}</div>}</div>;
}

function WarRoom({ uid }: { uid: string }) {
  const [room, setRoom] = useState("exam-crew"); const [name, setName] = useState("student" + uid.slice(0, 3)); const ws = useRef<WebSocket | null>(null);
  const [log, setLog] = useState<string[]>([]); const [text, setText] = useState(""); const [users, setU] = useState<string[]>([]);
  const add = (s: string) => setLog(l => [...l, s]);
  function join() { const w = new WebSocket(`${API.replace("http", "ws")}/ws/rooms/${room}?user=${name}`); ws.current = w;
    w.onmessage = e => { const m = JSON.parse(e.data);
      if (m.type === "presence") setU(m.users); else if (m.type === "state") m.notes.forEach((n: any) => add(`📝 ${n.user}: ${n.text}`));
      else if (m.type === "note") add(`📝 ${m.user}: ${m.text}`); else if (m.type === "card") add(`🃏 ${m.by}: ${m.front} → ${m.back}`);
      else if (m.type === "trivia") add(`❓ TRIVIA: ${m.q}`); else if (m.type === "trivia_result") add(`🏆 ${m.winner} got it! (${m.answer})`); else if (m.type === "trivia_wrong") add("❌ not quite"); }; }
  const send = (o: any) => ws.current?.send(JSON.stringify(o));
  return <div className="space-y-3"><div className="flex gap-2"><input className="inp" value={room} onChange={e => setRoom(e.target.value)} /><input className="inp" value={name} onChange={e => setName(e.target.value)} /><button className="btn" onClick={join}>Join</button></div>
    <p className="text-xs text-slate-400">Online: {users.join(", ")}</p><div className="card h-64 space-y-1 overflow-auto text-sm">{log.map((l, i) => <div key={i}>{l}</div>)}</div>
    <div className="flex gap-2"><input className="inp" value={text} onChange={e => setText(e.target.value)} />
      <button className="btn" onClick={() => { send({ type: "note", text }); setText(""); }}>Note</button>
      <button className="btn" onClick={() => { const [f, b] = text.split("="); send({ type: "card", front: f, back: b || "" }); setText(""); }}>Card (q=a)</button>
      <button className="btn" onClick={() => send({ type: "trivia_start" })}>Trivia</button>
      <button className="btn" onClick={() => { send({ type: "trivia_answer", answer: text }); setText(""); }}>Answer</button></div></div>;
}

function Focus() {
  const [ev, setEv] = useState<{ correct: boolean; seconds: number }[]>([]); const start = useRef(Date.now()); const [o, setO] = useState<any>(null);
  async function log(c: boolean) { const e = [...ev, { correct: c, seconds: 12 + Math.random() * 20 }]; setEv(e);
    setO(await post("/api/wellness/check", { events: e, session_minutes: (Date.now() - start.current) / 60000 + e.length * 4 })); }
  return <div className="space-y-3"><p className="text-sm text-slate-400">Log each practice answer; OmniPrep watches accuracy/speed decay and triggers a Pomodoro break.</p>
    <div className="flex gap-2"><button className="btn" onClick={() => log(true)}>✅ Correct</button><button className="btn" onClick={() => log(false)}>❌ Wrong</button></div>
    <p className="text-sm">{ev.length} answers logged</p>{o?.break && <div className="card border-amber-500 text-amber-300">☕ Take a {o.pomodoro?.break_minutes}-min break — {o.reason}</div>}<Out t={o} /></div>;
}
