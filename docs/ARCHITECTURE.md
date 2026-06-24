# Architecture
DevMind is a strict 10-state machine: UNDERSTAND -> PLAN -> BUILD -> RUN -> TEST -> (DEBUG -> FIX -> RUN) -> REVIEW -> DOCUMENT -> EXPORT -> COMPLETE.
State persisted to .devmind_state.json; `devmind continue` resumes after crashes.
Modules: llm/ (backends + router + manager + resource tracker), core/ (agent + state + safety + planner),
tools/ (file + shell + git + test + docker + patch engine), modules/ (code_generator, runner, debugger, fix_engine, reviewer, doc_writer, exporter),
memory/ (short_term, long_term sqlite, embeddings, file indexer), workspace/ (manager + sandbox), eval/ (benchmarks + scorer).
