"""Test runner module."""
from __future__ import annotations
from pathlib import Path
from ..tools.test_tool import TestTool


def run_project_tests(workspace: Path, plan: dict) -> tuple[bool, int, int, str]:
    cmd = (plan.get("test_command") or "").strip()
    tt = TestTool(workspace)
    if not cmd:
        return True, 0, 0, "no tests configured"
    if cmd.startswith("pytest"):
        r, p, f = tt.run_pytest()
        return f == 0, p, f, (r.stdout + r.stderr)[-2000:]
    r = tt.run_cmd(cmd)
    return r.ok, 0, 0, (r.stdout + r.stderr)[-2000:]
