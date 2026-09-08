# Development Roadmap

| Phase | Status | Objective | Depends on |
| --- | --- | --- | --- |
| 1 — Foundation & Local LLM Backend | **Complete and verified** | Modular local FastAPI and Ollama chat foundation | — |
| 2 — Document Ingestion & Processing | **Complete and verified** | Local PDF/TXT/DOCX storage and deterministic extraction | Phase 1 |
| 3 — Multi-Model Support & Router | **Complete and verified** | Model management and task-aware routing | Phases 1–2 |
| 4 — Local Knowledge Base / RAG | **Next** | Local indexing and retrieval | Phases 2–3 |
| 5 — Agentic Engine & Tool Calling | Planned | Multi-step task execution | Phases 3–4 |
| 6 — Multimodal Intelligence | Planned | OCR and vision workflows | Phases 2–5 |
| 7 — Sandbox & Deliverables | Planned | Safe execution and office-file outputs | Phases 5–6 |
| 8 — Security, Sovereignty & Auditability | Planned | Isolation, audit, governance hardening | All prior phases |
| 9 — Professional React Workbench | Planned | User-facing production workbench | Core backend phases |
| 10 — End-to-End SIH Demonstration | Planned | Integrated offline demonstration | All phases |

Each phase is tested and integrated before the next begins. Planned phase descriptions are intent, not claims of current capability.
