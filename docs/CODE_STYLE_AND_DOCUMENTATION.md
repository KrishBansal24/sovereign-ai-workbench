# Code Style and Documentation

## Python conventions

- Every production module begins with a docstring that describes its actual
  responsibility and its place in the application boundary.
- Public classes and non-trivial functions use docstrings that explain inputs,
  outputs, error behavior, or invariants when that context helps a maintainer.
- Production signatures use explicit parameter and return annotations. Prefer
  concrete types such as `list[str]`, `dict[str, str]`, `TypedDict`, Pydantic
  models, dataclasses, `Literal`, and `T | None` over untyped containers.
- Tests prioritize descriptive names and readable setup. Shared or non-trivial
  test helpers are typed and documented; trivial tests do not need boilerplate
  docstrings.
- Use descriptive names for domain values, such as `document_id`,
  `embedding_model`, `retrieved_results`, and `selected_model`.

## API and schema conventions

- Keep FastAPI routes thin: validate request data, delegate to a service, map
  known service errors to HTTP responses, and return a declared response model
  where the existing contract supports one.
- Pydantic fields exposed through API routes should have useful descriptions
  when they clarify validation, local-only processing, or response semantics.
- Do not place document parsing, model selection, retrieval algorithms, or
  direct persistence logic inside a route.

## Comments and security boundaries

Comments explain non-obvious design constraints rather than narrating syntax.
Use concise `SECURITY:` comments at genuine trust boundaries:

- `Settings` rejects non-loopback Ollama endpoints.
- `DocumentService` treats uploads and filenames as untrusted and controls
  validation and storage paths.
- `ModelRouter` accepts only registered model IDs, never arbitrary model tags.
- RAG keeps source metadata with vectors and passes retrieved local context to
  the grounded-answer prompt.
- `ToolExecutor` treats agent/LLM tool names and arguments as untrusted; only
  fixed registry entries may execute. Dynamic imports, callable resolution,
  shell execution, `eval`, and `exec` are prohibited.
- `AgentController` returns operational steps and source references, never
  hidden prompts or chain-of-thought.

## Local RAG conventions

`ChunkingService` preserves configured overlap so context near a boundary can
be retrieved. `EmbeddingService` calls only the configured local Ollama
embedding endpoint. `VectorStoreService` L2-normalizes vectors and uses FAISS
`IndexFlatIP`, giving cosine-similarity ranking for non-zero vectors. Raw
vectors, metadata, and the FAISS sidecar remain in the configured local data
directory. `KnowledgeService` creates source-traceable chunk records and
replaces a document's prior vectors during re-indexing.

## Change discipline

Preserve existing behavior unless a verified defect requires a fix. Do not add
architecture merely to satisfy documentation goals, do not expose private
implementation details in responses, and run the relevant tests after each
logical change before the final full-suite run.
