"""llama.cpp server — uses OpenAI-compatible endpoint."""
from .openai_compat import OpenAICompatBackend


class LlamaCppBackend(OpenAICompatBackend):
    name = "llamacpp"
