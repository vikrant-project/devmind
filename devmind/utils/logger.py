"""Build log writer — every line gets ISO timestamp prefix."""
from __future__ import annotations
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from ..config import settings


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str, *, level: str = "INFO") -> None:
    """Append timestamped line to build.log and stderr."""
    line = f"[{_ts()}] [{level}] {message}"
    try:
        with open(settings.build_log, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, file=sys.stderr)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
        logger.addHandler(h)
    return logger
