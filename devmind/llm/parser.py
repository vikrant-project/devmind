"""Parse code blocks, JSON, and diffs out of LLM responses."""
from __future__ import annotations
import json
import re
from typing import Optional

_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+\-]*)\n([\s\S]*?)```", re.MULTILINE)
_JSON_RE = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")


def extract_json(text: str) -> Optional[dict | list]:
    if not text:
        return None
    fences = _FENCE_RE.findall(text)
    candidates = fences + [text]
    for c in candidates:
        try:
            return json.loads(c.strip())
        except Exception:
            pass
        m = _JSON_RE.search(c)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                continue
    return None


def extract_code(text: str) -> str:
    if not text:
        return ""
    fences = _FENCE_RE.findall(text)
    # Skip fences whose content looks like a unified diff -- callers that want
    # diffs use extract_diff().
    for f in fences:
        stripped = f.strip("\n")
        if "---" in stripped and "+++" in stripped and "@@" in stripped:
            continue
        if stripped.startswith(("--- ", "@@ ", "+++ ")):
            continue
        return stripped
    return text.strip()


def extract_diff(text: str) -> Optional[str]:
    if not text:
        return None
    fences = _FENCE_RE.findall(text)
    for c in fences + [text]:
        if "---" in c and "+++" in c and "@@" in c:
            return c.strip("\n")
    return None
