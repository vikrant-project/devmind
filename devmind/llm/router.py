"""Task → local model routing."""
from __future__ import annotations
from typing import Optional
from ..utils.logger import log
from .backends.base import LLMBackend, LLMResponse
from .model_manager import HardwareProfile, ModelRecord, select_model
from .resource_tracker import resource_tracker


class LLMRouter:
    def __init__(self, backend: LLMBackend, models: list[ModelRecord], hp: HardwareProfile):
        self.backend = backend
        self.models = models
        self.hp = hp
        self.assignments: dict[str, Optional[ModelRecord]] = {}
        self._warmed = set()
        for task in ("planning", "coding", "debug", "fix", "review", "doc", "test", "embedding"):
            chosen = select_model(models, task, hp)
            self.assignments[task] = chosen
            if chosen:
                log(f"[ROUTER] {task} -> {chosen.name} ({chosen.param_count_b}B, {chosen.backend})")
            else:
                log(f"[ROUTER] {task} -> NO MODEL AVAILABLE", level="WARN")

    def model_for(self, task: str) -> Optional[ModelRecord]:
        return self.assignments.get(task)

    def warmup(self, task: str) -> None:
        m = self.model_for(task)
        if not m or m.name in self._warmed:
            return
        try:
            r = self.backend.chat(m.name, [{"role": "user", "content": "OK"}],
                                  temperature=0.0, max_tokens=8, timeout=120)
            log(f"[ROUTER] Warmup {m.name}: {r.tokens_per_second:.2f} tok/s")
            self._warmed.add(m.name)
        except Exception as e:
            log(f"[ROUTER] Warmup failed for {m.name}: {e}", level="WARN")

    def call(self, task: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: Optional[int] = None, timeout: float = 600.0) -> LLMResponse:
        m = self.model_for(task)
        if m is None:
            raise RuntimeError(f"No model available for task '{task}'")
        prompt_chars = sum(len(x.get("content", "")) for x in messages)
        est_tokens = prompt_chars // 4
        util = est_tokens / max(m.context_window, 1) * 100
        log(f"[ROUTER] Task: {task.upper()} | Model: {m.name} | Ctx: ~{est_tokens}/{m.context_window} ({util:.0f}%)")
        resp = self.backend.chat(m.name, messages, temperature=temperature,
                                 max_tokens=max_tokens, timeout=timeout)
        resource_tracker.record(task=task, response=resp, context_window=m.context_window)
        return resp

    def embed(self, text: str) -> Optional[list[float]]:
        m = self.model_for("embedding")
        if not m:
            return None
        try:
            return self.backend.embed(m.name, text)
        except Exception as e:
            log(f"[ROUTER] Embedding failed: {e}", level="WARN")
            return None
