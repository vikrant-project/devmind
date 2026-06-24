"""ZIP export."""
from __future__ import annotations
import zipfile
from pathlib import Path


def export_zip(workspace: Path, output: Path | None = None) -> Path:
    if output is None:
        output = workspace.parent / f"{workspace.name}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in workspace.rglob("*"):
            if f.is_file() and ".git/" not in str(f):
                zf.write(f, f.relative_to(workspace))
    return output
