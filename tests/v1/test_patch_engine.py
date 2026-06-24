from devmind.tools.file_tool import FileTool, PatchEngine
def test_patch_idempotent(tmp_path):
    ft = FileTool(tmp_path); pe = PatchEngine(ft)
    ft.write("m.py", "print(1)\nprint(2)\n")
    diff = pe.make_diff("m.py", "print(1)\nprint(3)\n")
    ok, _ = pe.apply("m.py", diff)
    assert ok and "print(3)" in ft.read("m.py")
