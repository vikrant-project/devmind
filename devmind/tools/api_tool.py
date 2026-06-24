"""HTTP smoke-test helper for API projects."""
from __future__ import annotations
import time
import httpx


def wait_for(url: str, timeout: float = 20.0, interval: float = 0.5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        r = httpx.get(url, timeout=timeout)
        return r.status_code, r.text[:500]
    except Exception as e:
        return 0, str(e)
