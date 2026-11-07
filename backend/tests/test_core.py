import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.rag import embed, hybrid_search
from app.srs import sm2
from app.syllabus import map_weightage
from app.exam import timing_report
from app.wellness import check

def test_hybrid_search_finds_relevant():
    docs = ["Mitochondria produce ATP through oxidative phosphorylation in the cell membrane layers " * 2,
            "The French revolution began in 1789 with the storming of the Bastille by angry crowds " * 2]
    ch = [{"id": i, "text": d, "embedding": embed(d)} for i, d in enumerate(docs)]
    assert hybrid_search("how do mitochondria make ATP", ch, 1)[0]["id"] == 0

def test_sm2_progression():
    e, i, r, _ = sm2(2.5, 0, 0, 5); assert i == 1
    e, i, r, _ = sm2(e, i, r, 5); assert i == 6
    assert sm2(e, i, r, 1)[1] == 1

def test_syllabus():
    out = map_weightage(["binary trees", "graph traversal"], ["1. Explain binary trees (10 marks)\n2. Describe binary trees insertion (5 marks)\n3. graph traversal BFS (5 marks)"])
    assert out[0]["topic"] == "binary trees" and out[0]["mark_weight_pct"] > 50

def test_timing_and_wellness():
    qs = [{"q": "a", "answer": "alpha", "marks": 5}, {"q": "b", "answer": "beta", "marks": 5}]
    r = timing_report(qs, [{"index": 0, "answer": "alpha", "seconds": 60}, {"index": 1, "answer": "x", "seconds": 500}], 10)
    assert r["time_wasted_s"] > 0
    ev = [{"correct": True, "seconds": 10}] * 5 + [{"correct": False, "seconds": 30}] * 5
    assert check(ev, 40)["break"]
