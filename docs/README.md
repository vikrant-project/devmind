# DevMind V3 — Autonomous CLI AI Coding Agent (Local LLM)
DevMind V3 is a production-grade autonomous coding agent that plans, codes, runs, tests, debugs,
fixes, reviews, documents, and exports software projects from a single natural-language prompt —
powered entirely by **local LLMs**. Zero API keys. Zero cloud cost. Fully offline once models are downloaded.

## Quick start
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull a coding model: `ollama pull qwen2.5-coder:7b`
3. Install DevMind: `pip install -e ".[dev]"`
4. Build something: `devmind build "Write a Python Fibonacci script"`

See SETUP.md, USAGE.md, ARCHITECTURE.md, MODELS.md, SAFETY.md, DEPLOYMENT.md.
