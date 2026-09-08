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

## Configuration

Set `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, and `LOG_LEVEL` in `.env`. The URL must remain a loopback host. Do not commit `.env`.

## Troubleshooting

If health shows Ollama unavailable, start the Ollama service and confirm `ollama list`. A 404 chat error means the configured model is not installed. A 503 means Ollama cannot be reached or timed out. Unit tests do not need Ollama.
