"""Detect and select a local LLM backend."""
from __future__ import annotations
from typing import Optional
from ..config import settings
from ..utils.logger import log
from .backends.base import LLMBackend
from .backends.ollama_backend import OllamaBackend
from .backends.llamacpp_backend import LlamaCppBackend
from .backends.vllm_backend import VLLMBackend
from .backends.openai_compat import OpenAICompatBackend


def _build(name: str) -> Optional[LLMBackend]:
    if name == "ollama":
        return OllamaBackend(settings.OLLAMA_HOST)
    if name == "llamacpp":
        return LlamaCppBackend(settings.LLAMACPP_HOST, settings.DEVMIND_LLM_API_KEY)
    if name == "vllm":
        return VLLMBackend(settings.VLLM_HOST, settings.DEVMIND_LLM_API_KEY)
    if name == "openai_compat":
        return OpenAICompatBackend(settings.DEVMIND_LLM_BASE_URL, settings.DEVMIND_LLM_API_KEY)
    return None


def detect_backend(explicit: Optional[str] = None) -> Optional[LLMBackend]:
    forced = explicit or settings.DEVMIND_LLM_BACKEND
    if forced:
        b = _build(forced)
        if b and b.ping():
            log(f"[BACKEND] Using explicit backend: {forced} at {b.base_url}")
            return b
        log(f"[BACKEND] Explicit backend '{forced}' not reachable.", level="WARN")
        return None

    for name in ("ollama", "llamacpp", "vllm", "openai_compat"):
        b = _build(name)
        if b and b.ping(timeout=2.0):
            log(f"[BACKEND] Auto-detected backend: {name} at {b.base_url}")
            return b
    log("[BACKEND] No local LLM backend reachable.", level="ERROR")
    return None


def setup_instructions() -> str:
    return (
        "No local LLM backend reachable. Set one up:\n"
        "  Option 1 (Ollama, recommended):\n"
        "    curl -fsSL https://ollama.com/install.sh | sh\n"
        "    ollama serve &\n"
        "    ollama pull qwen2.5-coder:7b\n"
        "  Option 2 (llama.cpp server):\n"
        "    llama-server -m model.gguf --port 8080\n"
        "  Option 3 (custom OpenAI-compatible server):\n"
        "    set DEVMIND_LLM_BASE_URL in .env\n"
    )
