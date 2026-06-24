"""Safe shell exec — blocklist enforced, workspace-scoped cwd."""
from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..core.safety import check_shell
from ..utils.logger import log


@dataclass
class ShellResult:
    cmd: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class ShellTool:
    def __init__(self, workspace: Path, env: dict | None = None):
        self.workspace = workspace.resolve()
        self.env = env or {}

    def run(self, cmd: str, *, timeout: int = 120, shell: bool = True, extra_env: dict | None = None) -> ShellResult:
        decision = check_shell(cmd)
        if not decision.allowed:
            log(f"[SHELL] BLOCKED: {cmd} -- {decision.reason}", level="ERROR")
            return ShellResult(cmd=cmd, returncode=126, stdout="", stderr=f"blocked: {decision.reason}")
        env = os.environ.copy()
        env.update(self.env)
        if extra_env:
            env.update(extra_env)
        try:
            r = subprocess.run(
                cmd if shell else cmd.split(),
                cwd=str(self.workspace), shell=shell, capture_output=True, text=True,
                timeout=timeout, env=env,
            )
            return ShellResult(cmd=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except subprocess.TimeoutExpired as e:
            return ShellResult(cmd=cmd, returncode=124, stdout=e.stdout or "", stderr=e.stderr or "",
                               timed_out=True)
        except Exception as e:
            return ShellResult(cmd=cmd, returncode=1, stdout="", stderr=str(e))
