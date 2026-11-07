import httpx, re
from .config import OPENROUTER_API_KEY, OPENROUTER_MODEL

def llm_available() -> bool:
    return bool(OPENROUTER_API_KEY)

def chat(system: str, user: str, temperature: float = 0.3) -> str | None:
    """Returns model text, or None when offline (callers use deterministic fallbacks)."""
    if not llm_available():
        return None
    try:
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={"model": OPENROUTER_MODEL, "temperature": temperature,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=90)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None

def extractive_summary(text: str, n: int = 6) -> list[str]:
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 5]
    return sents[:n]
