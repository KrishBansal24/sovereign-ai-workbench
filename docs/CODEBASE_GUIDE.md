# Codebase Guide

Start with `backend/app/main.py`, which configures logging and mounts routes.
`app.core.config.Settings` loads local-only configuration, including local
models, RAG parameters, `RAG_MIN_SIMILARITY`, and `AGENT_MAX_STEPS`.

- Basic chat: `api.routes.chat.chat` -> `OllamaService.chat` -> local Ollama.
- Upload: `documents.upload_document` -> `DocumentService.upload` -> selected
  PDF/DOCX/TXT parser -> UUID-named local storage and metadata.
- Model routing: `auto_chat.auto_chat` -> `TaskClassifier` -> `ModelRouter` ->
  `ModelManager` -> `OllamaService`.
- Indexing: `knowledge.index_document` -> `KnowledgeService.index` -> chunking
  -> local embeddings -> `VectorStoreService.replace_document`.
- RAG answer: `knowledge.ask_knowledge` -> `KnowledgeService.search` ->
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
