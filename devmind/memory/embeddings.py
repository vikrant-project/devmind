"""Local embeddings + simple vector store (SQLite + cosine in Python)."""
from __future__ import annotations
import json
import math
import sqlite3
from typing import Optional
from ..utils.helpers import new_id
from ..utils.logger import log


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = sum(x*y for x, y in zip(a, b))
    da = math.sqrt(sum(x*x for x in a))
    db = math.sqrt(sum(x*x for x in b))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def _tfidf_keyset(text: str) -> set:
    return {w.lower() for w in (text or "").split() if len(w) > 3}


class VectorStore:
    """Embeddings store; falls back to TF-IDF if no embedder is available."""
    def __init__(self, db_path, router=None):
        self.db_path = str(db_path)
        self.router = router
        self.conn = sqlite3.connect(self.db_path)
        self._available_check_done = False
        self._embedding_available = False

    def _embed(self, text: str) -> Optional[list[float]]:
        if self.router is None:
            return None
        try:
            return self.router.embed(text)
        except Exception:
            return None

    def add(self, source_table: str, source_id: str, text: str) -> str:
        vid = new_id("v_")
        vec = self._embed(text)
        self.conn.execute(
            "INSERT INTO embeddings VALUES (?,?,?,?,?,datetime('now'))",
            (vid, source_table, source_id, text[:2000], json.dumps(vec) if vec else "[]"),
        )
        self.conn.commit()
        return vid

    def search(self, query: str, source_table: str, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            "SELECT source_id, text, vector_json FROM embeddings WHERE source_table=?",
            (source_table,),
        ).fetchall()
        if not rows:
            return []
        q_vec = self._embed(query)
        if q_vec:
            scored = []
            for sid, text, vj in rows:
                try:
                    v = json.loads(vj) if vj else []
                except Exception:
                    v = []
                if v:
                    scored.append((_cosine(q_vec, v), sid, text))
            scored.sort(reverse=True)
            return [{"id": s, "text": t, "score": sc} for sc, s, t in scored[:limit]]
        # TF-IDF fallback
        qset = _tfidf_keyset(query)
        scored = []
        for sid, text, _ in rows:
            score = len(qset & _tfidf_keyset(text))
            if score:
                scored.append((score, sid, text))
        scored.sort(reverse=True)
        return [{"id": s, "text": t, "score": float(sc)} for sc, s, t in scored[:limit]]
