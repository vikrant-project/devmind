"""Git operations in workspace."""
from __future__ import annotations
from pathlib import Path
from .shell_tool import ShellTool


class GitTool:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sh = ShellTool(workspace)

    def init(self) -> bool:
        return self.sh.run("git init -q && git config user.email devmind@local && git config user.name DevMind").ok

    def commit_all(self, message: str) -> bool:
        self.sh.run("git add -A")
        r = self.sh.run(f"git commit -m {self._quote(message)} --allow-empty -q")
        return r.ok

    @staticmethod
    def _quote(s: str) -> str:
        return "'" + s.replace("'", "'\"'\"'") + "'"
