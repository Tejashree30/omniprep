# OmniPrep: AI Academic Operating System

An AI-powered exam-preparation platform that ingests your study material (PDFs, notebooks, lecture audio, YouTube, handwritten notes), turns it into persona-driven notes, quizzes and flashcards, and lets friends study together in real time.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-009688) ![Next.js](https://img.shields.io/badge/Next.js-14-black) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

| Module | What it does |
|---|---|
| **Multimodal ingestion** | PDFs, Jupyter notebooks, YouTube transcripts, lecture MP3/WAV (Whisper), handwritten-note images (OCR with LaTeX-style math normalisation) |
| **Hybrid RAG search** | BM25 + semantic similarity fused with Reciprocal Rank Fusion, then reranked; only top-k chunks reach the LLM |
| **Syllabus Weightage Mapper** | Scores topics by mark weight and appearance across past papers |
| **AI personas** | *Dr. Socratic* (rigorous proofs), *Grace* (80/20 emergency cram), *Architect Alex* (trade-offs and code) |
| **Feynman Interrogator** | Explain a topic by text or voice; the AI finds gaps and asks a follow-up |
| **Spaced repetition** | Flashcards scheduled with the SM-2 algorithm |
| **Panic Crammer** | Colour-coded one-page cheat sheets |
| **Exam Time Coach** | Mock exams with per-question pacing report |
| **War Rooms** | WebSocket rooms: shared notes, co-edited flashcards, AI trivia battles |
| **Focus Tracker** | Detects fatigue from accuracy and speed decay, suggests Pomodoro breaks |

## Architecture

```
Next.js UI ──REST/WebSocket──> FastAPI ──> Celery worker (heavy parsing) ──> Redis
                                  │
                                  └──> PostgreSQL / SQLite (+ vector chunks)  ──> OpenRouter LLM (optional)
```

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Async jobs | Celery + Redis (runs in-process when Redis is absent) |
| Data | PostgreSQL + pgvector (Docker) or SQLite (local) |
| AI | OpenRouter API, with offline fallbacks when no key is set |

## Quick start

### Option 1: Docker
```bash
cp .env.example .env          # optionally add OPENROUTER_API_KEY
docker compose up --build
```
App: http://localhost:3000 | API docs: http://localhost:8000/docs

### Option 2: Local (no Docker)
Requires Python 3.11 or 3.12 and Node.js 20+.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install fastapi "uvicorn[standard]" sqlalchemy celery redis httpx pydantic python-multipart pypdf youtube-transcript-api==0.6.2 Pillow pytesseract
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```
Audio transcription additionally needs `pip install openai-whisper` and `ffmpeg`; handwriting OCR needs the Tesseract binary.

### Configuration
| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Enables real LLM output (optional) |
| `OPENROUTER_MODEL` | Model name, default `openai/gpt-4o-mini` |
| `DATABASE_URL` | Defaults to SQLite locally |
| `REDIS_URL` | Enables the Celery worker; leave empty for in-process tasks |

## Project structure
```
backend/app/   main.py (API)  ingest.py  rag.py  personas.py  srs.py
               exam.py  syllabus.py  wellness.py  rooms.py  tasks.py  db.py  llm.py
backend/tests/ unit tests for retrieval, SM-2, syllabus, exam timing, wellness
frontend/app/  single-page dashboard with one tab per module
db/init.sql    pgvector extension setup
```

## Tests
```bash
cd backend && pip install pytest && pytest tests
```

## Design notes
- Embeddings are an offline hashing-trick placeholder so the project runs with no paid APIs; swap `rag.embed` for a hosted model and move vectors to pgvector for production.
- Retrieval keeps prompts small by sending only reranked top-k chunks. Benchmark on your own corpus before quoting token savings.
- Not yet implemented: JWT authentication, rate limiting, SuperMemo-18, true handwriting recognition via a vision model, and persistent war-room state across restarts (use Redis pub/sub to scale).

## Roadmap
LangGraph multi-agent workflow, vision-LLM handwriting OCR, auth, Redis-backed rooms, native pgvector search.

## License
MIT
