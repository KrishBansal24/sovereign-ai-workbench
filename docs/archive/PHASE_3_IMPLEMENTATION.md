# Phase 3 Implementation — Multi-Model Support & Automatic Router

Status: complete and verified. Phases 1–3 are complete and verified; Phase 4 is next.

## Design

The registry defines two configuration-driven local roles: `general` (`GENERAL_MODEL`, default `qwen3:8b`) and `coding` (`CODING_MODEL`, default `qwen2.5-coder:7b`). `ModelManager` owns registry lookup, capability lookup, and local availability. `TaskClassifier` identifies task family without logging content; `ModelRouter` maps the family to a registered role and returns short operational routing metadata.

## Routing and fallback

High-confidence signals handle coding, debugging, code explanation, document analysis, summarization, and reasoning. Ambiguous tasks intentionally select the general model. The coding role falls back to general when unavailable; no external inference or arbitrary user-selected Ollama name is possible. `POST /api/chat/auto` permits only the registered `general` or `coding` override IDs.

## APIs

- `GET /api/models` and `GET /api/models/{model_id}` report registered metadata and local availability.
- `POST /api/chat/auto` returns response text plus task type, selected model, explanation, and fallback state.

## Hardware and limitations

Ollama controls model loading/unloading on the RTX 3050 6 GB development GPU, so switching can add latency. The current classifier is deliberately lightweight and deterministic; a future phase may add an optional structured local classifier for more nuanced ambiguous work. There is no cloud fallback, RAG, OCR, vision, agent loop, or authentication.

## Tests

Mocked tests cover registry roles, task families, correct routing, coding fallback, registered override, and invalid override. They require neither actual local model nor internet.
