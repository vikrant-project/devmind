import os, pytest
from devmind.core.agent import Agent
@pytest.mark.integration
def test_full_build_fibonacci(tmp_path):
    if os.environ.get("DEVMIND_SKIP_INTEGRATION") == "1":
        pytest.skip("integration skipped")
    agent = Agent(mode="autonomous", max_iterations=2, use_docker=False)
    res = agent.build("Write a Python script main.py that prints the first 5 Fibonacci numbers, one per line. No dependencies.",
                      workspace=tmp_path)
    assert res["status"] in ("success", "partial")
    assert (tmp_path/"plan.json").exists()
    assert (tmp_path/"README.md").exists()
    assert (tmp_path/"DEVMIND_REPORT.json").exists()
