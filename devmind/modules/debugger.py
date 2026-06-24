"""Debug a failed run via LLM."""
from __future__ import annotations
from ..llm.parser import extract_json
from ..llm.prompts import DEBUG_PROMPT
from ..llm.router import LLMRouter


def diagnose(router: LLMRouter, plan: dict, command: str, error: str, file_index: dict) -> dict:
    idx_str = "\n".join(f"- {p}: {d}" for p, d in list(file_index.items())[:30])
    msg = DEBUG_PROMPT.format(
        project_name=plan.get("project_name", ""),
        command=command, error=error[:3000], file_index=idx_str,
    )
    resp = router.call("debug", [{"role": "user", "content": msg}], temperature=0.2, max_tokens=1024)
    j = extract_json(resp.content) or {}
    return {
        "root_cause": j.get("root_cause", "unknown"),
        "files_to_fix": j.get("files_to_fix", []),
        "suggested_fix": j.get("suggested_fix", ""),
    }
