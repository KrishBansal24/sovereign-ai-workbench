# Sovereign AI Request Flows

This document details the lifecycle of key operations in the Sovereign AI Workbench to illustrate the strict boundaries between the TUI and the backend authoritative logic.

## A. Knowledge (RAG) Flow

1. **User Input:** User enters a question in the TUI Knowledge screen.
2. **TUI Request:** TUI calls `POST /api/knowledge/ask` with the query string.
3. **Retrieval:**
   - `KnowledgeService` embeds the query using the local configured embedding model (e.g., `nomic-embed-text`).
   - Searches local FAISS vector store for matching document chunks.
   - Filters out chunks below the cosine similarity threshold or from un-indexed documents.
4. **Generation:**
   - If evidence is sufficient, `OllamaService` is called with the query and strict retrieved context.
   - If insufficient evidence, backend returns a grounded failure (hallucination prevention).
5. **TUI Render:** TUI receives the generated answer and source document IDs, mapping them to friendly names for display.

## B. Natural-Language Data Flow

1. **User Question:** User types a natural language question in the TUI Data tab.
2. **Context Selection:** TUI POSTs the question and the ID of the selected structured dataset.
3. **Intent Proposal:** The local LLM maps the natural language question to a strictly constrained `DataAnalysisRequest` JSON schema representing the intended operation and parameters.
4. **Strict Validation:** The backend validates the proposed operation (e.g., `group_average`, `statistics`) against allowed operations.
5. **Deterministic Execution:** The `DataAnalysisService` loads the dataset using Pandas and computes the exact result. The LLM does **NOT** perform trusted arithmetic directly.
6. **Result & Explanation:** The backend optionally asks the local model to explain the result, and returns the deterministic rows, columns, and text to the TUI.

## C. Agent Orchestration Flow

1. **User Task:** User specifies a complex goal in the Agent screen.
2. **Agent Endpoint:** TUI POSTs to `/api/agent/run`.
3. **Controller Loop (`AgentController`):**
   - **Plan:** Calls the local planner model (JSON mode) with the goal, available tool schemas, and recent history.
   - **Validate:** The proposed tool and arguments must pass Pydantic validation and exist in the allowed tool registry.
   - **Execute:** Runs the deterministic local tool (e.g., `knowledge_search`, `create_chart`).
   - **Observe:** Appends the execution result to the safe history.
   - **Repeat:** Loops until the planner chooses the `final` action, recovers deterministically, or the loop budget is exhausted.
4. **TUI Render:** TUI displays the safe tool trace (Activity), final result, and propagates any Knowledge sources.

## D. OCR/Vision Flow

1. **Upload:** User uploads an image, PDF, or text file.
2. **Extraction:** The backend `DocumentService` processes text natively if possible. If image-based or scanned, it proceeds to OCR.
3. **Reliability Assessment:** `OCRQualityService` evaluates the extraction quality (e.g., garbage characters, broken formatting).
4. **OCR/Vision:** If OCR is insufficient, the local vision model (`llava:7b`) attempts to recover tabular or diagram data.
5. **Review State:** Based on confidence, the backend issues warnings, placing the document in `review_required`, `accepted_with_warnings`, or `reupload_required`.
6. **Knowledge Eligibility:** Unreliable documents are barred from RAG indexing until the human-in-the-loop accepts them.

## E. Artifact Generation Flow

1. **Validated Inputs:** A deterministic calculation from Data Analysis or an approved Agent workflow produces structured rows and columns.
2. **Artifact Service:** The `DeliverableService` takes the structured payload.
3. **File Generation:** OpenPyXL, python-docx, pptx, or Matplotlib generates the local file.
4. **Validation:** The backend verifies file existence and format.
5. **Artifact Registry:** The artifact is tracked in the central database with `artifact_id`.
6. **User Save:** The TUI fetches the metadata, displays it, and allows the user to download the final bytes directly to the local filesystem without external dependencies.
