"""SQLite long-term memory."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import settings
from ..utils.helpers import new_id, sha1
from ..utils.logger import log


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY, session_id TEXT, prompt_summary TEXT, project_type TEXT,
    tech_stack_json TEXT, status TEXT, files_created INTEGER, tests_passed INTEGER,
    tests_failed INTEGER, iterations_used INTEGER, total_tokens INTEGER,
    peak_ram_mb INTEGER, total_inference_seconds REAL, created_at TEXT, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS error_patterns (
    id TEXT PRIMARY KEY, error_signature TEXT, error_description TEXT,
    fix_description TEXT, worked INTEGER, project_id TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS learned_patterns (
    id TEXT PRIMARY KEY, project_type TEXT, tech_stack_json TEXT,
    success_rate REAL, sample_count INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS model_performance (
    id TEXT PRIMARY KEY, model_name TEXT, task_type TEXT,
    avg_tokens_per_second REAL, avg_quality_score REAL,
    sample_count INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY, source_table TEXT, source_id TEXT,
    text TEXT, vector_json TEXT, created_at TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LongTermMemory:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.memory_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def record_project(self, *, session_id: str, prompt: str, project_type: str,
                       tech_stack: list, status: str, files_created: int,
                       tests_passed: int, tests_failed: int, iterations: int,
                       total_tokens: int, peak_ram_mb: float,
                       total_inference_seconds: float) -> str:
        pid = new_id("p_")
        self.conn.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, session_id, prompt[:300], project_type, json.dumps(tech_stack),
             status, files_created, tests_passed, tests_failed, iterations,
             total_tokens, int(peak_ram_mb), total_inference_seconds, _now(), _now()),
        )
        self.conn.commit()
        return pid

    def record_error_pattern(self, *, error_desc: str, fix_desc: str, worked: bool,
                             project_id: str, file_ext: str = "") -> None:
        sig = sha1(f"{error_desc.splitlines()[0][:200]}::{file_ext}")
        self.conn.execute(
            "INSERT INTO error_patterns VALUES (?,?,?,?,?,?,?)",
            (new_id("e_"), sig, error_desc[:500], fix_desc[:500],
             1 if worked else 0, project_id, _now()),
        )
        self.conn.commit()

    def record_model_perf(self, *, model: str, task: str, tps: float, quality: float) -> None:
        row = self.conn.execute(
            "SELECT id, avg_tokens_per_second, avg_quality_score, sample_count "
            "FROM model_performance WHERE model_name=? AND task_type=?",
            (model, task),
        ).fetchone()
        if row:
            mid, atps, aq, n = row
            n2 = n + 1
            new_tps = (atps * n + tps) / n2
            new_q = (aq * n + quality) / n2
            self.conn.execute(
                "UPDATE model_performance SET avg_tokens_per_second=?, avg_quality_score=?, "
                "sample_count=?, updated_at=? WHERE id=?",
                (new_tps, new_q, n2, _now(), mid),
            )
        else:
            self.conn.execute(
                "INSERT INTO model_performance VALUES (?,?,?,?,?,?,?)",
                (new_id("m_"), model, task, tps, quality, 1, _now()),
            )
        self.conn.commit()

    def find_similar_projects(self, prompt: str, limit: int = 3) -> list[dict]:
        words = set(w.lower() for w in prompt.split() if len(w) > 3)
        rows = self.conn.execute(
            "SELECT id, prompt_summary, project_type, status FROM projects "
            "ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        scored = []
        for r in rows:
            text_words = set(w.lower() for w in (r[1] or "").split() if len(w) > 3)
            score = len(words & text_words)
            if score:
                scored.append((score, r))
        scored.sort(reverse=True)
        out = []
        for _, r in scored[:limit]:
            out.append({"id": r[0], "prompt": r[1], "type": r[2], "status": r[3]})
        if out:
            log(f"[MEMORY] Found {len(out)} similar past projects")
        return out

    def find_similar_errors(self, error: str, limit: int = 5) -> list[dict]:
        sig = sha1(error.splitlines()[0][:200] if error else "")
        rows = self.conn.execute(
            "SELECT error_description, fix_description, worked FROM error_patterns "
            "WHERE error_signature=? AND worked=1 ORDER BY created_at DESC LIMIT ?",
            (sig, limit),
        ).fetchall()
        return [{"error": r[0], "fix": r[1], "worked": bool(r[2])} for r in rows]

    def list_projects(self, status: str = "all") -> list[dict]:
        q = "SELECT id, prompt_summary, project_type, status, created_at FROM projects"
        params: tuple = ()
        if status != "all":
            q += " WHERE status=?"
            params = (status,)
        q += " ORDER BY created_at DESC LIMIT 50"
        return [{"id": r[0], "prompt": r[1], "type": r[2], "status": r[3], "at": r[4]}
                for r in self.conn.execute(q, params).fetchall()]
