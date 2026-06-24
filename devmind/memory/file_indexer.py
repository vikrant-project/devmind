"""Workspace file indexer."""
from __future__ import annotations
from pathlib import Path
from typing import Optional


class FileIndexer:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.entries: dict[str, dict] = {}

    def refresh(self) -> None:
        self.entries.clear()
        for p in self.workspace.rglob("*"):
            if not p.is_file() or ".devmind_" in p.name or ".git/" in str(p):
                continue
            rel = str(p.relative_to(self.workspace))
            try:
                stat = p.stat()
                self.entries[rel] = {
                    "size": stat.st_size, "mtime": stat.st_mtime,
                    "token_estimate": stat.st_size // 4,
                }
            except Exception:
                continue

    def get_file(self, rel: str) -> Optional[str]:
        p = self.workspace / rel
        if p.exists() and p.is_file():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def list_with_descriptions(self, plan: dict) -> dict:
        out = {}
        for f in plan.get("files", []) or []:
            out[f.get("path", "")] = f.get("purpose", "")
        for k in self.entries:
            if k not in out:
                out[k] = "(generated)"
        return out
