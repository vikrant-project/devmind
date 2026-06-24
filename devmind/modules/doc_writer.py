"""README + ARCHITECTURE + DEVMIND_REPORT writer."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from ..llm.parser import extract_code
from ..llm.prompts import DOC_PROMPT
from ..llm.router import LLMRouter


def write_docs(router: LLMRouter, workspace: Path, plan: dict, results: dict) -> None:
    files = [f.get("path", "") for f in (plan.get("files") or [])]
    msg = DOC_PROMPT.format(
        project_name=plan.get("project_name", ""),
        project_type=plan.get("project_type", ""),
        summary=plan.get("summary", ""),
        tech_stack=", ".join(plan.get("tech_stack", []) or []),
        install_command=plan.get("install_command", ""),
        run_command=plan.get("run_command", ""),
        test_command=plan.get("test_command", ""),
        file_list=", ".join(files[:25]),
    )
    resp = router.call("doc", [{"role": "user", "content": msg}], temperature=0.2, max_tokens=2048)
    readme = extract_code(resp.content) or f"# {plan.get('project_name')}\n\n{plan.get('summary')}"
    (workspace / "README.md").write_text(readme, encoding="utf-8")

    arch_lines = [f"# Architecture — {plan.get('project_name')}", "",
                  f"**Type:** {plan.get('project_type')}",
                  f"**Tech stack:** {', '.join(plan.get('tech_stack', []) or [])}", "",
                  "## Files", ""]
    for f in plan.get("files", []) or []:
        arch_lines.append(f"- `{f.get('path')}` — {f.get('purpose', '')}")
    (workspace / "ARCHITECTURE.md").write_text("\n".join(arch_lines), encoding="utf-8")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan": plan,
        "results": results,
        "external_api_calls": 0,
        "powered_by": "local LLM only",
    }
    (workspace / "DEVMIND_REPORT.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
