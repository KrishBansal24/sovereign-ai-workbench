# Architecture Overview

`app.main` composes FastAPI routes, schemas validate API input, and services own local Ollama integration, model routing, documents, and RAG.

## Service Boundaries

```text
services/
├── llm/          Ollama HTTP integration, model registry, classifier, router
├── documents/    controlled upload storage and PDF/DOCX/TXT/Markdown/CSV parser boundary
├── knowledge/    chunking, embedding, FAISS index persistence, grounded search
├── multimodal/   OCR preprocessing/quality, reliability decisions, vision model
├── data/         Data Analysis intent mapping, calculation engine, operations
├── sandbox/      Bounded Python execution for isolated code tasks
├── agents/       Agent planner, execution loop, strict decisions
└── jobs/         Job progress and status tracking
```

Routes import the appropriate domain service rather than a flat, unrelated service module. `documents` may call `multimodal` extraction services; the knowledge domain consumes accepted document text; the LLM domain is the sole integration boundary for local model selection and Ollama requests.

For operations where status is useful, `services.jobs.JobProgressService` creates opaque server-generated IDs and stores only status, stage, message, timestamps, and optional approximate progress. `GET /api/jobs/{job_id}` is the frontend contract; it intentionally reveals no document bytes, paths, prompts, hidden reasoning, or environment values.

```text
Route -> Pydantic validation -> service -> local persistence or localhost Ollama
```

Documents flow through `services.documents.DocumentService` and deterministic PDF, DOCX, TXT, CSV, and Markdown parsers. RAG chunks document text, embeds it through local Ollama, and searches L2-normalized FAISS `IndexFlatIP` vectors (cosine similarity for non-zero rows).

Phase 3 model selection is `llm.TaskClassifier -> llm.ModelRouter -> llm.ModelManager -> llm.OllamaService`, restricted to registered roles and localhost-only configuration.

Phase 5 adds a bounded local agent:

```text
Goal -> AgentPlanner -> strict decision -> tool registry/schema -> ToolExecutor
     -> untrusted observation -> AgentPlanner -> final answer or controlled stop
```

## Terminal Presentation Layer

`backend/tui` is a separate Textual client. Its asynchronous API client calls existing FastAPI routes and its job poller consumes server-created state only. It can read client-selected files for multipart upload and save downloaded artifacts, but contains no backend business rules. The TUI acts purely as a presentation layer; it respects the backend as the definitive source of validation, reliability state, and knowledge access.

The controller enforces `AGENT_MAX_STEPS`, blocks repeated normalized calls, preserves backend-created source IDs, and emits safe audit metadata without logging prompts, documents, observations, answers, or chain-of-thought.

## Phase 7 Execution and Artifacts

Phase 7 adds `sandbox_service`, `data_analysis_service`, and `deliverable_service`. Structured specifications or code flow through schema validation, a local generator or subprocess, post-generation validation, central artifact registration, and a safe tool observation. Sandbox workspaces are deleted after runs; this is process/workspace isolation, not a hardened Phase 8 container/VM boundary.

## Local AI Integration

```text
Application → localhost Ollama API → Qwen3 8B → GPU
```

FastAPI provides the workbench API. Ollama manages the local model runtime and HTTP interface. Qwen3 is the initial configured reasoning model. Ollama is infrastructure beneath the workbench, not the workbench product.

The Ollama service abstraction lets future model-management work change runtimes or models without rewriting routes. `OLLAMA_MODEL` is configured externally, so Qwen3 is not permanently coupled to the application.

Phase 3 registers multiple roles such as `GENERAL_MODEL` (e.g. `qwen3:8b`), `CODING_MODEL` (e.g. `qwen2.5-coder:7b`), `VISION_MODEL` (e.g. `llava:7b`), and `EMBEDDING_MODEL` (e.g. `nomic-embed-text`). Ollama manages loading and unloading; the workbench does not attempt to keep all models resident in VRAM. Switching may add latency.

The current Windows development machine uses an RTX 3050 with 6 GB VRAM. This favors appropriately quantized models and modest context sizes. A future enterprise deployment may use more capable organization-controlled GPU infrastructure; that is planned, not implemented.
