"""Sandbox: Docker (preferred) or subprocess fallback."""
from __future__ import annotations
import os
import resource
import shutil
import subprocess
from pathlib import Path
from ..config import settings
from ..tools.shell_tool import ShellResult
from ..utils.logger import log


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


class Sandbox:
    def __init__(self, workspace: Path, *, prefer: str = "docker",
                 network_required: bool = False, image: str = "python:3.11-slim"):
        self.workspace = workspace.resolve()
        self.network_required = network_required
        self.image = image
        if prefer == "docker" and _docker_available():
            self.level = 1
        else:
            self.level = 2
            if prefer == "docker":
                log("[SANDBOX] Docker unavailable; falling back to Level 2 subprocess sandbox", level="WARN")

    def exec(self, cmd: str, *, timeout: int = 120) -> ShellResult:
        if self.level == 1:
            return self._exec_docker(cmd, timeout)
        return self._exec_subprocess(cmd, timeout)

    def _exec_docker(self, cmd: str, timeout: int) -> ShellResult:
        net = "bridge" if self.network_required else "none"
        full = [
            "docker", "run", "--rm",
            f"--cpus={settings.DEVMIND_SANDBOX_CPU}",
            f"--memory={settings.DEVMIND_SANDBOX_MEMORY}",
            f"--memory-swap={settings.DEVMIND_SANDBOX_MEMORY}",
            "--pids-limit=256", "--security-opt=no-new-privileges",
            f"--network={net}",
            "-v", f"{self.workspace}:/work", "-w", "/work",
            self.image, "bash", "-lc", cmd,
        ]
        try:
            r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
            return ShellResult(cmd=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except subprocess.TimeoutExpired as e:
            return ShellResult(cmd=cmd, returncode=124, stdout=e.stdout or "", stderr=e.stderr or "", timed_out=True)
        except Exception as e:
            return ShellResult(cmd=cmd, returncode=1, stdout="", stderr=str(e))

    def _exec_subprocess(self, cmd: str, timeout: int) -> ShellResult:
        log("[SANDBOX] WARNING: Level 2 (subprocess) sandbox in use")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "HOME": str(self.workspace), "LANG": "C.UTF-8"}

        def _limit():
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 5))
                resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
                resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
            except Exception:
                pass

        try:
            r = subprocess.run(
                cmd, shell=True, cwd=str(self.workspace), env=env,
                capture_output=True, text=True, timeout=timeout, preexec_fn=_limit,
            )
            return ShellResult(cmd=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except subprocess.TimeoutExpired as e:
            return ShellResult(cmd=cmd, returncode=124, stdout=e.stdout or "", stderr=e.stderr or "", timed_out=True)
        except Exception as e:
            return ShellResult(cmd=cmd, returncode=1, stdout="", stderr=str(e))
