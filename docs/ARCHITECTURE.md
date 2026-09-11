# Architecture

`app.main` composes FastAPI routes, schemas validate API input, and services
own local Ollama integration, model routing, documents, and RAG.

## Service boundaries

```text
services/
├── llm/          Ollama HTTP integration, model registry, classifier, router
├── documents/    controlled upload storage and PDF/DOCX/TXT parser boundary
├── knowledge/    chunking, embedding, FAISS index persistence, grounded search
└── multimodal/   OCR preprocessing/quality, reliability decisions, vision model
```

Routes import the appropriate domain service rather than a flat, unrelated
service module. `documents` may call `multimodal` extraction services; the
knowledge domain consumes accepted document text; the LLM domain is the sole
integration boundary for local model selection and Ollama requests.

For operations where status is useful, `services.jobs.JobProgressService`
creates opaque server-generated IDs and stores only status, stage, message,
timestamps, and optional approximate progress. `GET /api/jobs/{job_id}` is the
future frontend contract; it intentionally reveals no document bytes, paths,
prompts, hidden reasoning, or environment values.

```text
Route -> Pydantic validation -> service -> local persistence or localhost Ollama
```

Documents flow through `services.documents.DocumentService` and deterministic PDF, DOCX, and TXT
parsers. RAG chunks document text, embeds it through local Ollama, and searches
L2-normalized FAISS `IndexFlatIP` vectors (cosine similarity for non-zero rows).

Phase 3 model selection is `llm.TaskClassifier -> llm.ModelRouter ->
llm.ModelManager -> llm.OllamaService`, restricted to registered roles and
localhost-only configuration.

Phase 5 adds a bounded local agent:

```text
Goal -> AgentPlanner -> strict decision -> tool registry/schema -> ToolExecutor
     -> untrusted observation -> AgentPlanner -> final answer or controlled stop
```

The controller enforces `AGENT_MAX_STEPS`, blocks repeated normalized calls,
preserves backend-created source IDs, and emits safe audit metadata without
logging prompts, documents, observations, answers, or chain-of-thought.
