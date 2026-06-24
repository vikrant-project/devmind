from devmind.llm.model_manager import detect_hardware, discover_models, select_model
from devmind.llm.backend_detector import detect_backend
def test_hardware():
    hp = detect_hardware()
    assert hp.cpu_cores > 0 and hp.ram_total_gb > 0
def test_discover():
    b = detect_backend(); hp = detect_hardware()
    recs = discover_models(b, hp)
    assert len(recs) >= 1
def test_select():
    b = detect_backend(); hp = detect_hardware()
    recs = discover_models(b, hp)
    for task in ("planning","coding","fix","review","doc","test"):
        assert select_model(recs, task, hp) is not None
