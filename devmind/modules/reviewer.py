"""Code reviewer + simple security scan."""
from __future__ import annotations
import re
from pathlib import Path
from ..llm.parser import extract_json
from ..llm.prompts import REVIEW_PROMPT
from ..llm.router import LLMRouter


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([A-Za-z0-9_\-]{16,})['\"]"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
]


def scan_secrets(workspace: Path) -> list[dict]:
    findings = []
    for f in workspace.rglob("*"):
        if not f.is_file() or ".devmind_" in f.name or ".git/" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                findings.append({"file": str(f.relative_to(workspace)), "match": m.group(0)[:60]})
    return findings


def review(router: LLMRouter, workspace: Path, plan: dict) -> dict:
    summaries = []
    for f in (plan.get("files") or [])[:20]:
        p = workspace / f.get("path", "")
        if p.exists() and p.is_file():
            try:
                text = p.read_text(encoding="utf-8")[:1500]
            except Exception:
                continue
            summaries.append(f"--- {f.get('path')} ---\n{text}")
    msg = REVIEW_PROMPT.format(files_summary="\n\n".join(summaries)[:8000])
    resp = router.call("review", [{"role": "user", "content": msg}], temperature=0.1, max_tokens=1024)
    out = extract_json(resp.content) or {"critical_issues": [], "warnings": [], "summary": "no findings"}
    out["secrets"] = scan_secrets(workspace)
    return out
