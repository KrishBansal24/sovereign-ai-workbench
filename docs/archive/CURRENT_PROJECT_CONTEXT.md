# Current project context

## Identity and guardrails

Sovereign On-Premise Agentic AI Workbench is a local-first FastAPI application
with the Textual **Sovereign Terminal Workbench** as its primary UI. Do not add
cloud AI dependencies, telemetry, arbitrary shell or filesystem access, Phase
8 security work, React, commits, or pushes. Phase 7 is **implemented and
awaiting user manual verification**; it must not be marked verified.

## Current worktree

- Branch: `main`; HEAD `5810bb7`.
- Nothing staged.
- Uncommitted work is a substantial Phase 7 / Textual UI implementation:
  21 modified tracked files and untracked routes, schemas, services, tests,
  `backend/tui/`, and Phase 7/TUI documentation.
- Preserve all of it. Runtime `.env`, `backend/data/`, caches, and `venv/` are
  ignored generated/local state.

## Architecture

- `backend/app/main.py`: FastAPI composition.
- `app/core/config.py`: local-only Ollama validation and configuration.
- `app/services/llm`: configured general/coding/vision registry, deterministic
  classifier/router, localhost Ollama client. Default model names are Qwen3
  8B, Qwen2.5 Coder 7B, LLaVA 7B, and nomic embeddings; actual deployment
  values are environment-driven.
- `app/services/documents`: UUID-controlled upload storage, metadata/text JSON,
  PDF/DOCX/TXT/CSV/XLSX/image extraction; PDFs are page-aware and OCR bounded.
- `app/services/knowledge`: chunking, local embeddings, persistent normalized
  FAISS vectors, provenance-aware search and grounded answers.
- `app/agents` + `app/tools`: bounded planner / fixed schema-validated tool
  loop, repeat-call guard, safe trace (no chain of thought). Registered tools:
  knowledge search, metadata/text reads, calculator, Python sandbox, data
  analysis, chart/XLSX/DOCX/PPTX/PDF generation.
- `app/services/multimodal`: OCR quality, optional vision cross-check,
  reliability state and human-confirmation workflow. Index eligibility remains
  backend-authoritative.
- `app/services/jobs.py`: thread-safe but in-memory stage/progress records;
  jobs disappear after restart. Upload, sandbox, and analysis create jobs.
  Indexing, agent, and vision are currently synchronous and have no job
  progress.
- Phase 7 services: artifact UUID storage/metadata/download;
  CSV/XLSX analysis by managed document/artifact ID; deterministic validated
  chart/XLSX/DOCX/PPTX/PDF generators; restricted Python subprocess.

## Sandbox facts

`sandbox_service` validates AST, blocks selected dangerous imports/names,
runs `python -I -B` without a shell in a temporary workspace, uses a small
environment, timeout/output/file/artifact limits, registers validated files,
then deletes the workspace. It is **not** a VM/container/OS sandbox: code has
the service account's OS permissions and networking is not kernel-enforced.

## TUI

`backend/tui/app.py` is a one-file Textual UI with Dashboard, Agent,
Documents, Knowledge, OCR/Vision, Data, Sandbox, Artifacts, Jobs, Models,
Settings, and Help panels. `tui/services/api_client.py` centralizes async local
HTTP/multipart/download calls; `file_ingest.py` scans client-selected folders
only (no symlinks, caps supported files at 500); `job_poller.py` uses real
backend status; `state/progress.py` holds batch item state. State is mostly
held in app dictionaries and current widgets, so screen navigation retains
some selections/results but is not a formal state store.

The current UX pass uses PageHeader/ResultPanel components, a compact local
status bar, workflow pages, upload and deliverable dialogs, friendly job
metadata, dataset pickers, guided analysis forms, and artifact forms. Data and
deliverable creation no longer require normal users to type JSON, while the
backend schemas remain unchanged. OCR confirmation controls mount only for a
selected document with a backend-reported pending disagreement. The UI is still
intentionally a single `tui/app.py` module, but is organized around reusable
presentation components and centralized API calls.

## Routes

Current API prefixes: health `/api/health`; chat `/api/chat`; auto chat
`/api/chat/auto`; models `/api/models`; documents `/api/documents` (including
upload, upload-job, metadata/text/delete/confirmation); knowledge
`/api/knowledge` (index/list/remove/search/ask); agent `/api/agent` and
`/api/tools`; vision `/api/vision`; jobs `/api/jobs`; sandbox `/api/sandbox`;
analysis `/api/analysis`; deliverables `/api/deliverables`; artifacts
`/api/artifacts`. `/verify` is the developer verification surface.

## Data ownership

Persistent local files sit beneath `backend/data`: document originals/text/
metadata, FAISS vectors/index/metadata, and UUID-prefixed artifacts plus
metadata. Sandbox workspaces are ephemeral. Jobs are memory-only.

## Baseline and documentation

There are 37 tests in `backend/tests` covering API, documents, RAG, routing,
agent safety, OCR/reliability, jobs, Phase 7 contracts, and TUI utilities.
On 2026-09-12 the intended command
`backend/venv/Scripts/python.exe -m pytest -q` did not start because the venv
points at an unavailable/inaccessible Python 3.14 executable. Therefore no
pass/fail baseline is available yet; do not treat it as a test failure.

`docs/PHASE_7_IMPLEMENTATION.md` and `docs/TERMINAL_UI.md` describe the active
uncommitted implementation. `README.md` correctly says Phase 7 awaits manual
verification, but some Phase 6 wording in repository docs is stale relative to
the project handoff (which says Phase 6 was verified).
