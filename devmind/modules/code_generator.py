"""Generate file contents via LLM."""
from __future__ import annotations
from ..llm.parser import extract_code
from ..llm.prompts import CODE_PROMPT
from ..llm.router import LLMRouter
from ..utils.logger import log


_LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "jsx", ".tsx": "tsx",
    ".html": "html", ".css": "css", ".go": "go", ".sh": "bash", ".yml": "yaml", ".yaml": "yaml",
    ".json": "json", ".md": "markdown", ".toml": "toml", ".txt": "text", ".dockerfile": "dockerfile",
    ".env": "dotenv", ".lock": "text",
}


def language_for(path: str) -> str:
    p = path.lower()
    if p.endswith("dockerfile") or p == "dockerfile":
        return "dockerfile"
    if p.endswith("requirements.txt"):
        return "text"
    for ext, lang in _LANG_BY_EXT.items():
        if p.endswith(ext):
            return lang
    return "text"


def generate_file(router: LLMRouter, plan: dict, file_entry: dict) -> str:
    other = [f.get("path", "") for f in plan.get("files", []) if f.get("path") != file_entry.get("path")]
    lang = language_for(file_entry.get("path", ""))
    user = CODE_PROMPT.format(
        project_name=plan.get("project_name", ""),
        project_type=plan.get("project_type", ""),
        tech_stack=", ".join(plan.get("tech_stack", []) or []),
        other_files=", ".join(other[:30]),
        file_path=file_entry.get("path", ""),
        file_purpose=file_entry.get("purpose", ""),
        language=lang,
    )
    resp = router.call("coding",
                       [{"role": "system", "content": "Output only the file contents. No prose."},
                        {"role": "user", "content": user}],
                       temperature=0.2, max_tokens=4096, timeout=900)
    content = extract_code(resp.content)
    log(f"[BUILD] generated {file_entry.get('path')} ({len(content)} bytes)")
    return content
