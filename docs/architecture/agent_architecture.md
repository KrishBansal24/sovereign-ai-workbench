# Agent Architecture

The Sovereign AI Agent operates entirely locally using a strict Plan → Act → Observe → Decide bounded loop.

## Architecture and Flow

```text
Goal -> AgentPlanner -> strict decision -> tool registry/schema -> ToolExecutor
     -> untrusted observation -> AgentPlanner -> final answer or controlled stop
```

1. **Plan:** The `AgentPlanner` invokes the local JSON-capable reasoning model (e.g., `qwen3:8b`). It provides a system prompt detailing the user's goal, the allowed tool schemas, and the current execution history. The model must output a valid JSON response matching the `AgentStep` schema.
2. **Act:** The `AgentController` validates the proposed tool name and arguments against the backend's allowed tool registry. If valid, the `ToolExecutor` runs the deterministic local tool (e.g., `data_analysis`, `knowledge_search`, `create_chart`).
3. **Observe:** The tool returns an observation (e.g., calculation results, retrieved context, or file paths). This is appended to the agent's safe internal history.
4. **Decide:** The loop repeats. The planner sees the new observation and decides the next step, continuing until it selects the `final` tool to deliver the final answer, or until the maximum step budget (`AGENT_MAX_STEPS`) is exhausted.

## Security Boundaries

The Agent architecture relies on several strict boundaries:

- **Bounded Loop:** The loop cannot exceed `AGENT_MAX_STEPS`.
- **Schema-Validated Decisions:** Every action must parse into a strictly defined Pydantic model. If the model hallucinates or outputs conversational prose, the planner attempts to extract JSON. If it fails, a deterministic observation guides the model back on track.
- **Allowlisted Tools:** The agent cannot execute arbitrary shell commands. It only has access to a statically registered list of tools (e.g., `list_data_sources`, `data_analysis`, `knowledge_search`, `create_chart`, `create_spreadsheet`, `create_document`).
- **Repeated-Call Protection:** The `AgentController` tracks tool calls and normalizes arguments. If the model proposes the exact same tool with the exact same arguments repeatedly without progress, the backend intervenes to break the loop.
- **Safe Observations:** Tools return summarized string observations, preventing massive payload ingestion or hidden prompt injection from retrieved documents.
- **Source Propagation:** If the agent uses `knowledge_search`, the exact source document IDs are tracked and appended to the final response, ensuring the user can verify the original context.
- **No Hidden Reasoning:** The TUI displays the step-by-step tool trace (Activity) and the final result, but intentionally suppresses raw LLM chain-of-thought to prevent misleading or hallucinatory internal dialogue from being presented as fact.

## Example Workflow

A multi-tool industrial workflow is orchestrated as follows:
1. `list_data_sources` → Discover available datasets
2. `data_analysis` → Analyze vibration metrics
3. `knowledge_search` → Search maintenance manuals for the identified anomaly
4. `create_chart` → Generate a visual comparison of expected vs actual metrics
5. `create_spreadsheet` → Export the numerical differences
6. `create_document` → Write a grounded maintenance recommendation report
7. `final` → Summarize findings and return deliverable paths to the user.
