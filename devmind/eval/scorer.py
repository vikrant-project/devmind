"""Benchmark scoring."""
from __future__ import annotations
from pathlib import Path


def score_run(res: dict) -> tuple[int, dict]:
    score = 0
    b = {}
    status = res.get("status", "failed")
    if status != "failed":
        score += 20; b["build_completes"] = 20
    plan = res.get("plan", {})
    files = plan.get("files", [])
    ws = Path(res.get("workspace", "")) if res.get("workspace") else None
    if ws and ws.exists() and files:
        gen = sum(1 for f in files if (ws / f.get("path", "")).exists())
        if gen == len(files):
            score += 10; b["all_files_generated"] = 10
    results = res.get("results", {})
    if results.get("run_ok"):
        score += 20; b["project_runs"] = 20
    if results.get("test_ok") or (results.get("tests_passed", 0) > 0 and results.get("tests_failed", 0) == 0):
        score += 20; b["tests_pass"] = 20
    review = results.get("review") or {}
    if not review.get("secrets"):
        score += 10; b["no_secrets"] = 10
    if not review.get("critical_issues"):
        score += 10; b["no_critical_issues"] = 10
    if ws and (ws / "README.md").exists() and (ws / "README.md").stat().st_size > 50:
        score += 5; b["readme"] = 5
    if results.get("zip") and Path(results["zip"]).exists() and Path(results["zip"]).stat().st_size > 0:
        score += 5; b["zip_valid"] = 5
    return score, b
