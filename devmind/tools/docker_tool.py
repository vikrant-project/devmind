"""Docker availability + build helpers."""
from __future__ import annotations
import shutil
import subprocess


class DockerTool:
    @staticmethod
    def available() -> bool:
        if not shutil.which("docker"):
            return False
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False
