"""DevMind CLI (Typer)."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from . import __version__
from .config import settings
from .core.agent import Agent
from .core.safety import classify_prompt, refusal_text
from .llm.backend_detector import detect_backend, setup_instructions
from .llm.model_manager import detect_hardware, discover_models, select_model
from .modules.exporter import export_zip
from .memory.long_term import LongTermMemory
from .utils.display import console
from .utils.logger import log
from .workspace.manager import find_workspace

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def version():
    """Print DevMind version and environment info."""
    console.print(f"[bold]DevMind {__version__}[/bold]")
    console.print(f"Python: {sys.version.split()[0]}")
    console.print(f"Backend env: DEVMIND_LLM_BACKEND={settings.DEVMIND_LLM_BACKEND or 'auto'}")
    raise typer.Exit(0)


@app.command()
def config():
    """Show config (no secrets — local-only)."""
    table = Table(title="DevMind Config (local-only)")
    table.add_column("Key"); table.add_column("Value")
    for k in ["DEVMIND_LLM_BACKEND", "OLLAMA_HOST", "LLAMACPP_HOST", "VLLM_HOST",
              "DEVMIND_LLM_BASE_URL", "DEVMIND_MODELS_DIR", "DEVMIND_MODE",
              "DEVMIND_MAX_ITERATIONS", "DEVMIND_SANDBOX", "DEVMIND_GPU_ENABLED",
              "DEVMIND_CONTEXT_SIZE"]:
        table.add_row(k, str(getattr(settings, k)))
    table.add_row("EXTERNAL_API_KEYS", "[green]none — local LLM only[/green]")
    console.print(table)


@app.command()
def hardware():
    """Show detected hardware profile."""
    hp = detect_hardware()
    t = Table(title="Hardware profile")
    t.add_column("field"); t.add_column("value")
    t.add_row("profile", hp.profile); t.add_row("cpu_cores", str(hp.cpu_cores))
    t.add_row("cpu_model", hp.cpu_model); t.add_row("ram_total_gb", str(hp.ram_total_gb))
    t.add_row("ram_available_gb", str(hp.ram_available_gb)); t.add_row("gpu", hp.gpu_vendor)
    t.add_row("vram_gb", str(hp.vram_gb)); t.add_row("disk_free_gb", str(hp.disk_free_gb))
    t.add_row("max_param_b", str(hp.max_param_b))
    console.print(t)


@app.command()
def models():
    """List discovered local models + routing assignments."""
    backend = detect_backend()
    if not backend:
        console.print("[red]No backend reachable.[/red]")
        console.print(setup_instructions())
        raise typer.Exit(1)
    hp = detect_hardware()
    records = discover_models(backend, hp)
    t = Table(title=f"Local models (backend={backend.name})")
    t.add_column("name"); t.add_column("size_gb"); t.add_column("params_b")
    t.add_column("quant"); t.add_column("backend"); t.add_column("available")
    for r in records:
        t.add_row(r.name, str(r.size_gb), str(r.param_count_b), r.quantization,
                  r.backend, "[green]yes[/green]" if r.available else "[yellow]large[/yellow]")
    console.print(t)
    routing = Table(title="Task -> Model")
    routing.add_column("task"); routing.add_column("model")
    for task in ("planning", "coding", "debug", "fix", "review", "doc", "test", "embedding"):
        m = select_model(records, task, hp)
        routing.add_row(task, m.name if m else "[red]none[/red]")
    console.print(routing)


@app.command()
def build(
    prompt: str,
    model: Optional[str] = typer.Option(None, "--model"),
    coding_model: Optional[str] = typer.Option(None, "--coding-model"),
    planning_model: Optional[str] = typer.Option(None, "--planning-model"),
    mode: str = typer.Option("autonomous", "--mode"),
    max_iterations: int = typer.Option(5, "--max-iterations"),
    no_docker: bool = typer.Option(True, "--no-docker/--use-docker"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir"),
    no_git: bool = typer.Option(False, "--no-git"),
    export_zip_flag: bool = typer.Option(False, "--export-zip"),
    verbose: bool = typer.Option(False, "--verbose"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Build a project from a natural-language prompt."""
    if coding_model:
        settings.DEVMIND_CODING_MODEL = coding_model
    if planning_model:
        settings.DEVMIND_PLANNING_MODEL = planning_model
    decision = classify_prompt(prompt)
    if not decision.allowed:
        console.print(refusal_text(decision))
        raise typer.Exit(1)
    if dry_run:
        agent = Agent(mode=mode, max_iterations=max_iterations,
                      use_docker=not no_docker, model_override=model)
        from .core.planner import generate_plan
        plan = generate_plan(agent.router, prompt)
        console.print_json(json.dumps(plan, indent=2))
        return
    workspace = Path(output_dir) if output_dir else None
    agent = Agent(mode=mode, max_iterations=max_iterations,
                  use_docker=not no_docker, model_override=model)
    res = agent.build(prompt, workspace=workspace)
    console.print_json(json.dumps({"status": res.get("status"),
                                   "workspace": res.get("workspace"),
                                   "iterations": res.get("results", {}).get("iterations"),
                                   "tests": f"{res.get('results',{}).get('tests_passed',0)}/{res.get('results',{}).get('tests_passed',0)+res.get('results',{}).get('tests_failed',0)}",
                                   "resource_summary": res.get("results", {}).get("resource_summary", {})}, indent=2))


@app.command()
def continue_(workspace_path: str):
    """Resume an interrupted build."""
    ws = find_workspace(workspace_path)
    agent = Agent()
    res = agent.resume(ws)
    console.print_json(json.dumps({"status": res.get("status")}, indent=2))


# Typer command name with hyphen
app.command(name="continue")(continue_)


@app.command(name="list")
def list_cmd(status: str = typer.Option("all", "--status")):
    """List past projects from long-term memory."""
    mem = LongTermMemory()
    rows = mem.list_projects(status)
    mem.close()
    t = Table(title="Projects")
    for col in ("id", "type", "status", "at", "prompt"):
        t.add_column(col)
    for r in rows:
        t.add_row(r["id"], r["type"] or "", r["status"] or "", r["at"] or "", (r["prompt"] or "")[:60])
    console.print(t)


@app.command()
def inspect(workspace_path: str):
    """Inspect a workspace state & report."""
    ws = find_workspace(workspace_path)
    for fname in ("plan.json", ".devmind_state.json", "review.json", "DEVMIND_REPORT.json"):
        p = ws / fname
        if p.exists():
            console.rule(fname)
            console.print(p.read_text()[:4000])


@app.command()
def export(workspace_path: str, output: Optional[str] = typer.Option(None, "--output")):
    """Export workspace as ZIP."""
    ws = find_workspace(workspace_path)
    out = Path(output) if output else None
    z = export_zip(ws, out)
    console.print(f"[green]exported:[/green] {z}")


@app.command()
def benchmark(suite: str = typer.Option("mvp", "--suite"),
              output: Optional[str] = typer.Option(None, "--output")):
    """Run benchmark suite."""
    from .eval.runner import run_benchmarks
    res = run_benchmarks(suite=suite, output=Path(output) if output else None)
    console.print_json(json.dumps(res, indent=2))


@app.command()
def pull(model: str):
    """Convenience wrapper: pull a model via Ollama."""
    import subprocess
    r = subprocess.run(["ollama", "pull", model])
    raise typer.Exit(r.returncode)


@app.command()
def clean(workspace_path: str):
    """Delete a workspace."""
    import shutil
    ws = find_workspace(workspace_path)
    shutil.rmtree(ws)
    console.print(f"[yellow]deleted:[/yellow] {ws}")


if __name__ == "__main__":
    app()
