# API Reference

Base URL: `http://127.0.0.1:8000`; live OpenAPI documentation is `/docs`.

- `GET /api/health` reports backend and local Ollama/model availability.
- `POST /api/chat` accepts `{"message":"..."}` for the configured local model.
- `POST /api/chat/auto` classifies work and routes it to a registered local
  general or coding model.
- `POST /api/documents/upload` accepts a PDF, TXT, or DOCX multipart `file`.
- `GET /api/documents`, `GET /api/documents/{id}`, and
  `GET /api/documents/{id}/text` expose controlled document metadata/text.
- `POST /api/knowledge/documents/{id}/index` creates local RAG entries.
- `POST /api/knowledge/search` accepts `{"query":"...","top_k":5}` and
  returns source-traceable chunks with cosine-similarity scores.
- `POST /api/knowledge/ask` accepts `{"question":"..."}` for a local,
  context-grounded answer.
- `GET /api/tools` lists the fixed controlled tool registry.
- `POST /api/agent/run` accepts `{"goal":"..."}` and returns a bounded
  planner/tool trace, backend-derived sources, and an optional stop reason.

Agent tool names and arguments are not executable API input. They are selected
by the local planner, then validated against the fixed registry and Pydantic
tool schemas before `ToolExecutor` performs an explicit local operation.
