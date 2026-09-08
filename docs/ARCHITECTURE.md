# Architecture

## Current architecture — implemented

```text
API Client
  ↓
FastAPI routes and Pydantic schemas
  ↓
Ollama service
  ↓
Local Ollama API (localhost only)
  ↓
Configured Qwen3 8B model
```

Routes own HTTP concerns; `OllamaService` owns local runtime requests; `core/config.py` owns environment settings. This separation prevents API routes from becoming tied to a model or HTTP client.

## Target architecture — planned

```text
Frontend → FastAPI → Task Router → Model Manager → Agent Engine → Tools
                                                               ├─ Document processing
                                                               ├─ Local RAG
                                                               ├─ OCR and vision
                                                               ├─ Python sandbox
                                                               └─ Deliverable generation
```

## Principles

- **Local-first:** inference is constrained to localhost in Phase 1.
- **Model-agnostic:** `OLLAMA_MODEL` is configuration, not route logic.
- **Modular:** routes, schemas, services, and core utilities are separated.
- **Hardware-aware:** the initial development target is an RTX 3050 with 6 GB VRAM.
- **Secure and fail-safe:** service failures return safe API errors; prompts/responses are not logged.
- **Observable:** logs carry endpoint, model, duration, outcome, and error type.
