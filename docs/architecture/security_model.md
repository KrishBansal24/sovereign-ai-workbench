# Security Model

The Sovereign AI Workbench is designed for confidential industrial environments where sensitive data must remain local. Security is implemented through strict trust boundaries, backend validation, and local inference constraints.

## Threat Context and Local Deployment

Industrial workflows handle proprietary processes, equipment details, incident information, and operational knowledge (P&IDs, SOPs). The system ensures:
- **Local Inference:** No cloud provider or external API is required. Inference runs through local Ollama configurations.
- **Air-Gapped Design:** Designed for air-gapped operations without phoning home. (Note: software controls do not replace hardware physical air-gap enforcement by the host network.)
- **Configuration Constraints:** Connects only to registered localhost Ollama endpoints.

## Trust Boundaries

All inputs traversing the API are treated as untrusted until proven otherwise by the backend.

### Untrusted Inputs
- **User Input:** TUI requests, prompts, and file uploads are considered untrusted.
- **Documents:** Uploaded files undergo strict parsing. Notably, `.py` files and other executable scripts are treated purely as **inert text** during ingestion and cannot be executed by the document service.
- **Model Outputs:** AI model responses are treated as **proposals, not authority**. The backend enforces strict validation on model decisions.

### Backend-Authoritative Validation
The TUI contains no business validation logic. The FastAPI backend owns execution policy:
- **Data Operation Validation:** The model proposes intent (e.g., natural-language to structured request mapping), but the backend verifies the schema, column names, and allowed calculations before deterministic execution.
- **Artifact Validation:** Generated files are strictly validated against target schemas and paths before being registered and made available to the user.

## Agent and Execution Security

### Prompt Injection Resistance
The architecture mitigates prompt injection by explicitly limiting the model's capabilities:
- **Restricted Agent Tool Registry:** The model can only select from a statically allowed list of tools.
- **Schema Enforcement:** Tool arguments must strictly match Pydantic schemas. 

### Sandbox Restrictions
- **No Arbitrary Shell:** Models cannot execute arbitrary bash/shell commands.
- **Isolated Execution:** When Python generation is necessary (Sandbox/Deliverables), code runs in a highly constrained process with strict timeouts (e.g., 5 seconds) and isolated temporary workspaces that are purged after execution.
- **Controlled Observation:** Tool execution failures return safe, sanitized string observations to the Agent, preventing environment exposure.

### Safe Execution Trace
- **Repeated Tool Protection:** The backend breaks infinite loops if the model repeatedly requests the identical tool and arguments without progress.
- **No Chain-of-Thought Exposure:** Internal model reasoning is hidden from the user to prevent hallucinatory logic from being presented as factual reasoning. The TUI only displays safe tool execution traces (Activity) and deterministic results.

## Data Quality and Reliability

### OCR Reliability States
Because industrial scans vary in quality, OCR and Vision extractions are strictly governed:
- Extractions are graded: `accepted`, `accepted_with_warnings`, `review_required`, or `reupload_required`.
- **Knowledge Indexing Eligibility:** Unreliable documents are categorically barred from entering the RAG vector store. Trust cannot be implicitly granted to garbage data; human-in-the-loop review is required to promote a document to Knowledge.
