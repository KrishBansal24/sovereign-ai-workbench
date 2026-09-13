# Phase 5: Bounded Local Agent and Controlled Tools

Phase 5 runs a finite local workflow: goal -> `AgentPlanner` -> strict JSON
`PlannerDecision` -> registry/schema validation -> `ToolExecutor` -> safe
observation -> planner -> final answer or controlled stop.

`app.agents.planner.AgentPlanner` selects an approved local planning model via
the Phase 3 `ModelRouter` and `OllamaService`; no model tag is hardcoded.
Retrieved document text and tool observations are delimited untrusted data in
the planning prompt. Only the system policy and fixed registered tools control
execution.

`AgentController` enforces `AGENT_MAX_STEPS` (default 6), rejects repeated
normalized tool ID/argument signatures, propagates backend-derived sources,
and returns an operational trace without chain-of-thought. Malformed planner
JSON, unavailable planners, unknown tools, and invalid arguments stop safely.

`ToolExecutor` can execute only `knowledge_search`, `document_metadata`,
`document_text`, and deterministic `calculator`; arguments receive Pydantic
validation. It never uses dynamic imports, shell commands, `eval`, or `exec`.

Phase 4's normalized FAISS `IndexFlatIP` uses cosine similarity for non-zero
vectors. The agent applies configurable `RAG_MIN_SIMILARITY` (default 0.45) so
low-relevance nearest chunks produce an insufficient-knowledge response.

Safe audit logs contain run ID, step, action/tool, selected model/fallback,
duration, and stop reason. They exclude goals, documents, observations, answers,
and hidden reasoning.
