"""Workspace lifecycle."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from ..config import settings
from ..utils.helpers import slugify


def create_workspace(prompt: str, root: Path | None = None) -> Path:
    root = root or settings.workspace_root
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"{slugify(prompt)}_{ts}"
    ws = root / name
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def find_workspace(path_like: str) -> Path:
    p = Path(path_like).expanduser()
    if p.exists() and p.is_dir():
        return p.resolve()
    # try inside workspace root
    root = settings.workspace_root
    candidate = root / path_like
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"workspace not found: {path_like}")
