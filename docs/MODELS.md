# Local Model Guide

| Hardware profile | Suggested models |
|---|---|
| cpu_minimal (<8GB) | llama3.2:3b, phi3:mini, gemma2:2b |
| cpu_low (8-12GB) | qwen2.5-coder:7b, mistral:7b, llama3.1:8b |
| cpu_standard / vps_no_gpu | qwen2.5-coder:7b + llama3.1:8b + nomic-embed-text |
| cpu_high (32GB+) | deepseek-coder-v2:16b, qwen2.5:14b |
| gpu_high (16GB+ VRAM) | mixtral:8x7b, qwen2.5:32b, codellama:34b |

Task-type routing:
- CODING/FIX/TEST -> best code-specialized model
- PLANNING/DEBUG -> largest reasoning model
- REVIEW/DOC -> smallest capable model (to save RAM)
- EMBEDDING -> nomic-embed-text (preferred) or sentence-transformers fallback
