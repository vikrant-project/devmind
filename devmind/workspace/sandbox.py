"""Sandbox: Docker (preferred) or subprocess fallback.

Patched:
- Subprocess sandbox preserves a useful env (full PATH, real HOME for pip
  cache, http(s)_proxy if set) so pip/npm work as expected.
- Auto-detects install commands and enables outbound network for them when
  using Docker.
"""
from __future__ import annotations
import os
import re
import resource
import shutil
import subprocess
from pathlib import Path
from ..config import settings
from ..tools.shell_tool import ShellResult
from ..utils.logger import log


_INSTALL_RE = re.compile(
    r"\b(pip3?\s+install|npm\s+(install|i|ci)|yarn\s+(add|install)|"
    r"pnpm\s+(add|install)|go\s+(get|install|mod\s+download)|"
    r"cargo\s+(build|fetch|install)|apt(-get)?\s+install|"
    r"poetry\s+(install|add)|uv\s+(pip\s+install|sync|add)|gem\s+install|"
    r"bundle\s+install|\.venv/bin/pip\s+install|python3?\s+-m\s+venv)\b",
    re.IGNORECASE,
)


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _needs_network(cmd: str) -> bool:
    return bool(_INSTALL_RE.search(cmd or ""))


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
        # Allow network for install commands even if the plan didn't request it.
        net = "bridge" if (self.network_required or _needs_network(cmd)) else "none"
        uid = os.getuid()
        gid = os.getgid()
        full = [
            "docker", "run", "--rm",
            f"--cpus={settings.DEVMIND_SANDBOX_CPU}",
            f"--memory={settings.DEVMIND_SANDBOX_MEMORY}",
            f"--memory-swap={settings.DEVMIND_SANDBOX_MEMORY}",
            "--pids-limit=256", "--security-opt=no-new-privileges",
            f"--network={net}",
            f"--user={uid}:{gid}",
            "-e", "HOME=/tmp",
            "-v", f"{self.workspace}:/work", "-w", "/work",
            self.image, "bash", "-lc", cmd,
        ]
        try:
            r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
            return ShellResult(cmd=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except subprocess.TimeoutExpired as e:
            return ShellResult(cmd=cmd, returncode=124, stdout=e.stdout or "",
                               stderr=e.stderr or "", timed_out=True)
        except Exception as e:
            return ShellResult(cmd=cmd, returncode=1, stdout="", stderr=str(e))

    def _exec_subprocess(self, cmd: str, timeout: int) -> ShellResult:
        log("[SANDBOX] WARNING: Level 2 (subprocess) sandbox in use")
        # Preserve a functional env: real HOME (so pip cache + ~/.config work),
        # full PATH, proxy vars, and locale. Do not pass arbitrary secrets.
        base_path = os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
        env = {
            "PATH": base_path,
            "HOME": os.environ.get("HOME", str(self.workspace)),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "TERM": os.environ.get("TERM", "xterm"),
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
                  "http_proxy", "https_proxy", "no_proxy", "SSL_CERT_FILE",
                  "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
            if k in os.environ:
                env[k] = os.environ[k]

        def _limit():
            # CPU limit only — RLIMIT_AS and RLIMIT_NPROC frequently kill
            # legitimate operations (pip ensurepip, parallel compilers,
            # background threads) on shared hosts and provide little real
            # security in subprocess mode. Use Docker sandbox for hard limits.
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (timeout + 30, timeout + 60))
            except Exception:
                pass

        try:
            r = subprocess.run(
                cmd, shell=True, cwd=str(self.workspace), env=env,
                capture_output=True, text=True, timeout=timeout, preexec_fn=_limit,
            )
            return ShellResult(cmd=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except subprocess.TimeoutExpired as e:
            return ShellResult(cmd=cmd, returncode=124, stdout=e.stdout or "",
                               stderr=e.stderr or "", timed_out=True)
        except Exception as e:
            return ShellResult(cmd=cmd, returncode=1, stdout="", stderr=str(e))
