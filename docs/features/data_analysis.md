# Data Analysis

The Sovereign AI Workbench includes a secure, deterministic Data Analysis engine capable of processing structured datasets (CSV, XLSX) without exposing the raw data to the LLM for unreliable calculations.

## Managed Datasets

When CSV or XLSX files are uploaded, they are parsed and stored in the backend. The backend extracts metadata, including schema details (column names and data types), allowing the Agent and the UI to understand the dataset structure without reading every row.

## Deterministic Analysis Engine

LLMs are notoriously unreliable at arithmetic and statistical calculations. To solve this, the workbench separates *intent* from *execution*.

1. **Structured Fallback:** The user or Agent requests a specific calculation (e.g., average `vibration_hz` grouped by `pump_id`).
2. **Deterministic Execution:** The `DataAnalysisService` loads the data using Pandas, strictly validates the column names, and computes the exact mathematical result.
3. **Supported Operations:** The backend supports operations such as:
   - `summary_statistics`
   - `group_average`
   - `group_sum`
   - `correlation`
   - `filter_outliers`

## Natural-Language Data Mode

Users can query their data using natural language (e.g., *"What is the average pressure for each valve?"*) in the TUI Data tab.
- **Intent Mapping:** The local model maps the natural language question into a strict JSON schema (`DataAnalysisRequest`).
- **Validation:** The backend parses the JSON, validates it against allowed operations, and runs the deterministic calculation.
- **LLM Explanation:** The exact numerical result is passed back to the model, which provides a friendly textual explanation to accompany the deterministic data table.

This architecture ensures that users get the ease of natural language queries with the absolute mathematical certainty of a deterministic backend.
