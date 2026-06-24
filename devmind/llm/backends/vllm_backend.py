"""vLLM — uses OpenAI-compatible endpoint."""
from .openai_compat import OpenAICompatBackend


class VLLMBackend(OpenAICompatBackend):
    name = "vllm"
