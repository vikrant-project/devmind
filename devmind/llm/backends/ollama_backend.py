"""Ollama backend client (uses native /api endpoints)."""
from __future__ import annotations
import time
from typing import Optional
import httpx
from .base import LLMBackend, LLMResponse


class OllamaBackend(LLMBackend):
    name = "ollama"

    def ping(self, timeout: float = 5.0) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            r.raise_for_status()
            data = r.json()
            out = []
            for m in data.get("models", []):
                size_b = m.get("size", 0)
                out.append({
                    "name": m.get("name", "unknown"),
                    "size_gb": round(size_b / (1024**3), 2) if size_b else 0.0,
                    "details": m.get("details", {}),
                    "modified_at": m.get("modified_at", ""),
                })
            return out
        except Exception:
            return []

    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: Optional[int] = None, timeout: float = 600.0,
             extra: Optional[dict] = None) -> LLMResponse:
        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        if extra:
            options.update(extra)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        t0 = time.time()
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        elapsed = time.time() - t0
        content = (data.get("message") or {}).get("content", "")
        prompt_tokens = int(data.get("prompt_eval_count", 0) or 0)
        output_tokens = int(data.get("eval_count", 0) or 0)
        tps = (output_tokens / elapsed) if elapsed > 0 else 0.0
        return LLMResponse(
            content=content, model=model,
            prompt_tokens=prompt_tokens, output_tokens=output_tokens,
            total_tokens=prompt_tokens + output_tokens,
            elapsed_seconds=elapsed, tokens_per_second=tps,
            backend=self.name, raw=data,
        )

    def embed(self, model: str, text: str, timeout: float = 60.0) -> list[float]:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{self.base_url}/api/embeddings", json={"model": model, "prompt": text})
            r.raise_for_status()
            return r.json().get("embedding", [])

    def pull(self, model: str, timeout: float = 1800.0) -> bool:
        try:
            with httpx.Client(timeout=timeout) as c:
                r = c.post(f"{self.base_url}/api/pull", json={"model": model, "stream": False})
                return r.status_code == 200
        except Exception:
            return False
