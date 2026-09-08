# Phase 1 Implementation

## Objective and result

Phase 1 established a maintainable local LLM backend. It is implemented and manually verified.

## Design

`app/main.py` creates FastAPI and includes route modules. `api/routes/chat.py` validates and serves chat requests. `services/ollama_service.py` calls Ollama. `core/config.py` loads `.env`/environment configuration and limits the Ollama URL to loopback hosts. `core/logging_config.py` configures metadata-only logs.

## APIs and schemas

- `GET /api/health` reports `backend`, `ollama`, `model`, `model_status`, and `mode`. It remains HTTP 200 when Ollama is down so it can diagnose a live backend.
- `POST /api/chat` accepts a non-empty `message` (1–20,000 characters) and returns `response`, `model`, and local processing mode.

## Service behavior

The service checks Ollama through `/api/tags`, checks whether the configured model appears in that response, and sends chat messages to `/api/chat`. Connectivity/timeout, missing-model, bad upstream response, and malformed-response conditions map to safe API responses. Raw stack traces are not returned to users.

## Logging and tests

Logs record request lifecycle metadata, endpoint, selected model, duration, outcome, and error type. Full prompts and responses are not logged. Tests mock the service to cover health, empty-message validation, successful chat, and unavailable Ollama without requiring Qwen3.

## Start and verify

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
pytest
```

Use Swagger at `/docs`; run `GET /api/health`; then send a request to `POST /api/chat`.

## Limitations

Only one configured local model is supported. There is no document ingestion, OCR, vision, RAG, agent loop, authentication, frontend, enterprise audit trail, or enforced network air gap.
