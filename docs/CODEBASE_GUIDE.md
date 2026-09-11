# Codebase Guide

Start with `backend/app/main.py`, which configures logging and mounts routes.
`app.core.config.Settings` loads local-only configuration, including local
models, RAG parameters, `RAG_MIN_SIMILARITY`, and `AGENT_MAX_STEPS`.

## Project structure

```text
backend/app/
├── api/routes/       HTTP endpoints that validate requests and delegate work
├── agents/           bounded planner/controller loop and decision schemas
├── core/             environment-backed settings and logging setup
├── schemas/          shared API request and response contracts
├── services/
│   ├── llm/          local Ollama client, model inventory, classification, routing
│   ├── documents/    local document storage plus format parsers
│   ├── knowledge/    chunking, embeddings, FAISS persistence, and RAG retrieval
│   └── multimodal/   OCR quality/reliability checks and local vision analysis
└── tools/            registered tool schemas and controlled execution
```

`schemas/jobs.py` and `services/jobs.py` provide a small thread-safe,
in-memory, stage-first progress abstraction. It is used by document processing
and is deliberately generic enough for future indexing and agent work without
exposing document content, storage paths, or configuration values.

The test modules remain flat in `backend/tests/`: each maps directly to an API
or domain workflow and the current suite is small enough that nested test
packages would add navigation rather than clarity.

- Basic chat: `api.routes.chat.chat` -> `llm.OllamaService.chat` -> local Ollama.
- Upload: `documents.upload_document` -> `documents.DocumentService.upload` -> selected
  PDF/DOCX/TXT parser -> UUID-named local storage and metadata.
- Extraction confirmation: `documents.confirm_extraction` ->
  `DocumentService.confirm_extraction` -> retained OCR/vision candidates plus
  server-validated user provenance. Only isolated technical conflicts are
  eligible; wider unreadability requires a re-upload.
- Model routing: `auto_chat.auto_chat` -> `llm.TaskClassifier` -> `llm.ModelRouter` ->
  `llm.ModelManager` -> `llm.OllamaService`.
- Indexing: `knowledge.index_document` -> `knowledge.KnowledgeService.index` -> chunking
  -> local embeddings -> `knowledge.VectorStoreService.replace_document`.
- RAG answer: `knowledge.ask_knowledge` -> `knowledge.KnowledgeService.search` ->
  routed local model using retrieved source chunks.
- Agent run: `agent.run_agent` -> `AgentController.run` -> `AgentPlanner`
  -> validated decision -> `ToolExecutor` -> safe observation -> planner again
  -> final answer or bounded stop.

`tools.registry.TOOLS` is the allow-list for knowledge, document, and calculator
operations. `ToolExecutor` validates its Pydantic input before explicit local
handlers execute. The agent preserves backend-generated sources, blocks repeated
normalized calls, applies cosine-similarity relevance gating, and never returns
chain-of-thought.

Run all tests from `backend` with:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```
