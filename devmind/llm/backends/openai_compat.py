"""Generic OpenAI-compatible client (works with llama.cpp server, vLLM, LM Studio, Jan, TabbyAPI)."""
from __future__ import annotations
import time
from typing import Optional
import httpx
from .base import LLMBackend, LLMResponse


class OpenAICompatBackend(LLMBackend):
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str = "local"):
        super().__init__(base_url)
        self.api_key = api_key or "local"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def ping(self, timeout: float = 5.0) -> bool:
        for path in ("/v1/models", "/health", "/"):
            try:
                r = httpx.get(f"{self.base_url}{path}", headers=self._headers(), timeout=timeout)
                if r.status_code < 500:
                    return True
            except Exception:
                continue
        return False

    def list_models(self) -> list[dict]:
        try:
            r = httpx.get(f"{self.base_url}/v1/models", headers=self._headers(), timeout=10)
            r.raise_for_status()
            data = r.json().get("data", [])
            return [{"name": m.get("id", "unknown"), "size_gb": 0.0, "details": m} for m in data]
        except Exception:
            return []

    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: Optional[int] = None, timeout: float = 600.0,
             extra: Optional[dict] = None) -> LLMResponse:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if extra:
            payload.update(extra)
        t0 = time.time()
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{self.base_url}/v1/chat/completions", json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        elapsed = time.time() - t0
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content", "")
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)
        tps = (output_tokens / elapsed) if elapsed > 0 else 0.0
        return LLMResponse(
            content=content, model=model,
            prompt_tokens=prompt_tokens, output_tokens=output_tokens,
            total_tokens=prompt_tokens + output_tokens,
            elapsed_seconds=elapsed, tokens_per_second=tps,
            backend=self.name, raw=data,
        )
