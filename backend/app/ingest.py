"""Universal Harvester: PDF (multi-column aware), .ipynb, YouTube, audio (Whisper), handwritten notes (OCR -> LaTeX-ish)."""
import json, re, os
from .db import Session, Source, VectorChunk
from .rag import chunk_text, embed

def pdf_text(path: str) -> str:
    from pypdf import PdfReader
    out = []
    for p in PdfReader(path).pages:
        try: out.append(p.extract_text(extraction_mode="layout"))  # keeps column order
        except TypeError: out.append(p.extract_text())
    return "\n".join(filter(None, out))

def ipynb_text(path: str) -> str:
    nb = json.load(open(path, encoding="utf-8")); parts = []
    for c in nb.get("cells", []):
        s = "".join(c.get("source", []))
        parts.append(s if c["cell_type"] == "markdown" else f"[code]\n{s}")
    return "\n\n".join(parts)

def youtube_text(url: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    if not m: raise ValueError("Invalid YouTube URL")
    return " ".join(t["text"] for t in YouTubeTranscriptApi.get_transcript(m.group(1)))

def audio_text(path: str) -> str:
    import whisper
    return whisper.load_model(os.getenv("WHISPER_MODEL", "base")).transcribe(path)["text"]

def image_text(path: str) -> str:
    """OCR then normalise common math glyphs to LaTeX. For true handwriting, plug a vision LLM in here."""
    import pytesseract; from PIL import Image
    t = pytesseract.image_to_string(Image.open(path))
    for a, b in {"≤": r"\le ", "≥": r"\ge ", "∑": r"\sum ", "∫": r"\int ", "√": r"\sqrt ", "π": r"\pi ", "∞": r"\infty ", "×": r"\times "}.items():
        t = t.replace(a, b)
    return re.sub(r"(\w)\^(\w+)", r"$\1^{\2}$", t)

EXTRACT = {"pdf": pdf_text, "ipynb": ipynb_text, "youtube": youtube_text, "audio": audio_text, "image": image_text,
           "text": lambda p: open(p, encoding="utf-8", errors="ignore").read()}

def kind_of(name: str) -> str:
    e = name.lower().rsplit(".", 1)[-1]
    return {"pdf": "pdf", "ipynb": "ipynb", "mp3": "audio", "wav": "audio", "m4a": "audio",
            "png": "image", "jpg": "image", "jpeg": "image"}.get(e, "text")

def ingest_source(source_id: str):
    with Session() as s:
        src = s.get(Source, source_id); src.status = "processing"; s.commit()
        try:
            text = EXTRACT[src.kind](src.path)
            chunks = chunk_text(text)
            for c in chunks:
                s.add(VectorChunk(source_id=src.id, user_id=src.user_id, chunk_text=c, embedding=embed(c)))
            src.status, src.detail = "ready", f"{len(chunks)} chunks"
        except Exception as e:
            src.status, src.detail = "failed", str(e)[:300]
        s.commit()
