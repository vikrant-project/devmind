"""Base class for local LLM backends."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    tokens_per_second: float = 0.0
    backend: str = ""
    raw: dict = field(default_factory=dict)


class LLMBackend(ABC):
    name: str = "base"

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    def ping(self, timeout: float = 5.0) -> bool: ...

    @abstractmethod
    def list_models(self) -> list[dict]: ...

    @abstractmethod
    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: Optional[int] = None, timeout: float = 600.0,
             extra: Optional[dict] = None) -> LLMResponse: ...

    def embed(self, model: str, text: str, timeout: float = 60.0) -> list[float]:
        raise NotImplementedError(f"{self.name} does not support embeddings")
