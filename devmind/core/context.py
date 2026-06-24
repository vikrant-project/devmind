"""Session context (short-term memory wrapper)."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SessionContext:
    session_id: str
    prompt: str = ""
    plan: dict = field(default_factory=dict)
    workspace: Optional[Path] = None
    file_index: dict = field(default_factory=dict)  # path -> description
    error_history: list = field(default_factory=list)  # list of {file, error, fix}
    exchange_buffer: list = field(default_factory=list)  # rolling LLM exchanges
    project_summary: str = ""
    mode: str = "autonomous"
    max_iterations: int = 5

    def add_exchange(self, role: str, content: str) -> None:
        self.exchange_buffer.append({"role": role, "content": content[:8000]})
        if len(self.exchange_buffer) > 30:
            self.exchange_buffer = self.exchange_buffer[-30:]

    def record_error(self, file: str, error: str, fix: str = "") -> None:
        self.error_history.append({"file": file, "error": error[:2000], "fix": fix[:2000]})
