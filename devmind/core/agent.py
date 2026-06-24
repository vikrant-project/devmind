"""Main agent orchestrator — runs the state machine end to end."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import settings
from ..llm.backend_detector import detect_backend, setup_instructions
from ..llm.model_manager import detect_hardware, discover_models
from ..llm.resource_tracker import resource_tracker
from ..llm.router import LLMRouter
from ..memory.long_term import LongTermMemory
from ..memory.embeddings import VectorStore
from ..memory.file_indexer import FileIndexer
from ..memory.short_term import compress_if_needed
from ..modules.code_generator import generate_file
from ..modules.code_runner import install_and_run
from ..modules.debugger import diagnose
from ..modules.doc_writer import write_docs
from ..modules.exporter import export_zip
from ..modules.fix_engine import fix_file
from ..modules.reviewer import review
from ..modules.test_runner import run_project_tests
from ..core.context import SessionContext
from ..core.planner import generate_plan
from ..core.safety import classify_prompt, refusal_text
from ..core.state_machine import State, StateMachine
from ..core.task_manager import order_files
from ..tools.file_tool import FileTool, PatchEngine
from ..tools.git_tool import GitTool
from ..tools.registry import load_plugins
from ..utils.helpers import new_id, safe_write_json
from ..utils.logger import log
from ..workspace.manager import create_workspace
from ..workspace.sandbox import Sandbox


class Agent:
    def __init__(self, *, mode: str = "autonomous", max_iterations: int = 5,
                 use_docker: bool = True, model_override: Optional[str] = None):
        self.mode = mode
        self.max_iterations = max_iterations
        self.use_docker = use_docker
        self.model_override = model_override
        self.backend = detect_backend()
        if not self.backend:
            raise RuntimeError(setup_instructions())
        self.hw = detect_hardware()
        self.models = discover_models(self.backend, self.hw)
        if not self.models:
            raise RuntimeError(
                "No local models found. Pull at least one model:\n"
                "  ollama pull qwen2.5-coder:7b"
            )
        self.router = LLMRouter(self.backend, self.models, self.hw)
        if model_override:
            for t in list(self.router.assignments.keys()):
                for m in self.models:
                    if m.name == model_override:
                        self.router.assignments[t] = m
                        break
        try:
            load_plugins(Path(__file__).resolve().parent.parent / "tools" / "plugins")
        except Exception as e:
            log(f"[PLUGINS] load skipped: {e}", level="WARN")

    def build(self, prompt: str, *, workspace: Optional[Path] = None) -> dict:
        log(f"[AGENT] START prompt={prompt[:120]}")
        decision = classify_prompt(prompt)
        if not decision.allowed:
            print(refusal_text(decision))
            return {"status": "refused", "reason": decision.reason}

        ws = workspace or create_workspace(prompt)
        log(f"[AGENT] workspace={ws}")
        resource_tracker.attach_workspace(ws)
        session_id = new_id("s_")
        ctx = SessionContext(session_id=session_id, prompt=prompt, workspace=ws,
                             mode=self.mode, max_iterations=self.max_iterations)
        sm = StateMachine(ws, session_id)
        ft = FileTool(ws)
        pe = PatchEngine(ft)
        git = GitTool(ws)
        git.init()
        memory = LongTermMemory()
        vec = VectorStore(memory.db_path, router=self.router)
        indexer = FileIndexer(ws)

        # UNDERSTAND
        sm.enter(State.UNDERSTAND)
        ctx.add_exchange("user", prompt)

        # PLAN
        sm.enter(State.PLAN, model=(self.router.model_for("planning") or type("x",(),{"name":""})).name)
        hints = [p["prompt"] for p in memory.find_similar_projects(prompt)]
        plan = generate_plan(self.router, prompt, hints)
        ctx.plan = plan
        safe_write_json(ws / "plan.json", plan)

        # BUILD
        sm.enter(State.BUILD, model=(self.router.model_for("coding") or type("x",(),{"name":""})).name)
        ordered = order_files(plan.get("files", []) or [])
        for entry in ordered:
            content = generate_file(self.router, plan, entry)
            ft.write(entry["path"], content)
            sm.add_file(entry["path"])
            ctx.file_index[entry["path"]] = entry.get("purpose", "")
            # check context pressure
            mctx = self.router.model_for("coding")
            if mctx and resource_tracker.stats.calls:
                util = resource_tracker.stats.calls[-1].context_utilization_pct
                compress_if_needed(ctx, util)
        git.commit_all("DevMind BUILD")
        indexer.refresh()

        # RUN + TEST + FIX loop
        results = {"iterations": 0, "tests_passed": 0, "tests_failed": 0, "errors": []}
        sandbox = Sandbox(ws, prefer="docker" if self.use_docker else "subprocess",
                          network_required=bool(plan.get("network_required", False)))
        run_ok = False
        test_ok = False
        last_err = ""
        for it in range(self.max_iterations):
            results["iterations"] = it + 1
            sm.bump_iteration()
            sm.enter(State.RUN)
            inst, run = install_and_run(ws, plan, sandbox)
            if (run is None and inst.ok) or (run is not None and run.ok):
                run_ok = True
                last_err = ""
            else:
                run_ok = False
                last_err = (run.stderr + run.stdout) if run else (inst.stderr + inst.stdout)
                last_err = last_err[-3000:]
                ctx.record_error("run", last_err)

            if run_ok:
                sm.enter(State.TEST)
                ok, p, f, output = run_project_tests(ws, plan)
                results["tests_passed"] = p
                results["tests_failed"] = f
                if ok:
                    test_ok = True
                    break
                last_err = output

            # DEBUG + FIX
            sm.enter(State.DEBUG, model=(self.router.model_for("debug") or type("x",(),{"name":""})).name)
            diag = diagnose(self.router, plan, plan.get("run_command", "") or plan.get("test_command", ""),
                            last_err, indexer.list_with_descriptions(plan))
            files_to_fix = diag.get("files_to_fix") or [f["path"] for f in plan.get("files", [])][:1]
            sm.enter(State.FIX, model=(self.router.model_for("fix") or type("x",(),{"name":""})).name)
            any_fixed = False
            for rel in files_to_fix[:3]:
                if not ft.exists(rel):
                    continue
                ok, msg = fix_file(self.router, ft, pe, rel, last_err)
                if ok:
                    any_fixed = True
                    ctx.record_error(rel, last_err[-500:], msg)
                    memory.record_error_pattern(error_desc=last_err, fix_desc=msg, worked=True,
                                                project_id=session_id, file_ext=Path(rel).suffix)
            if not any_fixed:
                results["errors"].append(last_err[-500:])
                break

        # REVIEW
        sm.enter(State.REVIEW, model=(self.router.model_for("review") or type("x",(),{"name":""})).name)
        review_result = review(self.router, ws, plan)
        results["review"] = review_result
        safe_write_json(ws / "review.json", review_result)

        # DOCUMENT
        sm.enter(State.DOCUMENT, model=(self.router.model_for("doc") or type("x",(),{"name":""})).name)
        results["resource_summary"] = resource_tracker.summary()
        results["run_ok"] = run_ok
        results["test_ok"] = test_ok
        write_docs(self.router, ws, plan, results)
        git.commit_all("DevMind DOCS")

        # EXPORT
        sm.enter(State.EXPORT)
        zip_path = export_zip(ws)
        results["zip"] = str(zip_path)

        sm.enter(State.COMPLETE)
        status = "success" if (run_ok and (test_ok or not plan.get("test_command"))) else "partial"
        if not run_ok and results.get("errors"):
            status = "failed"
        memory.record_project(
            session_id=session_id, prompt=prompt, project_type=plan.get("project_type", "other"),
            tech_stack=plan.get("tech_stack", []), status=status,
            files_created=len(sm.record.files_generated),
            tests_passed=results["tests_passed"], tests_failed=results["tests_failed"],
            iterations=results["iterations"], total_tokens=resource_tracker.stats.total_tokens,
            peak_ram_mb=resource_tracker.stats.peak_ram_mb,
            total_inference_seconds=resource_tracker.stats.total_inference_seconds,
        )
        vec.add("projects", session_id, f"{prompt} {plan.get('summary', '')}")
        memory.close()
        log(f"[AGENT] DONE status={status} ws={ws}")
        return {"status": status, "workspace": str(ws), "session_id": session_id,
                "plan": plan, "results": results}

    def resume(self, workspace: Path) -> dict:
        state_file = workspace / ".devmind_state.json"
        if not state_file.exists():
            raise RuntimeError("no .devmind_state.json — cannot resume")
        rec = json.loads(state_file.read_text(encoding="utf-8"))
        prompt = (workspace / "plan.json").exists() and json.loads(
            (workspace / "plan.json").read_text()).get("summary", "") or "resumed"
        log(f"[AGENT] RESUMING from {rec.get('current_state')}")
        return self.build(prompt, workspace=workspace)
