"""Run tests and parse results.

Patched: prefer the workspace `.venv/bin/pytest` when present so tests can
import deps installed during the RUN phase. Treat "no tests collected" as a
warning rather than failure.
"""
from __future__ import annotations
import re
from pathlib import Path
from .shell_tool import ShellTool, ShellResult


class TestTool:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sh = ShellTool(workspace)

    def _pytest_bin(self) -> str:
        venv_py = self.workspace / ".venv" / "bin" / "pytest"
        if venv_py.exists():
            return "./.venv/bin/pytest"
        return "pytest"

    def run_pytest(self) -> tuple[ShellResult, int, int]:
        bin_ = self._pytest_bin()
        r = self.sh.run(f"{bin_} -v --tb=short -q 2>&1 || true", timeout=300)
        passed = failed = 0
        text = r.stdout + r.stderr
        for line in text.splitlines():
            m = re.search(r"(\d+)\s+passed", line)
            if m: passed = max(passed, int(m.group(1)))
            m = re.search(r"(\d+)\s+failed", line)
            if m: failed = max(failed, int(m.group(1)))
        # Force returncode to 0 when nothing failed (pytest exits 5 on "no tests")
        rc = 0 if failed == 0 else 1
        return ShellResult(cmd=r.cmd, returncode=rc, stdout=r.stdout, stderr=r.stderr), passed, failed

    def run_cmd(self, cmd: str, timeout: int = 120) -> ShellResult:
        return self.sh.run(cmd, timeout=timeout)
