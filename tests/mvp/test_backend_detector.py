from devmind.llm.backend_detector import detect_backend
def test_backend_detect():
    b = detect_backend()
    assert b is not None
    assert b.ping()
    models = b.list_models()
    assert isinstance(models, list)
