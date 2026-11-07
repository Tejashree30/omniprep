"""Mock exam generation + Exam Time-Management Coach post-mortem."""
import json, re
from .llm import chat
from .rag import tokenize

def generate_questions(topic: str, contexts: list[str], n=5) -> list[dict]:
    raw = chat("You write exam questions. Reply with ONLY a JSON list of objects "
               '{"q": str, "answer": str, "marks": int}.',
               f"Topic: {topic}\nMaterial:\n" + "\n---\n".join(contexts) + f"\nWrite {n} questions.")
    if raw:
        try:
            return json.loads(re.sub(r"^```json|```$", "", raw.strip()).strip())[:n]
        except Exception:
            pass
    qs = []  # offline fallback: cloze questions from the material
    for c in contexts:
        for s in re.split(r"(?<=[.!?])\s+", c):
            words = [w for w in s.split() if len(w) > 6]
            if len(s.split()) > 8 and words:
                key = max(words, key=len)
                qs.append({"q": s.replace(key, "_____"), "answer": key.strip(".,;:"), "marks": 2})
            if len(qs) >= n: return qs
    return qs

def grade(answer: str, truth: str) -> float:
    a, t = set(tokenize(answer)), set(tokenize(truth))
    return round(len(a & t) / len(t), 2) if t else 0.0

def timing_report(questions: list[dict], answers: list[dict], total_minutes: float) -> dict:
    """answers: [{'index','answer','seconds'}]. Budget time proportional to marks."""
    total_marks = sum(q.get("marks", 1) for q in questions) or 1
    rows = []; wasted = 0
    for a in answers:
        q = questions[a["index"]]; budget = total_minutes * 60 * q.get("marks", 1) / total_marks
        score = grade(a["answer"], q.get("answer", ""))
        over = a["seconds"] - budget; wasted += max(0, over) if score < .5 else 0
        verdict = ("Overspent for low score - skip & return" if over > 0 and score < .5 else
                   "Overspent but paid off" if over > 0 else
                   "Too fast - review before moving on" if a["seconds"] < budget * .3 and score < .7 else "Good pacing")
        rows.append({"index": a["index"], "seconds": a["seconds"], "budget_s": round(budget),
                     "score": score, "marks": q.get("marks", 1), "verdict": verdict})
    earned = sum(r["score"] * r["marks"] for r in rows)
    return {"score": round(earned, 2), "out_of": total_marks, "rows": rows,
            "time_wasted_s": round(wasted),
            "advice": "Skip any question that exceeds 1.5x its time budget on the first pass." if wasted else "Pacing was healthy."}
