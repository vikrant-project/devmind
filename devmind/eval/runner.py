"""Benchmark runner."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional
from .scorer import score_run
from ..core.agent import Agent
from ..utils.logger import log


BENCH_DIR = Path(__file__).resolve().parent / "benchmarks"

MVP_SUITE = ["01_fibonacci.txt", "04_csv_converter.txt"]
FULL_SUITE = [
    "01_fibonacci.txt", "02_todo_api.txt", "03_portfolio_site.txt",
    "04_csv_converter.txt", "05_hn_scraper.txt", "06_auth_api.txt",
    "07_discord_bot.txt", "08_docker_app.txt",
]


def run_benchmarks(suite: str = "mvp", output: Optional[Path] = None) -> dict:
    items = MVP_SUITE if suite == "mvp" else FULL_SUITE
    results = []
    agent = Agent(mode="autonomous", max_iterations=3)
    for fname in items:
        p = BENCH_DIR / fname
        if not p.exists():
            continue
        prompt = p.read_text(encoding="utf-8").strip()
        t0 = time.time()
        try:
            res = agent.build(prompt)
        except Exception as e:
            log(f"[BENCH] {fname} crashed: {e}", level="ERROR")
            res = {"status": "failed", "error": str(e)}
        elapsed = round(time.time() - t0, 2)
        score, breakdown = score_run(res)
        results.append({"benchmark": fname, "score": score, "breakdown": breakdown,
                        "status": res.get("status"), "elapsed": elapsed})
    total = sum(r["score"] for r in results) / max(len(results), 1)
    summary = {"suite": suite, "overall_score": round(total, 1), "results": results}
    out_path = output or Path("~/devmind/benchmark_results.json").expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    return summary
