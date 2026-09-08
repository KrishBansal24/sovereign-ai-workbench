# API Reference — Phase 1

Base URL: `http://127.0.0.1:8000`.

## `GET /api/health`

Purpose: diagnose backend, local Ollama, and configured-model availability. It returns HTTP 200 even if Ollama is unavailable because the FastAPI backend is still reachable.

Example response:

```json
{"backend":"online","ollama":"available","model":"qwen3:8b","model_status":"available","mode":"local"}
```

`ollama` can be `unavailable`; `model_status` is then `unavailable` because it cannot be verified.

## `POST /api/chat`

Purpose: submit a message to the configured local Ollama model.

Request:

```json
{"message":"Explain what a P&ID is."}
```

Successful response:

```json
{"response":"...","model":"qwen3:8b","processing":"local"}
```

An empty or missing message returns 422. Unavailable Ollama returns 503. A missing configured model returns 404. An invalid/unexpected local runtime response returns 502. Swagger at `/docs` supplies the live OpenAPI schema.
