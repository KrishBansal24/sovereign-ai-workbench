# Sovereign AI Workbench

A self-hosted, local-first, agentic AI workbench for confidential industrial environments where sensitive documents, operational data, scanned records, engineering drawings, calculations, and internal knowledge must remain on-premise.

The Sovereign AI Workbench is explicitly designed for local-only and air-gapped deployments. By processing all logic and intelligence locally, the workbench guarantees absolute data sovereignty.

## Key Capabilities

- **Local-First Architecture:** Complete offline operation with no external cloud AI providers.
- **Multimodal Document Ingestion:** Natively parses PDF, DOCX, TXT, CSV, and Markdown. Treats uploaded Python source code strictly as inert, unexecuted text.
- **OCR & Vision Reliability:** Assesses the quality of scanned documents using OCR and Vision fallback (`llava`), categorizing extractions into strict human-in-the-loop review states to prevent "garbage in, garbage out".
- **Local Knowledge / RAG:** FAISS vector store powered by local embeddings (`nomic-embed-text`) providing grounded, cited answers and strict hallucination prevention (insufficient-evidence refusal).
- **Deterministic Data Analysis:** Translates natural language into strict JSON intents and executes them deterministically in pandas, preventing LLM arithmetic hallucinations.
- **Safe Python Sandbox:** Ephemeral, isolated subprocess execution for bounded code execution with strict timeouts.
- **Agent Orchestration:** A bounded Plan-Act-Observe-Decide loop powered by local reasoning models (`qwen3`), constrained to an allowlist of backend-authoritative tools with prompt-injection resistance.
- **Artifact Generation:** Generates offline deliverables (Charts, Excel Workbooks, Word Documents) directly from deterministic data or Agent insight.
- **Professional Terminal UI (TUI):** A rich, keyboard-driven Textual console interface for operating the system securely from the terminal.

## Architecture

The system uses a strict client-server separation where the FastAPI backend enforces all business rules, validation, and execution boundaries. The Terminal UI is a thin presentation layer.

```text
User
 │
 ▼
Textual Terminal Workbench (TUI)
 │
 ▼
FastAPI Backend (Authoritative Validation & Policy)
 │
 ├── Documents & Extractors
 ├── Knowledge / RAG
 ├── OCR / Vision
 ├── Data Analysis
 ├── Python Sandbox
 ├── Agent Controller
 ├── Artifact Service
 └── Jobs & Progress
 │
 ▼
Local Model Layer / Ollama Integration
 │
 ├── Reasoning (e.g. qwen3:8b)
 ├── Coding (e.g. qwen2.5-coder:7b)
 ├── Vision (e.g. llava:7b)
 └── Embeddings (e.g. nomic-embed-text)
 │
 ▼
Local Storage / FAISS Vector Index / Ephemeral Runtime Workspaces
```

## Configured Models

The backend is model-agnostic and relies on specific roles that can be configured via environment variables. The default roles are:
- **Reasoning (`GENERAL_MODEL`):** `qwen3:8b`
- **Coding (`CODING_MODEL`):** `qwen2.5-coder:7b`
- **Vision (`VISION_MODEL`):** `llava:7b`
- **Embeddings (`EMBEDDING_MODEL`):** `nomic-embed-text`

## Project Structure

```text
sovereign-ai-workbench/
├── backend/
│   ├── app/                # FastAPI backend logic and domain services
│   ├── tui/                # Textual Terminal UI presentation client
│   └── tests/              # Comprehensive pytest suite
├── docs/                   # Detailed project documentation (see Documentation Index)
├── tools/                  # Developer utilities and verification scripts
├── README.md               # This entry point
└── .gitignore              # Source control exclusions
```

## Quick Start

### 1. Prerequisites & Models
Ensure Python 3.10+ and Ollama are installed. Pull the required models:
```powershell
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b
ollama pull llava:7b
ollama pull nomic-embed-text
```

### 2. Install Dependencies
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 3. Run Backend
Start the local FastAPI server:
```powershell
uvicorn app.main:app --reload --reload-exclude "data/**"
```
*(Swagger UI is available at `http://127.0.0.1:8000/docs`)*

### 4. Run Terminal Workbench
In a new terminal window:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m tui
```

### 5. Run Tests
Verify the installation by running the test suite:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```

## Demo Workflow

1. **Start** the local backend and the Terminal Workbench.
2. **Upload** confidential P&IDs, operational manuals, and CSV datasets in the Documents tab.
3. **Review** the OCR/Vision status for scans; manually approve `review_required` items.
4. **Index** trusted documents to the Knowledge base.
5. **Analyze** the operational CSV data using natural language in the Data tab.
6. **Ask the Agent** to investigate anomalies in the data, cross-reference the manual, and create a comparison chart and maintenance report.
7. **Save** the generated artifacts to your local disk for offline distribution.

## Security Model Summary

Sovereign AI operates under strict security boundaries:
- **Local Inference:** No cloud provider required; no data leaves the network.
- **Backend-Authoritative:** The TUI cannot dictate state. All inputs and tool calls are schema-validated.
- **Restricted Execution:** The Python Sandbox executes in a strictly bounded, timed-out subprocess without arbitrary shell access.
- **Gated Knowledge:** Unreliable or garbled OCR scans are prohibited from polluting the RAG index until reviewed by a human.
- **Prompt Injection Boundaries:** The Agent selects tools from a hardcoded allowlist, and observations are sanitized to prevent data-driven prompt injections.

For full technical details, see the [Security Model](docs/architecture/security_model.md).

## Documentation Index

**Project Context**
- [Problem Statement](docs/project/problem_statement.md)
- [Phase 7 Summary](docs/project/phase7_summary.md)
- [Known Limitations](docs/project/limitations.md)

**Architecture**
- [Architecture Overview](docs/architecture/overview.md)
- [Request Flows](docs/architecture/request_flows.md)
- [Agent Architecture](docs/architecture/agent_architecture.md)
- [Security Model](docs/architecture/security_model.md)

**Features**
- [Documents](docs/features/documents.md)
- [Knowledge / RAG](docs/features/knowledge_rag.md)
- [OCR / Vision](docs/features/ocr_vision.md)
- [Data Analysis](docs/features/data_analysis.md)
- [Python Sandbox](docs/features/sandbox.md)
- [Agent Orchestration](docs/features/agent.md)
- [Artifact Generation](docs/features/artifacts.md)
- [Terminal UI (TUI)](docs/features/tui.md)

**Development & Verification**
- [Getting Started](docs/development/getting_started.md)
- [Project Structure](docs/development/project_structure.md)
- [Configuration](docs/development/configuration.md)
- [Testing](docs/development/testing.md)
- [Contributing](docs/development/contributing.md)
- [Phase 7 Verification](docs/verification/phase7_verification.md)
- [TUI End-to-End Verification](docs/verification/tui_end_to_end.md)
