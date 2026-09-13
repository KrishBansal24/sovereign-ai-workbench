# Testing

The Sovereign AI Workbench uses `pytest` for its automated regression testing. 
Tests are designed to verify the deterministic backend logic without requiring a live Ollama GPU instance during the test run (models and embeddings are mocked in the test environment).

## Running the Suite

Ensure you are in the `backend/` directory with the virtual environment activated.

```powershell
pytest
```

## Test Coverage

The test suite covers all major capabilities and security boundaries:

- **TUI Tests:** Verifies the Textual client's state transitions, file ingestion dialogs, and job polling mechanisms.
- **Natural-Language Data:** Validates the schema extraction, intent mapping, and deterministic fallback calculation pipelines.
- **Knowledge / RAG:** Ensures chunks are generated, vector cosine similarity thresholds are respected, and insufficient evidence correctly halts generation.
- **OCR / Vision:** Tests the reliability grading engine and ensures corrupted text (`review_required`) is appropriately gated from indexing.
- **Sandbox Execution:** Validates process isolation, timeout enforcement, and correct parsing of standard output/error.
- **Agent Orchestration:** Ensures the bounded `Plan-Act-Observe-Decide` loop halts at `AGENT_MAX_STEPS`, successfully validates allowed tools, and prevents repeated redundant executions.
- **Artifact Generation:** Validates that charts, XLSX, and DOCX files are successfully generated on the disk and tracked in the registry.

## Expectations

- As of Phase 7, the test suite baseline is exactly **85 passing tests**.
- Any test failure is treated as a critical block for a release checkpoint.
- Do not add "skip" decorators simply to bypass test failures. All tests must pass locally.
