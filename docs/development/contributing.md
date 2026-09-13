# Contributing Guidelines

This document outlines the coding standards, architecture principles, and contribution expectations for the Sovereign AI Workbench.

## Python Conventions

- **Docstrings:** Every production module must begin with a docstring that describes its responsibility and its place in the application boundary. Public classes and non-trivial functions use docstrings explaining inputs, outputs, error behavior, and invariants.
- **Typing:** Production signatures use explicit parameter and return annotations. Prefer concrete types (`list[str]`, `dict[str, str]`, Pydantic models, `Literal`, `T | None`) over untyped containers.
- **Tests:** Tests prioritize descriptive names and readable setup. Shared helpers are typed and documented.
- **Naming:** Use descriptive names for domain values (`document_id`, `embedding_model`, `selected_model`).

## API and Schema Architecture

- **Backend Authority:** The backend is the single source of truth for validation, reliability states, and business logic. The TUI and any future frontend must remain thin presentation layers.
- **Thin Routes:** FastAPI routes validate request data, delegate immediately to a domain service, map service errors to HTTP responses, and return a declared Pydantic response model.
- **Separation of Concerns:** Do not place document parsing, model selection, retrieval algorithms, or direct persistence logic inside a route.

## Comments and Security Boundaries

Use concise `SECURITY:` comments at genuine trust boundaries:
- `Settings` rejects non-loopback Ollama endpoints.
- `DocumentService` treats uploads and filenames as untrusted and strictly controls validation and storage paths.
- `ModelRouter` accepts only registered model IDs, never arbitrary model tags.
- RAG passes strict retrieved local context to the grounded-answer prompt and prevents hallucination.
- `ToolExecutor` treats agent tool names and arguments as untrusted; only fixed registry entries may execute. Dynamic imports, `eval`, `exec`, or `shell=True` subprocesses are strictly prohibited.
- `AgentController` returns operational steps and source references, never hidden prompts or chain-of-thought logic.

## Change Discipline

1. **Preserve Behavior:** Preserve existing Phase 7 behavior unless a verified defect requires a fix. 
2. **Safe Refactoring:** Do not add architecture merely to satisfy documentation goals.
3. **No Private Leakage:** Do not expose private implementation details, exact file paths, or stack traces in API responses.
4. **Test Expectations:** Always run the complete pytest suite before committing. Do not weaken tests.
5. **Documentation Updates:** When modifying core workflows or schemas, update the relevant `docs/features/` or `docs/architecture/` files to match the codebase. **The codebase is the source of truth.**
