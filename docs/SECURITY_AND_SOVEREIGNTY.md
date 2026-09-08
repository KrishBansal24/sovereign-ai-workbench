# Security and Sovereignty

## Threat context

Industrial prompts and documents may contain proprietary processes, equipment details, incident information, and operational knowledge. The system must avoid unnecessarily exporting such data.

## Current controls

- No OpenAI, Anthropic, Gemini, or other cloud inference API is used.
- Configuration rejects non-loopback Ollama endpoints.
- Prompts and model responses are not written to normal application logs.
- Service errors are translated to safe messages rather than Python stack traces.
- `.env`, runtime data, outputs, caches, and virtual environments are excluded from version control.

## Planned controls

Full network isolation, authentication, role-based access, a tamper-evident audit trail, document retention controls, sandbox isolation, malware scanning, and enterprise deployment governance are future work. Phase 1 does not claim to enforce a complete air gap.
