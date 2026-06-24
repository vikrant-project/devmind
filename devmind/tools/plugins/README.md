# DevMind tool plugins
Drop a `.py` file in this directory exposing a `register(registry)` function
to add new tools. The CLI auto-discovers and loads them at startup.

Example:
```python
from devmind.tools.base import Tool

def register(registry):
    registry.register(Tool("hello", "print hello", lambda: "hi"))
```
