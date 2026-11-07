"""Syllabus Weightage Mapper: topic frequency + mark mass across past papers -> probability."""
import re
from .rag import tokenize

def map_weightage(topics: list[str], papers: list[str]) -> list[dict]:
    mass = {t: 0.0 for t in topics}; hits = {t: 0 for t in topics}
    for paper in papers:
        for q in re.split(r"\n\s*(?=(?:Q|Question)?\s*\d+[.)])", paper):
            m = re.findall(r"(\d+)\s*(?:marks?|pts?|points?)", q, re.I)
            marks = float(m[-1]) if m else 1.0
            qt = set(tokenize(q))
            for t in topics:
                tt = set(tokenize(t))
                if tt and len(tt & qt) / len(tt) >= 0.5:
                    mass[t] += marks; hits[t] += 1
    total = sum(mass.values()) or 1.0
    out = [{"topic": t, "mark_weight_pct": round(100 * mass[t] / total, 1),
            "appearances": hits[t],
            "exam_probability": round(min(0.99, hits[t] / max(len(papers), 1)), 2)} for t in topics]
    return sorted(out, key=lambda x: -x["mark_weight_pct"])
