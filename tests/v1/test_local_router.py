from devmind.llm.backend_detector import detect_backend
from devmind.llm.model_manager import detect_hardware, discover_models
from devmind.llm.router import LLMRouter
def test_call_real_local():
    b = detect_backend(); hp = detect_hardware()
    recs = discover_models(b, hp)
    r = LLMRouter(b, recs, hp)
    resp = r.call("review", [{"role":"user","content":"Reply with the single word OK"}],
                  temperature=0.0, max_tokens=8)
    assert resp.content and resp.total_tokens >= 0
    assert resp.backend == b.name
