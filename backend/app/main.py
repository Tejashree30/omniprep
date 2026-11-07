import os, shutil, datetime as dt
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from .config import UPLOAD_DIR
from .db import init_db, Session, User, Source, VectorChunk, StudySession, Flashcard, Exam
from .ingest import kind_of
from .tasks import ingest_task
from .rag import hybrid_search, tokenize
from .llm import chat, extractive_summary, llm_available
from . import personas, srs, exam as examlib, syllabus, wellness
from .rooms import manager

app = FastAPI(title="OmniPrep API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _s(): init_db()

def _chunks(uid, source_ids=None):
    with Session() as s:
        q = select(VectorChunk).where(VectorChunk.user_id == uid)
        if source_ids: q = q.where(VectorChunk.source_id.in_(source_ids))
        return [{"id": c.id, "text": c.chunk_text, "embedding": c.embedding} for c in s.scalars(q)]

def _ctx(uid, query, k=6): return [c["text"] for c in hybrid_search(query, _chunks(uid), k)]

@app.get("/health")
def health(): return {"ok": True, "llm": llm_available()}

# ---- users
class UserIn(BaseModel): email: str; education_level: str = "undergraduate"
@app.post("/api/users")
def user(u: UserIn):
    with Session() as s:
        ex = s.scalar(select(User).where(User.email == u.email))
        if ex: return {"id": ex.id, "email": ex.email}
        n = User(email=u.email, education_level=u.education_level); s.add(n); s.commit()
        return {"id": n.id, "email": n.email}

# ---- Module 1: ingestion
@app.post("/api/sources/upload")
async def upload(user_id: str = Form(...), file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, f"{os.urandom(4).hex()}_{os.path.basename(file.filename)}")
    with open(path, "wb") as f: shutil.copyfileobj(file.file, f)
    with Session() as s:
        src = Source(user_id=user_id, kind=kind_of(file.filename), name=file.filename, path=path); s.add(src); s.commit()
        ingest_task.delay(src.id); return {"id": src.id, "kind": src.kind, "status": "queued"}

class UrlIn(BaseModel): user_id: str; url: str
@app.post("/api/sources/youtube")
def yt(b: UrlIn):
    with Session() as s:
        src = Source(user_id=b.user_id, kind="youtube", name=b.url, path=b.url); s.add(src); s.commit()
        ingest_task.delay(src.id); return {"id": src.id, "status": "queued"}

@app.get("/api/sources")
def sources(user_id: str):
    with Session() as s:
        return [{"id": x.id, "name": x.name, "kind": x.kind, "status": x.status, "detail": x.detail}
                for x in s.scalars(select(Source).where(Source.user_id == user_id).order_by(Source.created_at.desc()))]

@app.get("/api/search")
def search(user_id: str, q: str, k: int = 5):
    return [{"text": c["text"], "score": c["score"]} for c in hybrid_search(q, _chunks(user_id), k)]

class SylIn(BaseModel): topics: list[str]; past_papers: list[str]
@app.post("/api/syllabus/map")
def syl(b: SylIn): return syllabus.map_weightage(b.topics, b.past_papers)

# ---- Module 2: notes
class NotesIn(BaseModel): user_id: str; topic: str; persona: str = "grace"
@app.post("/api/notes")
def notes(b: NotesIn):
    p = personas.get(b.persona); ctx = _ctx(b.user_id, b.topic)
    if not ctx: raise HTTPException(400, "Upload study material first.")
    out = chat(p["system"], f"Topic: {b.topic}\n\nSource material:\n" + "\n---\n".join(ctx))
    if not out:
        out = f"# {b.topic} ({p['name']}, offline mode)\n" + "\n".join(f"- {x}" for c in ctx for x in extractive_summary(c, 3))
    with Session() as s:
        ss = StudySession(user_id=b.user_id, topic=b.topic, profile_mode=b.persona, notes=out); s.add(ss); s.commit()
        return {"id": ss.id, "persona": p["name"], "notes": out}

@app.post("/api/cheatsheet")
def cheat(b: NotesIn):
    ctx = _ctx(b.user_id, b.topic, 10)
    if not ctx: raise HTTPException(400, "Upload study material first.")
    out = chat("Compress into a one-page cheat sheet. Use these colour tags: [RED] must-memorise formulas, [YELLOW] definitions, [GREEN] worked-example patterns, [BLUE] common traps. Highest-probability content first.", "\n---\n".join(ctx))
    if not out: out = "\n".join(f"[YELLOW] {x}" for c in ctx for x in extractive_summary(c, 2))
    return {"cheatsheet": out}

# ---- Module 3: cognitive
class FeynIn(BaseModel): user_id: str; topic: str; explanation: str
@app.post("/api/feynman")
def feynman(b: FeynIn):
    ctx = _ctx(b.user_id, b.topic, 4)
    r = chat("You are a rigorous professor in a Feynman-technique session. Given the student's explanation and the source material, identify gaps or errors, then ask exactly ONE sharp follow-up question. Be concise.",
             f"Material:\n{chr(10).join(ctx)}\n\nStudent explanation:\n{b.explanation}")
    if not r:
        missing = sorted(set(tokenize(" ".join(ctx))) - set(tokenize(b.explanation)), key=len, reverse=True)[:3]
        r = f"Your explanation omits: {', '.join(missing)}. Can you explain how these connect to {b.topic}?"
    return {"reply": r}

class CardGen(BaseModel): user_id: str; topic: str; n: int = 8
@app.post("/api/flashcards/generate")
def cards(b: CardGen):
    qs = examlib.generate_questions(b.topic, _ctx(b.user_id, b.topic), b.n)
    with Session() as s:
        for q in qs: s.add(Flashcard(user_id=b.user_id, front=q["q"], back=q["answer"]))
        s.commit()
    return {"created": len(qs)}

@app.get("/api/flashcards/due")
def due(user_id: str):
    with Session() as s:
        return [{"id": c.id, "front": c.front, "back": c.back, "interval": c.interval} for c in
                s.scalars(select(Flashcard).where(Flashcard.user_id == user_id, Flashcard.due <= dt.datetime.utcnow()))]

class Review(BaseModel): quality: int
@app.post("/api/flashcards/{cid}/review")
def review(cid: str, b: Review):
    with Session() as s:
        c = s.get(Flashcard, cid)
        if not c: raise HTTPException(404)
        c.ease, c.interval, c.reps, c.due = srs.sm2(c.ease, c.interval, c.reps, b.quality); s.commit()
        return {"next_due": c.due.isoformat(), "interval_days": c.interval}

class ExamIn(BaseModel): user_id: str; topic: str; n: int = 5; minutes: float = 10
@app.post("/api/exams")
def make_exam(b: ExamIn):
    qs = examlib.generate_questions(b.topic, _ctx(b.user_id, b.topic), b.n)
    if not qs: raise HTTPException(400, "Upload study material first.")
    with Session() as s:
        e = Exam(user_id=b.user_id, topic=b.topic, questions=qs); s.add(e); s.commit()
        return {"id": e.id, "questions": [{"q": q["q"], "marks": q.get("marks", 1)} for q in qs]}

class Submit(BaseModel): answers: list[dict]; total_minutes: float = 10
@app.post("/api/exams/{eid}/submit")
def submit(eid: str, b: Submit):
    with Session() as s:
        e = s.get(Exam, eid)
        if not e: raise HTTPException(404)
        e.report = examlib.timing_report(e.questions, b.answers, b.total_minutes); s.commit()
        return e.report

# ---- Module 4: wellness + war rooms
class Well(BaseModel): events: list[dict]; session_minutes: float
@app.post("/api/wellness/check")
def well(b: Well): return wellness.check(b.events, b.session_minutes)

@app.websocket("/ws/rooms/{room}")
async def ws(websocket: WebSocket, room: str, user: str = "anon"):
    await manager.join(room, websocket, user)
    try:
        while True: await manager.handle(room, websocket, user, await websocket.receive_json())
    except WebSocketDisconnect:
        await manager.leave(room, websocket)
