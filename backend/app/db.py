import uuid, datetime as dt
from sqlalchemy import create_engine, String, Text, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
Session = sessionmaker(engine, expire_on_commit=False)
uid = lambda: str(uuid.uuid4())
now = lambda: dt.datetime.utcnow()

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[str] = mapped_column(String, default="student")
    education_level: Mapped[str] = mapped_column(String, default="undergraduate")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)          # pdf|ipynb|youtube|audio|image|text
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="queued")  # queued|processing|ready|failed
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class VectorChunk(Base):
    __tablename__ = "vector_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON)

class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    topic: Mapped[str] = mapped_column(String)
    profile_mode: Mapped[str] = mapped_column(String)
    notes: Mapped[str] = mapped_column(Text, default="")
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class Flashcard(Base):
    __tablename__ = "flashcards"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    interval: Mapped[int] = mapped_column(Integer, default=0)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    due: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    topic: Mapped[str] = mapped_column(String)
    questions: Mapped[list] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON, default=dict)

def init_db():
    Base.metadata.create_all(engine)
