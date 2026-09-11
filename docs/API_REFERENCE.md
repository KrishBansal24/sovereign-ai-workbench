# API Reference

Base URL: `http://127.0.0.1:8000`; live OpenAPI documentation is `/docs`.

`GET /verify` serves a temporary local developer interface. It is not the
Phase 9 production frontend and calls only the controlled APIs listed here.

- `GET /api/health` reports backend and local Ollama/model availability.
- `POST /api/chat` accepts `{"message":"..."}` for the configured local model.
- `POST /api/chat/auto` classifies work and routes it to a registered local
  general or coding model.
- `POST /api/documents/upload` accepts a PDF, TXT, DOCX, PNG, or JPEG multipart
  `file` and returns safe extraction reliability metadata plus an optional job ID.
- `GET /api/documents`, `GET /api/documents/{id}`, and
  `GET /api/documents/{id}/text` expose controlled document metadata/text.
- `POST /api/knowledge/documents/{id}/index` creates local RAG entries.
- `POST /api/documents/{id}/confirm-extraction` accepts
  `{"field_or_token":"...","selected_source":"ocr|vision|manual","manual_value":"..."}`
  for a server-recorded isolated disagreement.
- `GET /api/jobs/{job_id}` returns safe status, stage, message, and approximate
  progress for long local processing; it never exposes content or paths.
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
