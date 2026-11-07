"""Spaced repetition. SM-2 (SuperMemo-2) scheduling; quality 0-5."""
import datetime as dt

def sm2(ease: float, interval: int, reps: int, quality: int):
    quality = max(0, min(5, quality))
    if quality < 3:
        reps, interval = 0, 1
    else:
        interval = 1 if reps == 0 else 6 if reps == 1 else round(interval * ease)
        reps += 1
    ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return round(ease, 3), interval, reps, dt.datetime.utcnow() + dt.timedelta(days=interval)
