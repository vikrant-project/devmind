from .base import registry, Tool
from .file_tool import FileTool, PatchEngine
from .shell_tool import ShellTool
from .git_tool import GitTool
from .test_tool import TestTool
from .docker_tool import DockerTool

__all__ = ["registry", "Tool", "FileTool", "PatchEngine", "ShellTool", "GitTool", "TestTool", "DockerTool"]


def load_plugins(plugins_dir):
    """Discover and load plugins from a directory (.py files exposing a `register(registry)` function)."""
    import importlib.util
    from pathlib import Path
    p = Path(plugins_dir)
    if not p.exists():
        return []
    loaded = []
    for f in p.glob("*.py"):
        if f.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"devmind_plugin_{f.stem}", f)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(registry)
                    loaded.append(f.stem)
            except Exception:
                continue
    return loaded
