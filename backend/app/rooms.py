"""Stateful WebSocket War Rooms: pooled notes, co-edited flashcards, AI-moderated trivia."""
import json
from fastapi import WebSocket
from .llm import chat
from .exam import grade

class Room:
    def __init__(self):
        self.clients: dict[WebSocket, str] = {}
        self.notes: list[dict] = []; self.cards: list[dict] = []
        self.trivia: dict | None = None; self.scores: dict[str, int] = {}

class RoomManager:
    def __init__(self): self.rooms: dict[str, Room] = {}
    def room(self, name): return self.rooms.setdefault(name, Room())

    async def broadcast(self, r: Room, msg: dict):
        for ws in list(r.clients):
            try: await ws.send_json(msg)
            except Exception: r.clients.pop(ws, None)

    async def join(self, name: str, ws: WebSocket, user: str):
        await ws.accept(); r = self.room(name); r.clients[ws] = user
        await ws.send_json({"type": "state", "notes": r.notes, "cards": r.cards, "scores": r.scores, "trivia": r.trivia and r.trivia["q"]})
        await self.broadcast(r, {"type": "presence", "users": list(r.clients.values())})

    async def leave(self, name: str, ws: WebSocket):
        r = self.room(name); r.clients.pop(ws, None)
        await self.broadcast(r, {"type": "presence", "users": list(r.clients.values())})

    async def handle(self, name: str, ws: WebSocket, user: str, m: dict):
        r = self.room(name); t = m.get("type")
        if t == "note":
            r.notes.append({"user": user, "text": m["text"]}); await self.broadcast(r, {"type": "note", "user": user, "text": m["text"]})
        elif t == "card":
            c = {"front": m["front"], "back": m["back"], "by": user}; r.cards.append(c); await self.broadcast(r, {"type": "card", **c})
        elif t == "card_edit" and 0 <= m.get("index", -1) < len(r.cards):
            r.cards[m["index"]].update(front=m["front"], back=m["back"]); await self.broadcast(r, {"type": "cards", "cards": r.cards})
        elif t == "trivia_start":
            ctx = "\n".join(n["text"] for n in r.notes[-10:]) or m.get("topic", "general study skills")
            out = chat("Ask ONE short trivia question about the material. Reply as JSON {\"q\":..,\"a\":..}.", ctx)
            try:
                r.trivia = json.loads(out)
            except Exception:
                r.trivia = {"q": f"Name one key idea from the notes pooled so far ({len(r.notes)} notes).", "a": ctx.split()[0] if ctx else "study"}
            await self.broadcast(r, {"type": "trivia", "q": r.trivia["q"]})
        elif t == "trivia_answer" and r.trivia:
            ok = grade(m["answer"], r.trivia["a"]) >= .5
            if ok:
                r.scores[user] = r.scores.get(user, 0) + 10
                await self.broadcast(r, {"type": "trivia_result", "winner": user, "answer": r.trivia["a"], "scores": r.scores}); r.trivia = None
            else:
                await ws.send_json({"type": "trivia_wrong"})

manager = RoomManager()
