from pathlib import Path
import tempfile, pytest
from devmind.tools.file_tool import FileTool, PatchEngine
def test_write_read(tmp_path):
    ft = FileTool(tmp_path)
    ft.write("a/b.py", "x = 1\n")
    assert ft.read("a/b.py") == "x = 1\n"
    assert "a/b.py" in ft.list_files()
def test_escape_blocked(tmp_path):
    ft = FileTool(tmp_path)
    with pytest.raises(ValueError):
        ft.write("../escape.py", "bad")
def test_patch_simple(tmp_path):
    ft = FileTool(tmp_path); pe = PatchEngine(ft)
    ft.write("m.py", "a = 1\nb = 2\n")
    new = "a = 1\nb = 3\n"
    diff = pe.make_diff("m.py", new)
    ok, msg = pe.apply("m.py", diff)
    assert ok, msg
    assert ft.read("m.py") == new
def test_patch_rollback_bad_syntax(tmp_path):
    ft = FileTool(tmp_path); pe = PatchEngine(ft)
    ft.write("m.py", "a = 1\n")
    bad = "--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-a = 1\n+a =\n"
    ok, _ = pe.apply("m.py", bad)
    assert not ok
    assert ft.read("m.py") == "a = 1\n"
