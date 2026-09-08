# Sovereign AI Workbench

Sovereign On-Premise Agentic AI Workbench using open-weight multimodal models for confidential industrial work. This SIH 2026 project is being developed for the Mangalore Refinery and Petrochemicals Limited (MRPL) context.

The workbench is intended to let industrial teams use AI without sending confidential operational, engineering, or business information to external AI services. It is local-first: model inference runs on organization-controlled hardware through a local runtime.

## Status

**Implemented and verified — Phase 1: Foundation & Local LLM Backend.** The current backend provides a modular FastAPI application, local Ollama integration, health/model checks, a chat API, configuration, safe logging, and unit tests.

**Complete and verified — Phase 2: Document Ingestion & Processing.** The backend stores local PDF, TXT, and DOCX uploads under generated identifiers and extracts text deterministically. OCR, RAG, vision, and LLM document analysis remain unimplemented.

**Planned — Phases 3–10.** RAG, OCR, vision, multi-model routing, agents, sandboxes, deliverable generation, a React workbench, and enterprise security controls are not implemented yet.

## Current architecture

```text
API client → FastAPI → Ollama service → localhost Ollama → Qwen3 8B → RTX 3050
```

Ollama is the local inference runtime, not the workbench itself. The configured model is environment-driven rather than embedded throughout the API.

## Technology and development hardware

- Python, FastAPI, Uvicorn, Requests, Pydantic
- Ollama with `qwen3:8b` as the initial local model
- Windows development machine with NVIDIA GeForce RTX 3050 (6 GB VRAM)

## Repository layout

```text
backend/
  app/                 FastAPI application, routes, schemas, services, and core utilities
  tests/               Phase 1 automated tests
  .env.example         Safe configuration template
  requirements.txt     Phase 1 dependencies
docs/                  Architecture, setup, API, roadmap, and security documentation
outputs/               Runtime-generated outputs (not committed)
```

## Setup and run

Prerequisites: Windows, Python, Ollama, and a locally installed model such as `qwen3:8b`.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen3:8b
uvicorn main:app --reload
```

Open Swagger at `http://127.0.0.1:8000/docs` and OpenAPI at `http://127.0.0.1:8000/openapi.json`.

The default `.env` values are local-only:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

## Implemented API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Backend, local Ollama, and configured-model status |
| `POST /api/chat` | Send a message to the configured local model |
| `POST /api/documents/upload` | Store and extract one local PDF, TXT, or DOCX file |
| `GET /api/documents` | List document metadata |
| `GET /api/documents/{document_id}` | Retrieve one document's metadata |
| `GET /api/documents/{document_id}/text` | Retrieve extracted text for development/testing |
| `DELETE /api/documents/{document_id}` | Delete the stored document, text, and metadata |

Example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType 'application/json' -Body '{"message":"Explain what a P&ID is."}'
```

## Tests

Run mocked unit tests; Ollama and Qwen3 are not required for them:

```powershell
cd backend
pytest
```

## Offline and security posture

Phase 1 rejects non-local Ollama URLs and uses no cloud AI API. Logs record operational metadata, not complete prompts or model responses. This is a foundation, not a full air-gap or enterprise security implementation; see [Security and Sovereignty](docs/SECURITY_AND_SOVEREIGNTY.md).

## Roadmap and limitations

The full phased plan is in [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md). Current limitations include one configured model, no authentication, no OCR/vision/RAG, and no frontend. Scanned or image-only PDFs report `ocr_required`; Phase 2 does not perform OCR.

## SIH 2026

This repository documents a phased, demonstrable implementation for the Smart India Hackathon 2026 problem context. It does not contain proprietary MRPL documents, credentials, model weights, or cloud inference dependencies.
