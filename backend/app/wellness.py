"""Burnout & Focus Tracker: fatigue = long session + accuracy drop + slowing responses."""
def check(events: list[dict], session_minutes: float) -> dict:
    """events: chronological [{'correct': bool, 'seconds': float}]"""
    if len(events) < 6:
        return {"break": session_minutes >= 50, "reason": "Long session" if session_minutes >= 50 else "Keep going", "pomodoro": None}
    h = len(events) // 2; a, b = events[:h], events[h:]
    acc = lambda e: sum(x["correct"] for x in e) / len(e)
    spd = lambda e: sum(x["seconds"] for x in e) / len(e)
    drop = acc(a) - acc(b); slow = spd(b) / (spd(a) or 1)
    fatigued = (drop >= .2 and session_minutes >= 20) or (slow >= 1.5 and drop > 0) or session_minutes >= 90
    return {"break": fatigued, "accuracy_drop": round(drop, 2), "slowdown_x": round(slow, 2),
            "reason": "Accuracy/speed decline detected" if fatigued else "Focus stable",
            "pomodoro": {"break_minutes": 15 if session_minutes >= 90 else 5} if fatigued else None}
