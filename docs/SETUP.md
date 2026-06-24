# Setup
## System packages
sudo apt install -y python3 python3-venv docker.io git patch
## Backend (choose one)
- Ollama (recommended): `curl -fsSL https://ollama.com/install.sh | sh && ollama serve &`
- llama.cpp server: `llama-server -m model.gguf --port 8080`
- vLLM: `python -m vllm.entrypoints.openai.api_server --model PATH --port 8000`
- Any OpenAI-compatible local server: set `DEVMIND_LLM_BASE_URL`
## Models
For vps_no_gpu profile: `ollama pull qwen2.5-coder:7b && ollama pull nomic-embed-text`
