# Architecture

Status: Phase 1 and Phase 2 are complete and verified. Phase 3 is next; Phases 4–10 are planned.

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

## Document ingestion architecture — implemented in Phase 2

```text
Upload → validation → generated document ID → local storage → selected parser → extracted text + JSON metadata
```

`DocumentService` owns storage and metadata; parsers extract PDF, TXT, and DOCX text deterministically. FastAPI routes only handle HTTP input/output. Files are stored by UUID rather than raw filename, and extracted text is stored separately from metadata. This is deliberately reusable by planned RAG, OCR, vision, and agent tools.

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
- **Content-safe:** document logs contain only IDs, type, size, duration, and character count—not extracted text.
