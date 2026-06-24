"""Dependency-aware ordering of file generation tasks."""
from __future__ import annotations


def order_files(files: list[dict]) -> list[dict]:
    """Topological sort by depends_on; ties broken by original order."""
    by_path = {f["path"]: f for f in files if "path" in f}
    visited = set()
    out: list[dict] = []

    def visit(node: dict, stack: set):
        p = node["path"]
        if p in visited or p in stack:
            return
        stack.add(p)
        for dep in node.get("depends_on", []) or []:
            if dep in by_path:
                visit(by_path[dep], stack)
        stack.discard(p)
        visited.add(p)
        out.append(node)

    for f in files:
        if "path" in f:
            visit(f, set())
    return out
