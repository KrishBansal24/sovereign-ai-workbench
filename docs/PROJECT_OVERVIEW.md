# Project Overview

## Problem and purpose

Industrial organizations need AI assistance for work such as interpreting procedures, reviewing inspection material, preparing reports, and retrieving institutional knowledge. Sending that material to public cloud AI services can conflict with confidentiality, data-residency, operational-security, and offline-operation needs. The Sovereign AI Workbench is a planned on-premise alternative for the MRPL/SIH 2026 context.

Sovereign AI means the organization controls the runtime, models, data paths, and eventual audit controls. Phase 1 has established a local backend foundation; it is not yet a complete enterprise air-gap solution.

## Intended users and use cases

Planned users include process engineers, maintenance and inspection teams, operations personnel, technical writers, and authorized administrators. Planned use cases include local procedure assistance, technical-document extraction, equipment and drawing understanding, confidential knowledge retrieval, and creation of engineering deliverables.

## Target system — planned

```text
User → Workbench → Task Router → Models → Agent → Tools / RAG / OCR / Sandbox → Deliverables
```

The task router, multiple models, agent, tools, RAG, OCR, sandbox, and deliverables are future components, not current features.

## Requirements

The eventual system must be local-first, model-agnostic, modular, hardware-aware, observable, and secure. It must remain usable offline, support open-weight models, process text and eventually images/documents, and generate auditable outputs without exporting confidential inputs.

## Current implementation

Phase 1 provides FastAPI, a localhost-only Ollama service, a configurable Qwen3 8B default, health/model status, local chat, safe errors, and metadata-only logging. See [Phase 1 Implementation](PHASE_1_IMPLEMENTATION.md).
