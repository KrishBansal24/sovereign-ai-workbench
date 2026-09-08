# Local AI Architecture

```text
Application → localhost Ollama API → Qwen3 8B → GPU
```

FastAPI provides the workbench API. Ollama manages the local model runtime and HTTP interface. Qwen3 is the initial configured reasoning model. Ollama is infrastructure beneath the workbench, not the workbench product.

The Ollama service abstraction lets future model-management work change runtimes or models without rewriting routes. `OLLAMA_MODEL` is configured externally, so Qwen3 is not permanently coupled to the application.

Phase 3 registers `GENERAL_MODEL` and `CODING_MODEL` roles. Ollama manages loading and unloading; the workbench does not attempt to keep both models resident in the RTX 3050's 6 GB VRAM. Switching may add latency.

The current Windows development machine uses an RTX 3050 with 6 GB VRAM. This favors appropriately quantized models and modest context sizes. A future enterprise deployment may use more capable organization-controlled GPU infrastructure; that is planned, not implemented.
