"""Agent state machine with persistence and resume."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from ..utils.helpers import safe_write_json, read_json
from ..utils.logger import log


class State(str, Enum):
    IDLE = "IDLE"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    BUILD = "BUILD"
    RUN = "RUN"
    TEST = "TEST"
    DEBUG = "DEBUG"
    FIX = "FIX"
    REVIEW = "REVIEW"
    DOCUMENT = "DOCUMENT"
    EXPORT = "EXPORT"
    COMPLETE = "COMPLETE"
    REPORT_FAILURE = "REPORT_FAILURE"


@dataclass
class StateRecord:
    session_id: str
    current_state: str = State.IDLE.value
    completed_states: list = field(default_factory=list)
    iteration_count: int = 0
    files_generated: list = field(default_factory=list)
    last_error: str = ""
    model_used_per_state: dict = field(default_factory=dict)
    timestamps: dict = field(default_factory=dict)


class StateMachine:
    def __init__(self, workspace: Path, session_id: str):
        self.workspace = workspace
        self.path = workspace / ".devmind_state.json"
        existing = read_json(self.path, None)
        if existing:
            self.record = StateRecord(**{k: existing.get(k, v) for k, v in asdict(StateRecord(session_id=session_id)).items()})
        else:
            self.record = StateRecord(session_id=session_id)
        self._persist()

    @property
    def current(self) -> State:
        return State(self.record.current_state)

    def _persist(self) -> None:
        safe_write_json(self.path, asdict(self.record))

    def enter(self, state: State, *, model: Optional[str] = None) -> None:
        if self.record.current_state and self.record.current_state != State.IDLE.value \
                and self.record.current_state not in self.record.completed_states:
            self.record.completed_states.append(self.record.current_state)
        self.record.current_state = state.value
        self.record.timestamps[state.value] = datetime.now(timezone.utc).isoformat()
        if model:
            self.record.model_used_per_state[state.value] = model
        log(f"[STATE] -> {state.value}")
        self._persist()

    def set_error(self, err: str) -> None:
        self.record.last_error = err[:2000]
        self._persist()

    def add_file(self, path: str) -> None:
        if path not in self.record.files_generated:
            self.record.files_generated.append(path)
            self._persist()

    def bump_iteration(self) -> None:
        self.record.iteration_count += 1
        self._persist()

    def resume_target(self) -> Optional[State]:
        """Where should we resume? After last completed state."""
        if not self.record.completed_states:
            return None
        order = [s.value for s in State]
        try:
            last = self.record.completed_states[-1]
            idx = order.index(last)
            if idx + 1 < len(order):
                return State(order[idx + 1])
        except (ValueError, IndexError):
            pass
        return None
