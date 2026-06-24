"""Generate diff via LLM and apply via PatchEngine."""
from __future__ import annotations
from ..llm.parser import extract_diff, extract_code
from ..llm.prompts import FIX_PROMPT
from ..llm.router import LLMRouter
from ..tools.file_tool import FileTool, PatchEngine
from ..utils.logger import log


def fix_file(router: LLMRouter, file_tool: FileTool, patch_engine: PatchEngine,
             rel_path: str, error: str) -> tuple[bool, str]:
    try:
        content = file_tool.read(rel_path)
    except Exception as e:
        return False, f"read failed: {e}"
    msg = FIX_PROMPT.format(file_path=rel_path, file_content=content[:6000], error=error[:2000])
    resp = router.call("fix", [{"role": "user", "content": msg}], temperature=0.2, max_tokens=2048)
    diff = extract_diff(resp.content)
    if diff:
        ok, m = patch_engine.apply(rel_path, diff)
        if ok:
            return True, "patched"
        log(f"[FIX] patch failed: {m}; attempting full rewrite", level="WARN")
    # Fallback: ask for full rewrite
    rewrite = extract_code(resp.content)
    # Guard: never write a unified diff to a source file.
    if rewrite and ("@@" in rewrite[:80] and ("---" in rewrite[:80] or "+++" in rewrite[:80])):
        rewrite = ""
    if rewrite and rewrite != content:
        try:
            file_tool.write(rel_path, rewrite)
            return True, "rewritten"
        except Exception as e:
            return False, f"rewrite failed: {e}"
    return False, "no usable diff or rewrite"
