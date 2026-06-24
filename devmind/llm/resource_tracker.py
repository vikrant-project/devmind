"""Per-call & per-session resource tracking (no API costs in V3)."""
from __future__ import annotations
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import psutil

from ..utils.logger import log
from .backends.base import LLMResponse


def _vram_mb() -> float:
    if not shutil.which("nvidia-smi"):
        return 0.0
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            return float(r.stdout.strip().splitlines()[0])
    except Exception:
        pass
    return 0.0


@dataclass
class CallStat:
    timestamp: float
    task: str
    model: str
    backend: str
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    tokens_per_second: float
    elapsed_seconds: float
    ram_before_mb: float
    ram_after_mb: float
    vram_before_mb: float
    vram_after_mb: float
    cpu_pct: float
    context_window: int
    context_utilization_pct: float


@dataclass
class SessionStats:
    total_tokens: int = 0
    total_inference_seconds: float = 0.0
    peak_ram_mb: float = 0.0
    peak_vram_mb: float = 0.0
    pressure_events: int = 0
    slowest_call: dict = field(default_factory=dict)
    calls: list[CallStat] = field(default_factory=list)
    external_api_calls: int = 0  # always 0


class ResourceTracker:
    def __init__(self) -> None:
        self.stats = SessionStats()
        self._workspace_log: Optional[Path] = None
        self._proc = psutil.Process()
        self._last_ram_before = 0.0
        self._last_vram_before = 0.0

    def attach_workspace(self, workspace: Path) -> None:
        self._workspace_log = workspace / ".devmind_resources.jsonl"
        self._workspace_log.parent.mkdir(parents=True, exist_ok=True)
        self._workspace_log.touch(exist_ok=True)

    def mark_before(self) -> None:
        self._last_ram_before = self._proc.memory_info().rss / (1024**2)
        self._last_vram_before = _vram_mb()

    def record(self, *, task: str, response: LLMResponse, context_window: int) -> CallStat:
        ram_after = self._proc.memory_info().rss / (1024**2)
        vram_after = _vram_mb()
        cpu = self._proc.cpu_percent(interval=None)
        util = (response.total_tokens / max(context_window, 1)) * 100.0
        stat = CallStat(
            timestamp=time.time(), task=task, model=response.model, backend=response.backend,
            prompt_tokens=response.prompt_tokens, output_tokens=response.output_tokens,
            total_tokens=response.total_tokens, tokens_per_second=response.tokens_per_second,
            elapsed_seconds=response.elapsed_seconds,
            ram_before_mb=self._last_ram_before, ram_after_mb=ram_after,
            vram_before_mb=self._last_vram_before, vram_after_mb=vram_after,
            cpu_pct=cpu, context_window=context_window, context_utilization_pct=util,
        )
        self.stats.calls.append(stat)
        self.stats.total_tokens += stat.total_tokens
        self.stats.total_inference_seconds += stat.elapsed_seconds
        self.stats.peak_ram_mb = max(self.stats.peak_ram_mb, ram_after)
        self.stats.peak_vram_mb = max(self.stats.peak_vram_mb, vram_after)
        if util > 80.0:
            self.stats.pressure_events += 1
            log(f"[RESOURCE] Context pressure: {util:.0f}% on {response.model}", level="WARN")
        if not self.stats.slowest_call or stat.elapsed_seconds > self.stats.slowest_call.get("elapsed_seconds", 0):
            self.stats.slowest_call = {"task": task, "model": response.model,
                                       "elapsed_seconds": stat.elapsed_seconds}
        if stat.tokens_per_second and stat.tokens_per_second < 1.0:
            log(f"[RESOURCE] Slow inference: {stat.tokens_per_second:.2f} tok/s — model may be too large",
                level="WARN")
        if self._workspace_log:
            try:
                with self._workspace_log.open("a") as f:
                    f.write(json.dumps(asdict(stat)) + "\n")
            except Exception:
                pass
        return stat

    def summary(self) -> dict:
        n = max(len(self.stats.calls), 1)
        avg_tps = sum(c.tokens_per_second for c in self.stats.calls) / n
        return {
            "total_tokens": self.stats.total_tokens,
            "avg_tokens_per_second": round(avg_tps, 2),
            "peak_ram_mb": round(self.stats.peak_ram_mb, 1),
            "peak_vram_mb": round(self.stats.peak_vram_mb, 1),
            "total_inference_seconds": round(self.stats.total_inference_seconds, 2),
            "calls": len(self.stats.calls),
            "context_pressure_events": self.stats.pressure_events,
            "slowest_call": self.stats.slowest_call,
            "external_api_calls": 0,
        }


resource_tracker = ResourceTracker()
