from devmind.memory.long_term import LongTermMemory
def test_record_and_query(tmp_path):
    db = tmp_path/"m.db"
    m = LongTermMemory(db)
    pid = m.record_project(session_id="s1", prompt="todo api fastapi sqlite",
        project_type="python_api", tech_stack=["python","fastapi"], status="success",
        files_created=5, tests_passed=3, tests_failed=0, iterations=1,
        total_tokens=100, peak_ram_mb=200, total_inference_seconds=5.0)
    assert pid
    sim = m.find_similar_projects("fastapi todo")
    assert any("todo" in s["prompt"] for s in sim)
    m.record_model_perf(model="qwen", task="coding", tps=10.0, quality=1.0)
    m.record_model_perf(model="qwen", task="coding", tps=20.0, quality=1.0)
    m.close()
