"""File operations + patch-based editing with rollback."""
from __future__ import annotations
import difflib
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..utils.logger import log


class FileTool:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.log_path = self.workspace / ".devmind_files.log"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _safe(self, rel: str) -> Path:
        p = (self.workspace / rel).resolve()
        if not str(p).startswith(str(self.workspace)):
            raise ValueError(f"path escapes workspace: {rel}")
        return p

    def _log(self, op: str, path: str, note: str = "") -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {op} {path} {note}\n"
        try:
            with self.log_path.open("a") as f:
                f.write(line)
        except Exception:
            pass

    def write(self, rel: str, content: str) -> Path:
        p = self._safe(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self._log("WRITE", rel, f"bytes={len(content)}")
        return p

    def read(self, rel: str) -> str:
        return self._safe(rel).read_text(encoding="utf-8")

    def exists(self, rel: str) -> bool:
        return self._safe(rel).exists()

    def list_files(self) -> list[str]:
        out = []
        for p in self.workspace.rglob("*"):
            if p.is_file() and ".devmind_" not in p.name and ".git/" not in str(p):
                out.append(str(p.relative_to(self.workspace)))
        return out


class PatchEngine:
    """Apply unified diffs with verify + rollback."""

    def __init__(self, file_tool: FileTool):
        self.ft = file_tool

    def apply(self, rel_path: str, diff_text: str) -> tuple[bool, str]:
        """Return (success, message). On failure, file is rolled back to pre-patch state."""
        target = self.ft._safe(rel_path)
        if not target.exists():
            return False, f"target file does not exist: {rel_path}"
        original = target.read_text(encoding="utf-8")
        snapshot = original

        # Try `patch` utility first
        ok, msg = self._apply_with_patch_util(target, diff_text)
        if not ok:
            # Fall back to difflib
            ok, msg = self._apply_with_difflib(target, original, diff_text)
            if not ok:
                target.write_text(snapshot, encoding="utf-8")
                self.ft._log("PATCH_FAIL", rel_path, msg)
                return False, msg

        # Verify syntax
        syn_ok, syn_msg = self._verify_syntax(target)
        if not syn_ok:
            target.write_text(snapshot, encoding="utf-8")
            self.ft._log("PATCH_ROLLBACK", rel_path, syn_msg)
            return False, f"syntax check failed, rolled back: {syn_msg}"
        self.ft._log("PATCH_OK", rel_path)
        return True, "patched"

    def _apply_with_patch_util(self, target: Path, diff_text: str) -> tuple[bool, str]:
        if not shutil.which("patch"):
            return False, "patch not available"
        with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False) as f:
            f.write(diff_text)
            diff_path = f.name
        try:
            r = subprocess.run(
                ["patch", "-p1", "--no-backup-if-mismatch", "-i", diff_path],
                cwd=target.parent.parent if target.parent != self.ft.workspace else self.ft.workspace,
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                return True, "patched via patch util"
            # Try p0
            r2 = subprocess.run(
                ["patch", "-p0", "--no-backup-if-mismatch", "-i", diff_path],
                cwd=self.ft.workspace, capture_output=True, text=True, timeout=30,
            )
            if r2.returncode == 0:
                return True, "patched via patch -p0"
            return False, (r.stderr or r.stdout or "patch failed")[:500]
        finally:
            Path(diff_path).unlink(missing_ok=True)

    def _apply_with_difflib(self, target: Path, original: str, diff_text: str) -> tuple[bool, str]:
        # Best-effort: parse hunks, apply replacements manually.
        lines = original.splitlines(keepends=True)
        try:
            patched = self._manual_unified_apply(lines, diff_text)
        except Exception as e:
            return False, f"difflib parse error: {e}"
        if patched is None:
            return False, "could not apply diff manually"
        target.write_text("".join(patched), encoding="utf-8")
        return True, "patched via difflib fallback"

    @staticmethod
    def _manual_unified_apply(lines: list[str], diff_text: str) -> Optional[list[str]]:
        out = list(lines)
        diff_lines = diff_text.splitlines()
        i = 0
        cursor = 0
        while i < len(diff_lines):
            ln = diff_lines[i]
            if ln.startswith("@@"):
                # Parse hunk header @@ -a,b +c,d @@
                try:
                    parts = ln.split()
                    src = parts[1]  # -a,b
                    src_start = int(src.split(",")[0].lstrip("-"))
                except Exception:
                    i += 1
                    continue
                cursor = max(src_start - 1, 0)
                i += 1
                # Collect hunk body
                old_block: list[str] = []
                new_block: list[str] = []
                while i < len(diff_lines) and not diff_lines[i].startswith("@@") \
                        and not diff_lines[i].startswith("---"):
                    h = diff_lines[i]
                    if h.startswith(" "):
                        old_block.append(h[1:] + "\n")
                        new_block.append(h[1:] + "\n")
                    elif h.startswith("-"):
                        old_block.append(h[1:] + "\n")
                    elif h.startswith("+"):
                        new_block.append(h[1:] + "\n")
                    i += 1
                # Locate old_block near cursor and replace
                joined_old = "".join(old_block)
                joined_new = "".join(new_block)
                window = "".join(out[cursor:cursor + len(old_block) + 5])
                if joined_old in "".join(out):
                    full = "".join(out)
                    full = full.replace(joined_old, joined_new, 1)
                    out = full.splitlines(keepends=True)
                else:
                    return None
            else:
                i += 1
        return out

    def _verify_syntax(self, target: Path) -> tuple[bool, str]:
        ext = target.suffix.lower()
        if ext == ".py":
            try:
                import ast
                ast.parse(target.read_text(encoding="utf-8"))
                return True, ""
            except SyntaxError as e:
                return False, f"python syntax: {e}"
        if ext in (".json",):
            try:
                import json
                json.loads(target.read_text(encoding="utf-8"))
                return True, ""
            except Exception as e:
                return False, f"json: {e}"
        return True, ""

    def make_diff(self, rel_path: str, new_content: str) -> str:
        old = self.ft.read(rel_path).splitlines(keepends=True)
        new = new_content.splitlines(keepends=True)
        return "".join(difflib.unified_diff(old, new, fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}"))
