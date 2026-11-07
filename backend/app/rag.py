"""Hybrid retrieval: BM25 (lexical) + cosine over hashed embeddings (semantic), fused with
Reciprocal Rank Fusion, then a lightweight reranker. Top-k context cuts prompt tokens vs
stuffing whole documents."""
import math, re, hashlib
from collections import Counter

_TOK = re.compile(r"[a-z0-9]+")
STOP = set("the a an of and or to in is are was for on with as by at from that this it be".split())
def tokenize(t): return [w for w in _TOK.findall(t.lower()) if w not in STOP]

def chunk_text(text: str, size=180, overlap=30) -> list[str]:
    w = text.split(); out = []; i = 0
    while i < len(w):
        out.append(" ".join(w[i:i + size])); i += size - overlap
    return [c for c in out if len(c.split()) > 8]

def embed(text: str, dim=256) -> list[float]:
    """Offline hashing-trick embedding (unigrams+bigrams). Swap for a hosted model in prod."""
    v = [0.0] * dim; toks = tokenize(text)
    for t in toks + [a + "_" + b for a, b in zip(toks, toks[1:])]:
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        v[h % dim] += 1.0 if (h >> 64) % 2 == 0 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]

def cosine(a, b): return sum(x * y for x, y in zip(a, b))

def bm25(query: str, docs: list[str], k1=1.5, b=0.75) -> list[float]:
    toks = [tokenize(d) for d in docs]; N = len(docs) or 1
    avg = sum(map(len, toks)) / N or 1
    df = Counter(t for d in toks for t in set(d))
    scores = []
    for d in toks:
        tf = Counter(d); s = 0.0
        for q in set(tokenize(query)):
            if q in tf:
                idf = math.log(1 + (N - df[q] + .5) / (df[q] + .5))
                s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(d) / avg))
        scores.append(s)
    return scores

def hybrid_search(query: str, chunks: list[dict], k=5) -> list[dict]:
    """chunks: [{'id','text','embedding'}]"""
    if not chunks: return []
    lex = bm25(query, [c["text"] for c in chunks])
    qe = embed(query); sem = [cosine(qe, c["embedding"]) for c in chunks]
    def ranks(s): return {i: r for r, i in enumerate(sorted(range(len(s)), key=lambda i: -s[i]))}
    rl, rs = ranks(lex), ranks(sem)
    fused = {i: 1 / (60 + rl[i]) + 1 / (60 + rs[i]) for i in range(len(chunks))}
    cand = sorted(fused, key=lambda i: -fused[i])[:max(k * 3, k)]
    qt = set(tokenize(query))
    def rerank(i):  # coverage of query terms + fused score
        ct = set(tokenize(chunks[i]["text"]))
        return fused[i] * 60 + (len(qt & ct) / (len(qt) or 1))
    top = sorted(cand, key=lambda i: -rerank(i))[:k]
    return [{**chunks[i], "score": round(rerank(i), 4)} for i in top]
