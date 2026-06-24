from typer.testing import CliRunner
from devmind.cli import app
runner = CliRunner()
def test_version():
    r = runner.invoke(app, ["version"])
    assert r.exit_code == 0
    assert "DevMind 3.0.0" in r.stdout
def test_config():
    r = runner.invoke(app, ["config"])
    assert r.exit_code == 0
    assert "local LLM only" in r.stdout
def test_hardware():
    r = runner.invoke(app, ["hardware"])
    assert r.exit_code == 0
