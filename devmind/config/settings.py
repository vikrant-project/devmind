"""Centralized configuration via pydantic-settings."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def _expand(p: Optional[str]) -> Optional[str]:
    if not p:
        return p
    return str(Path(os.path.expandvars(os.path.expanduser(p))).resolve())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Backend
    DEVMIND_LLM_BACKEND: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    LLAMACPP_HOST: str = "http://localhost:8080"
    VLLM_HOST: str = "http://localhost:8000"
    DEVMIND_LLM_BASE_URL: str = "http://localhost:1234"
    DEVMIND_LLM_API_KEY: str = "local"

    # Models dir
    DEVMIND_MODELS_DIR: str = "~/devmind/models"

    # Model routing overrides
    DEVMIND_PLANNING_MODEL: str = ""
    DEVMIND_CODING_MODEL: str = ""
    DEVMIND_DEBUG_MODEL: str = ""
    DEVMIND_FIX_MODEL: str = ""
    DEVMIND_REVIEW_MODEL: str = ""
    DEVMIND_DOC_MODEL: str = ""
    DEVMIND_TEST_MODEL: str = ""
    DEVMIND_EMBEDDING_MODEL: str = ""

    # Hardware
    DEVMIND_GPU_ENABLED: bool = False
    DEVMIND_CONTEXT_SIZE: int = 4096
    DEVMIND_NUM_THREADS: str = ""
    DEVMIND_GPU_LAYERS: str = ""

    # Agent
    DEVMIND_MODE: str = "autonomous"
    DEVMIND_MAX_ITERATIONS: int = 5
    DEVMIND_WORKSPACE_ROOT: str = "~/devmind/workspaces"
    DEVMIND_MEMORY_DB: str = "~/.devmind/memory.db"

    # Sandbox
    DEVMIND_SANDBOX: str = "docker"
    DEVMIND_SANDBOX_CPU: int = 2
    DEVMIND_SANDBOX_MEMORY: str = "1g"
    DEVMIND_SANDBOX_TIMEOUT: int = 120

    # VPS
    DEVMIND_VPS_HOST: str = ""
    DEVMIND_VPS_USER: str = ""

    @property
    def models_dir(self) -> Path:
        p = Path(os.path.expanduser(self.DEVMIND_MODELS_DIR))
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def workspace_root(self) -> Path:
        p = Path(os.path.expanduser(self.DEVMIND_WORKSPACE_ROOT))
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def memory_db_path(self) -> Path:
        p = Path(os.path.expanduser(self.DEVMIND_MEMORY_DB))
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def build_log(self) -> Path:
        p = Path(os.path.expanduser("~/devmind/build.log"))
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
