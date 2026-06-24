"""Hardware detection, model discovery, auto-selection."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import psutil

from ..config import settings
from ..utils.helpers import parse_param_count, parse_quant, safe_write_json
from ..utils.logger import log
from .backends.base import LLMBackend


@dataclass
class HardwareProfile:
    profile: str
    cpu_cores: int
    cpu_model: str
    ram_total_gb: float
    ram_available_gb: float
    gpu_present: bool
    gpu_vendor: str
    vram_gb: float
    disk_free_gb: float
    max_param_b: float


def detect_hardware() -> HardwareProfile:
    cpu_cores = psutil.cpu_count(logical=True) or 1
    cpu_model = "unknown"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    vm = psutil.virtual_memory()
    ram_total_gb = round(vm.total / (1024**3), 2)
    ram_available_gb = round(vm.available / (1024**3), 2)

    gpu_present = False
    gpu_vendor = "none"
    vram_gb = 0.0
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                vals = [int(x.strip()) for x in out.stdout.strip().splitlines() if x.strip().isdigit()]
                if vals:
                    gpu_present = True
                    gpu_vendor = "nvidia"
                    vram_gb = round(max(vals) / 1024.0, 2)
        except Exception:
            pass
    if not gpu_present and shutil.which("rocm-smi"):
        try:
            r = subprocess.run(["rocm-smi", "--showmeminfo", "vram"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                m = re.search(r"(\d+)\s*MB", r.stdout)
                if m:
                    gpu_present = True
                    gpu_vendor = "amd"
                    vram_gb = round(int(m.group(1)) / 1024.0, 2)
        except Exception:
            pass

    models_dir = settings.models_dir
    try:
        usage = shutil.disk_usage(models_dir)
        disk_free_gb = round(usage.free / (1024**3), 2)
    except Exception:
        disk_free_gb = 0.0

    is_vps = _is_vps()
    profile = _profile_name(gpu_present, vram_gb, ram_total_gb, is_vps)
    max_param_b = _max_param_for_profile(profile)

    hp = HardwareProfile(
        profile=profile, cpu_cores=cpu_cores, cpu_model=cpu_model,
        ram_total_gb=ram_total_gb, ram_available_gb=ram_available_gb,
        gpu_present=gpu_present, gpu_vendor=gpu_vendor, vram_gb=vram_gb,
        disk_free_gb=disk_free_gb, max_param_b=max_param_b,
    )
    profile_path = Path(os.path.expanduser("~/.devmind/hardware_profile.json"))
    safe_write_json(profile_path, asdict(hp))
    log(f"[HARDWARE] profile={profile} cores={cpu_cores} ram={ram_total_gb}GB gpu={gpu_vendor} vram={vram_gb}GB")
    return hp


def _is_vps() -> bool:
    # Heuristic: AWS/GCP/Azure/DO instances usually have these markers
    indicators = [
        Path("/sys/class/dmi/id/product_name"),
        Path("/sys/class/dmi/id/sys_vendor"),
    ]
    for p in indicators:
        try:
            if p.exists():
                v = p.read_text(errors="ignore").lower()
                for k in ("amazon", "ec2", "google", "azure", "digitalocean", "kvm", "qemu", "openstack"):
                    if k in v:
                        return True
        except Exception:
            continue
    return False


def _profile_name(gpu: bool, vram: float, ram: float, is_vps: bool) -> str:
    if gpu:
        if vram >= 16: return "gpu_high"
        if vram >= 8: return "gpu_standard"
        if vram >= 4: return "gpu_low"
    if is_vps:
        return "vps_no_gpu"
    if ram < 8: return "cpu_minimal"
    if ram < 12: return "cpu_low"
    if ram < 32: return "cpu_standard"
    return "cpu_high"


def _max_param_for_profile(p: str) -> float:
    return {
        "cpu_minimal": 3.0, "cpu_low": 7.0, "cpu_standard": 13.0, "cpu_high": 34.0,
        "gpu_low": 7.0, "gpu_standard": 13.0, "gpu_high": 70.0,
        "vps_no_gpu": 13.0,
    }.get(p, 7.0)


@dataclass
class ModelRecord:
    model_id: str
    name: str
    backend: str
    path_or_tag: str
    size_gb: float
    param_count_b: float
    quantization: str
    context_window: int
    capabilities: list
    available: bool


def _infer_capabilities(name: str) -> list:
    n = name.lower()
    caps = []
    if any(k in n for k in ("coder", "code", "starcoder", "deepseek-coder")):
        caps.append("code")
    if any(k in n for k in ("instruct", "chat", "it", "llama", "mistral", "qwen", "mixtral", "phi", "gemma")):
        caps.extend(["chat", "instruct"])
    if any(k in n for k in ("embed", "minilm", "nomic-embed")):
        caps.append("embedding")
    return list(set(caps)) or ["chat"]


def discover_models(backend: Optional[LLMBackend], hp: HardwareProfile) -> list[ModelRecord]:
    records: list[ModelRecord] = []
    seen = set()

    if backend is not None:
        for m in backend.list_models():
            name = m.get("name", "unknown")
            if name in seen:
                continue
            seen.add(name)
            param = parse_param_count(name) or m.get("details", {}).get("parameter_size", 0)
            try:
                param_f = float(param) if not isinstance(param, str) else parse_param_count(param)
            except Exception:
                param_f = parse_param_count(name)
            records.append(ModelRecord(
                model_id=name, name=name, backend=backend.name,
                path_or_tag=name, size_gb=float(m.get("size_gb", 0.0)),
                param_count_b=param_f, quantization=parse_quant(name),
                context_window=settings.DEVMIND_CONTEXT_SIZE,
                capabilities=_infer_capabilities(name),
                available=(param_f == 0.0 or param_f <= hp.max_param_b * 1.2),
            ))

    md = settings.models_dir
    if md.exists():
        for gguf in md.rglob("*.gguf"):
            name = gguf.stem
            if name in seen:
                continue
            seen.add(name)
            size_gb = round(gguf.stat().st_size / (1024**3), 2)
            param = parse_param_count(name)
            records.append(ModelRecord(
                model_id=name, name=name, backend="gguf",
                path_or_tag=str(gguf), size_gb=size_gb,
                param_count_b=param, quantization=parse_quant(name),
                context_window=settings.DEVMIND_CONTEXT_SIZE,
                capabilities=_infer_capabilities(name),
                available=(param == 0.0 or param <= hp.max_param_b * 1.2),
            ))

    log(f"[MODELS] Discovered {len(records)} model(s)")
    return records


def select_model(records: list[ModelRecord], task: str, hp: HardwareProfile) -> Optional[ModelRecord]:
    """Choose best model for task. task in: planning, coding, debug, fix, review, doc, test, embedding."""
    if not records:
        return None
    explicit_map = {
        "planning": settings.DEVMIND_PLANNING_MODEL,
        "coding": settings.DEVMIND_CODING_MODEL,
        "debug": settings.DEVMIND_DEBUG_MODEL,
        "fix": settings.DEVMIND_FIX_MODEL,
        "review": settings.DEVMIND_REVIEW_MODEL,
        "doc": settings.DEVMIND_DOC_MODEL,
        "test": settings.DEVMIND_TEST_MODEL,
        "embedding": settings.DEVMIND_EMBEDDING_MODEL,
    }
    explicit = explicit_map.get(task, "").strip()
    if explicit:
        for r in records:
            if r.name == explicit or r.model_id == explicit:
                return r

    available = [r for r in records if r.available]
    if not available:
        available = records

    if task == "embedding":
        embed = [r for r in available if "embedding" in r.capabilities]
        if embed:
            return embed[0]

    code_models = [r for r in available if "code" in r.capabilities]
    chat_models = [r for r in available if "chat" in r.capabilities or "instruct" in r.capabilities]

    if task in ("coding", "fix", "test"):
        pool = code_models or chat_models or available
        return max(pool, key=lambda r: r.param_count_b)

    if task in ("planning", "debug"):
        pool = chat_models or available
        return max(pool, key=lambda r: r.param_count_b)

    if task in ("review", "doc"):
        pool = chat_models or available
        # smallest fits - to save RAM
        non_zero = [r for r in pool if r.param_count_b > 0]
        if non_zero:
            return min(non_zero, key=lambda r: r.param_count_b)
        return pool[0]

    return available[0]
