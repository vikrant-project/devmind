"""Plan generation."""
from __future__ import annotations
from typing import Optional

from ..llm.parser import extract_json
from ..llm.prompts import PLAN_PROMPT
from ..llm.router import LLMRouter
from ..utils.logger import log


def generate_plan(router: LLMRouter, prompt: str, memory_hints: Optional[list] = None) -> dict:
    hints = ""
    if memory_hints:
        hints = "\n\nRelated past projects:\n" + "\n".join(f"- {h}" for h in memory_hints[:3])
    user_msg = f"Project request:\n{prompt}{hints}"
    resp = router.call(
        "planning",
        [{"role": "system", "content": PLAN_PROMPT},
         {"role": "user", "content": user_msg}],
        temperature=0.2, max_tokens=2048, timeout=600,
    )
    plan = extract_json(resp.content) or {}
    if not isinstance(plan, dict):
        plan = {}
    plan.setdefault("project_name", "untitled-project")
    plan.setdefault("project_type", "other")
    plan.setdefault("tech_stack", [])
    plan.setdefault("network_required", False)
    plan.setdefault("summary", prompt[:200])
    plan.setdefault("files", [])
    plan.setdefault("run_command", "")
    plan.setdefault("test_command", "")
    plan.setdefault("install_command", "")
    log(f"[PLAN] project={plan['project_name']} files={len(plan['files'])} type={plan['project_type']}")
    return plan
