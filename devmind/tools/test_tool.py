"""Run tests and parse results."""
from __future__ import annotations
import re
from pathlib import Path
from .shell_tool import ShellTool, ShellResult


class TestTool:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sh = ShellTool(workspace)

    def run_pytest(self) -> tuple[ShellResult, int, int]:
        r = self.sh.run("pytest -v --tb=short -q 2>&1 || true", timeout=180)
        passed = failed = 0
        for line in (r.stdout + r.stderr).splitlines():
            m = re.search(r"(\d+)\s+passed", line)
            if m: passed = max(passed, int(m.group(1)))
            m = re.search(r"(\d+)\s+failed", line)
            if m: failed = max(failed, int(m.group(1)))
        return r, passed, failed

    def run_cmd(self, cmd: str, timeout: int = 120) -> ShellResult:
        return self.sh.run(cmd, timeout=timeout)
