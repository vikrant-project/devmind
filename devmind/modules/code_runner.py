"""Install deps + run project in sandbox.

For static web frontends (HTML/CSS/JS only) we never try to exec the run
command (which is usually natural language like 'Open index.html in a browser').
Instead we validate the workspace: index.html exists and parses, all planned
files exist. This avoids futile RUN -> DEBUG -> FIX loops for static projects.
"""
from __future__ import annotations
import re
from html.parser import HTMLParser
from pathlib import Path

from ..tools.shell_tool import ShellResult
from ..workspace.sandbox import Sandbox
from ..utils.logger import log


_BROWSER_PHRASES = re.compile(
    r"\b(open\s+.+\s+in\s+.*browser|open\s+in\s+browser|visit\s+http|"
    r"navigate\s+to|double[- ]click|launch\s+browser|view\s+in\s+browser)\b",
    re.IGNORECASE,
)
_STATIC_TYPES = {"web_frontend", "static_site", "html", "frontend"}


class _HTMLChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []
        self.saw_html = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag == "html":
            self.saw_html = True

    def error(self, message: str) -> None:  # type: ignore[override]
        self.errors.append(message)


def _validate_static_site(workspace: Path, plan: dict) -> ShellResult:
    """Validate a static site without executing anything."""
    missing: list[str] = []
    for entry in plan.get("files", []) or []:
        rel = entry.get("path", "")
        if rel and not (workspace / rel).exists():
            missing.append(rel)
    index = workspace / "index.html"
    if not index.exists():
        # try any .html
        htmls = list(workspace.glob("**/*.html"))
        if not htmls:
            return ShellResult(
                cmd="<static-validate>",
                returncode=1,
                stdout="",
                stderr="No HTML file found in workspace",
            )
        index = htmls[0]
    try:
        html_text = index.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return ShellResult(
            cmd="<static-validate>", returncode=1, stdout="", stderr=f"cannot read {index}: {e}"
        )
    checker = _HTMLChecker()
    try:
        checker.feed(html_text)
        checker.close()
    except Exception as e:
        return ShellResult(
            cmd="<static-validate>", returncode=1, stdout="", stderr=f"HTML parse error: {e}"
        )
    if missing:
        return ShellResult(
            cmd="<static-validate>",
            returncode=1,
            stdout="",
            stderr=f"missing planned files: {', '.join(missing)}",
        )
    stdout = f"static site OK: {index.name} ({len(html_text)} bytes)"
    if checker.errors:
        stdout += f"; html warnings: {len(checker.errors)}"
    return ShellResult(cmd="<static-validate>", returncode=0, stdout=stdout, stderr="")


def _is_browser_open(cmd: str) -> bool:
    if not cmd:
        return False
    if _BROWSER_PHRASES.search(cmd):
        return True
    # Heuristic: command starts with a capital letter and has spaces but no
    # typical shell tokens — likely natural language, not a shell command.
    stripped = cmd.strip()
    if stripped and stripped[0].isupper() and " " in stripped:
        shellish = re.search(r"[|&;<>$`]|--|\.\/|\b(python|node|npm|yarn|pnpm|go|cargo|java|bash|sh|make|docker|uvicorn|flask|gunicorn)\b", stripped)
        if not shellish:
            return True
    return False


def install_and_run(
    workspace: Path, plan: dict, sandbox: Sandbox
) -> tuple[ShellResult, ShellResult | None]:
    install_cmd = (plan.get("install_command") or "").strip()
    run_cmd = (plan.get("run_command") or "").strip()
    project_type = (plan.get("project_type") or "").lower()

    # Static site fast-path: validate files, never exec a browser-open command.
    is_static = project_type in _STATIC_TYPES or _is_browser_open(run_cmd)
    if is_static:
        log(f"[RUN] static-site validation (project_type={project_type or 'inferred'})")
        validation = _validate_static_site(workspace, plan)
        return validation, validation

    install_result: ShellResult | None = None
    if install_cmd:
        log(f"[RUN] install: {install_cmd}")
        install_result = sandbox.exec(install_cmd, timeout=180)
        if not install_result.ok:
            return install_result, None
    if not run_cmd:
        return install_result or ShellResult(cmd="", returncode=0, stdout="", stderr=""), None
    log(f"[RUN] run: {run_cmd}")
    run_result = sandbox.exec(run_cmd, timeout=90)
    return install_result or ShellResult(cmd="", returncode=0, stdout="", stderr=""), run_result
