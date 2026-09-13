# Terminal Workbench

The Sovereign AI Workbench includes a rich Textual Terminal User Interface (TUI). The TUI serves strictly as a presentation layer for the local FastAPI backend. It contains **no** agent, RAG, OCR, sandbox, or deliverable business logic. 

## Design Philosophy

The TUI is designed to be professional, secure, and user-friendly for industrial operators:
- **No Raw JSON/IDs:** Users select documents, jobs, and artifacts by their human-readable names. Internal UUIDs are resolved by the TUI and are not part of standard workflows.
- **Backend-Authoritative:** The TUI builds validated structured requests, but the backend is always the final authority on validation, execution, and state.
- **Safe State Display:** The interface shows safe disconnected states when the backend is offline. It only communicates with the configured local backend and never exposes `.env` secrets or raw shell access.

## Screens and Workflows

- **Home:** Concise workspace status (document/artifact counts, job activity) and model availability.
- **Agent:** Interface to interact with the local bounded Agent, displaying step-by-step activity traces, final results, and saved artifacts.
- **Documents:** Workspace for ingesting files and folders. Supports batch progress for bulk imports.
- **Knowledge:** Chat interface to ask questions against the indexed RAG database.
- **OCR / Vision:** Inspection screen to review and accept/reject extracted text or OCR warnings.
- **Data:** Natural-language and structured data analysis against managed CSV/XLSX files.
- **Sandbox:** A technical interface for running bounded Python execution tasks.
- **Artifacts:** Listing of all generated deliverables with options to save them locally.
- **Jobs:** Live tracking of asynchronous backend tasks (e.g., parsing, data analysis).

## Controls

Navigation and operation are fully keyboard-driven:
- `1`–`9`: Quick navigation to core screens.
- `R`: Refresh backend state.
- `Ctrl+K` or `F2`: Open Command Palette for quick action discovery.
- `?`: Open Help.
- `Q`: Quit the workbench.

## Security Constraints

- The TUI never executes folder scans on behalf of the backend. Folder scanning during batch upload happens entirely in the client process, and individual files are streamed to the backend explicitly.
- Uploads and artifact downloads resolve strictly to human-entered or user-selected local paths. The backend never receives raw file system paths from the client.
