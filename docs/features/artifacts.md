# Artifact Generation

The Sovereign AI Workbench includes a `DeliverableService` designed to turn AI insights and deterministic numerical calculations into tangible, offline-ready industrial files.

## Supported Artifact Types

The backend natively supports generating the following artifact formats:
- **Charts:** `.png` (Bar, Line, Scatter charts generated via Matplotlib)
- **Spreadsheets:** `.xlsx` (Generated via OpenPyXL)
- **Documents:** `.docx` (Generated via python-docx)
- **Markdown:** `.md`

*Note: PowerPoint (`.pptx`) and PDF (`.pdf`) generation from deliverables are not implemented in the current Phase 7 capability set.*

## Generation and Validation

When the user requests an artifact (via the Data Analysis tab) or the Agent invokes a creation tool (e.g., `create_spreadsheet`), the process is strictly validated:
1. **Creation:** The `DeliverableService` receives structured input (title, layout, data rows) and delegates to the appropriate format generator.
2. **File Generation:** Files are built entirely locally using Python libraries.
3. **Validation:** After generation, the backend verifies that the file exists, has a non-zero size, and matches the requested format.
4. **Registry:** The artifact is logged into the backend's central registry with a UUID `artifact_id`.

## User Interaction and Save As

Once registered, the backend returns the `artifact_id` and metadata to the TUI.
- The TUI automatically downloads new artifacts created during Data Analysis or Agent runs into the local `outputs/` directory.
- The TUI provides visual confirmation of the saved path using safe, normalized local paths to ensure the user knows exactly where the offline files are located.
