# Configuration

The Sovereign AI Workbench is configured using environment variables defined in the `.env` file located in the `backend/` directory.

## Core Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | The URL of the local Ollama instance. **SECURITY:** Must remain a loopback/localhost address. |
| `OLLAMA_TIMEOUT_SECONDS` | `300` | Timeout for Ollama inference requests. |
| `LOG_LEVEL` | `INFO` | Standard application logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

## Model Overrides
The backend defines roles for models rather than hardcoding names throughout the codebase. While these default to sensible local models, they can be overridden in `.env`:

| Variable | Default Value | Description |
|---|---|---|
| `OLLAMA_MODEL` / `GENERAL_MODEL` | `qwen3:8b` | Primary reasoning and chat model. |
| `CODING_MODEL` | `qwen2.5-coder:7b` | Specialized model for structured intent mapping and Python generation. |
| `VISION_MODEL` | `llava:7b` | Multimodal model used for OCR fallback and image comprehension. |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Dense embedding model used for RAG FAISS vectors. |

## Constants & Constraints
Certain architectural limits are defined in `app.core.config.Settings` (and can be exposed via `.env` if needed):
- `AGENT_MAX_STEPS = 10`: The maximum number of tool executions the agent is allowed before a forced controlled stop.
- `RAG_MIN_SIMILARITY = 0.50`: The baseline cosine similarity threshold for FAISS vector retrieval.

## Security Warning
- Do **not** commit `.env` files or API keys (though this system is designed to run entirely locally without external API keys).
- Do not expose `OLLAMA_BASE_URL` to external networks in development mode.
