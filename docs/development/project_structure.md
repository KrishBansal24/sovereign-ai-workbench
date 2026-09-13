# Project Structure

The Sovereign AI Workbench consists of a FastAPI backend and a Textual TUI. 
Start with `backend/app/main.py`, which configures logging and mounts routes. `app.core.config.Settings` loads local-only configuration, including local models, RAG parameters, `RAG_MIN_SIMILARITY`, and `AGENT_MAX_STEPS`.

## Core Directories

```text
sovereign-ai-workbench/
├── backend/
│   ├── app/                # FastAPI backend source
│   │   ├── api/routes/     # HTTP endpoints that validate requests and delegate work
│   │   ├── agents/         # Bounded planner/controller loop and decision schemas
│   │   ├── core/           # Environment-backed settings and logging setup
│   │   ├── schemas/        # Shared API request and response contracts
│   │   ├── services/       # Core domain logic
│   │   └── tools/          # Registered tool schemas and controlled execution
│   ├── tui/                # Textual Terminal UI presentation client
│   ├── tests/              # Pytest suite
│   └── requirements.txt    # Python dependencies
├── docs/                   # Markdown documentation (this folder)
├── tools/                  # Developer utilities and verification scripts
├── README.md               # Main project entry point
└── .gitignore              # Source control exclusions
```

## Backend Services

The `backend/app/services/` directory is organized by domain:
- `llm/`: Local Ollama client, model inventory, classification, and routing.
- `documents/`: Local document storage, UUID assignment, and deterministic format parsers (PDF, DOCX, TXT, CSV, Markdown).
- `knowledge/`: Chunking, embeddings, FAISS persistence, and RAG retrieval.
- `multimodal/`: OCR quality/reliability checks and local vision analysis.
- `data/`: Data Analysis execution and deterministic calculation engines.
- `sandbox/`: Bounded Python execution subprocess.
- `deliverable/`: Artifact generation (charts, XLSX, DOCX).
- `jobs/`: Opaque, server-generated job progress tracking.

## Tests

The test modules remain flat in `backend/tests/`. Each test module maps directly to an API or domain workflow (e.g., `test_tui_app.py`, `test_agent_tools.py`, `test_ollama_service.py`).

## Tools & Utilities

Standalone development and verification scripts (such as test manual setups or isolated component tests) are located in `tools/development/`.

## Where New Code Belongs

- **New REST API Endpoints:** Add to `backend/app/api/routes/`.
- **New Core Capabilities:** Create a new module in `backend/app/services/` and expose via API routes.
- **New Agent Actions:** Define the Pydantic schema in `backend/app/tools/schemas.py`, implement the executor in `backend/app/tools/executor.py`, and register it in `backend/app/tools/registry.py`.
- **New TUI Screens:** Add the screen in `backend/tui/screens/` and the UI components in `backend/tui/widgets/`. Ensure **no business logic** leaks into the TUI.
