# Development Setup

## Prerequisites

Use Windows with Python, Git, Ollama, and a locally installed model. Create a virtual environment in `backend` if one does not exist.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen3:8b
uvicorn main:app --reload
```

Swagger is at `http://127.0.0.1:8000/docs`. Run `pytest` from `backend` for mocked unit tests.

## Temporary verification UI

This is a local developer verification interface, not the Phase 9 production
frontend. Start Ollama, start the backend, then open
`http://127.0.0.1:8000/verify`. Upload a document or image, inspect the
backend-provided reliability result, confirm isolated OCR/vision disagreements
when requested, index reliable text, ask RAG, and run an agent goal. The page
polls only server-issued job IDs; Swagger remains available at `/docs`.

Each action card keeps independent progress and response state. Responses stay
below their own progress panel, and `waiting_for_user` stops polling so the
confirmation controls can be used without affecting results in other cards.

## Configuration

Set `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, and `LOG_LEVEL` in `.env`. The URL must remain a loopback host. Do not commit `.env`.

## Troubleshooting

If health shows Ollama unavailable, start the Ollama service and confirm `ollama list`. A 404 chat error means the configured model is not installed. A 503 means Ollama cannot be reached or timed out. Unit tests do not need Ollama.
