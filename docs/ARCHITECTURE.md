# Architecture

`app.main` composes FastAPI routes, schemas validate API input, and services
own local Ollama integration, model routing, documents, and RAG.

```text
Route -> Pydantic validation -> service -> local persistence or localhost Ollama
```

Documents flow through `DocumentService` and deterministic PDF, DOCX, and TXT
parsers. RAG chunks document text, embeds it through local Ollama, and searches
L2-normalized FAISS `IndexFlatIP` vectors (cosine similarity for non-zero rows).

Phase 3 model selection is `TaskClassifier -> ModelRouter -> ModelManager ->
OllamaService`, restricted to registered roles and localhost-only configuration.

Phase 5 adds a bounded local agent:

```text
Goal -> AgentPlanner -> strict decision -> tool registry/schema -> ToolExecutor
     -> untrusted observation -> AgentPlanner -> final answer or controlled stop
```

The controller enforces `AGENT_MAX_STEPS`, blocks repeated normalized calls,
preserves backend-created source IDs, and emits safe audit metadata without
logging prompts, documents, observations, answers, or chain-of-thought.
