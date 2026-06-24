"""Small utilities."""
from __future__ import annotations
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def safe_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len] or "project"


def parse_param_count(name: str) -> float:
    """Extract parameter count in billions from model name. Returns 0.0 if unknown."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*[bB](?!\w)", name)
    if m:
        return float(m.group(1))
    m2 = re.search(r"(\d+)x(\d+)\s*[bB]", name)
    if m2:
        return float(m2.group(1)) * float(m2.group(2))
    return 0.0


def parse_quant(name: str) -> str:
    m = re.search(r"(Q\d+_[A-Z0-9_]+|Q\d+|F16|F32|BF16)", name, re.IGNORECASE)
    return m.group(1).upper() if m else "unknown"
