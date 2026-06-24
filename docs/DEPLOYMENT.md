# Deployment
DevMind is local-first. Recommended VPS deployment:
1. SSH to VPS, install Docker + Ollama
2. `git clone <repo>` + `pip install -e .`
3. `ollama pull qwen2.5-coder:7b`
4. Run `devmind build "..."` — generated projects can be exported as ZIP or built into a Docker image.
