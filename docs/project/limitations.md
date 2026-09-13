# Current Limitations

As of Phase 7, the Sovereign AI Workbench is fully functional but operates within specific technical and architectural limitations.

## Hardware and Performance

- **Consumer GPU Latency:** The system is currently optimized for a Windows development machine with an RTX 3050 (6 GB VRAM). Switching between models (e.g., from reasoning to vision) forces Ollama to reload models, which introduces noticeable latency.
- **Model Size:** The strict VRAM constraints require the use of highly quantized, smaller open-weight models (like `qwen3:8b`). These models are highly capable but do not possess the vast parametric knowledge or zero-shot logical reasoning capacity of massive proprietary models (like GPT-4).

## Air-Gap Enforcement

- **Software Level Only:** The workbench is designed to operate entirely offline without phoning home. However, it does not *physically* enforce a network air-gap. In a true secure deployment, network isolation must be enforced by the host firewall and infrastructure.

## OCR and Vision

- **OCR Quality Dependency:** The reliability of document ingestion is highly dependent on the quality of the uploaded scan. Severely degraded industrial schematics will correctly be marked `review_required`, but this necessitates human intervention.
- **Vision Reliability:** `llava:7b` handles basic visual extraction and fallback parsing but struggles with complex, dense P&ID engineering schematics.

## Data and Agent Operations

- **Agent Sync Constraints:** The Agent operates via a synchronous polling architecture in the TUI, which currently lacks incremental token streaming for step execution.
- **Complex Data Requests:** While Natural-Language Data Mode securely handles filtering, aggregation, and correlations, requests that require complex nested pivots or multi-table joins will fail strict schema validation. For these edge cases, users must rely on the Python Sandbox or the Agent.
- **Artifact Formats:** PDF and PowerPoint deliverable generation, while architecturally planned for, are not implemented in the current Phase 7 rollout.

## User Interface

- **TUI-Focused:** The current presentation layer is entirely command-line based via Textual. A future web-based React frontend is planned but does not yet exist.
