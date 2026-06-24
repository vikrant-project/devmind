from devmind.workspace.sandbox import Sandbox
def test_subprocess_echo(tmp_path):
    sb = Sandbox(tmp_path, prefer="subprocess")
    assert sb.level == 2
    r = sb.exec("echo from-sandbox", timeout=10)
    assert r.ok and "from-sandbox" in r.stdout
def test_subprocess_timeout(tmp_path):
    sb = Sandbox(tmp_path, prefer="subprocess")
    r = sb.exec("sleep 5", timeout=2)
    assert r.timed_out
