# Getting Started

This guide details how to set up the Sovereign AI Workbench for local development.

## Prerequisites

- **OS:** Windows (preferred for current development)
- **Python:** 3.10 or higher
- **Ollama:** Installed locally
- **Hardware:** A GPU with at least 6GB VRAM (e.g., RTX 3050) is recommended for acceptable local inference latency.

## 1. Install and Pull Local Models

The workbench relies on local Ollama models. The default configuration uses the following:

```powershell
# Reasoning and general chat
ollama pull qwen3:8b

# Coding and structured extraction
ollama pull qwen2.5-coder:7b

# Multimodal / Vision
ollama pull llava:7b

# Embeddings (RAG)
ollama pull nomic-embed-text
```

## 2. Python Environment Setup

Create a virtual environment and install dependencies:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Configuration

Copy the example environment file:
```powershell
Copy-Item .env.example .env
```
By default, the `.env` connects to `http://127.0.0.1:11434`. Do not expose the backend or Ollama to the public internet during development.

## 4. Run the Backend

Start the FastAPI server:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-exclude "data/**"
```

The API will be available at `http://127.0.0.1:8000`. 
Swagger documentation is available at `http://127.0.0.1:8000/docs`.

## 5. Run the Terminal UI (TUI)

Open a **new** PowerShell window to run the TUI:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m tui
```

*(Note: The old HTML `/verify` UI is deprecated in favor of the TUI.)*

## 6. Running Tests

To run the automated test suite (does not require Ollama to be running):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```
