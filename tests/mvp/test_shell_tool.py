from devmind.tools.shell_tool import ShellTool
def test_run_echo(tmp_path):
    r = ShellTool(tmp_path).run("echo hi")
    assert r.ok and "hi" in r.stdout
def test_blocked(tmp_path):
    r = ShellTool(tmp_path).run("rm -rf /")
    assert r.returncode == 126
def test_timeout(tmp_path):
    r = ShellTool(tmp_path).run("sleep 5", timeout=1)
    assert r.timed_out
