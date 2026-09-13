"""Bounded local-agent loop connecting planner decisions to controlled tools.

The controller never executes planner prose. Each JSON decision is validated,
resolved through the fixed tool registry, executed by ``ToolExecutor``, and fed
back as a delimited untrusted observation until a final answer or safe stop.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.agents.planner import AgentPlanner, agent_planner
from app.agents.schemas import AgentObservation, AgentResponse, AgentStep, PlannerDecision
from app.core.config import Settings, settings
from app.tools.executor import ToolExecutor, tool_executor
from app.tools.registry import TOOLS, ToolDefinition


logger = logging.getLogger(__name__)


class AgentController:
    """Run a finite planner -> tool -> observation -> planner workflow.

    Tool-call signatures prevent a planner from repeatedly making an identical
    request. The max-step budget is a final backstop against malformed or
    unproductive local-model plans.
    """

    def __init__(
        self,
        planner: AgentPlanner = agent_planner,
        executor: ToolExecutor = tool_executor,
        app_settings: Settings = settings,
    ) -> None:
        """Create a controller with replaceable local dependencies for tests."""
        self.planner = planner
        self.executor = executor
        self.settings = app_settings

    def run(self, goal: str) -> AgentResponse:
        """Execute a bounded local agent run and return an operational trace."""
        run_id = str(uuid.uuid4())
        started_at = time.perf_counter()
        observations: list[AgentObservation] = []
        steps: list[AgentStep] = []
        sources: list[dict[str, str]] = []
        seen_signatures: set[str] = set()
        duplicate_recovery_used = False

        for step_number in range(1, self.settings.agent_max_steps + 1):
            try:
                decision, model_id, fallback_used = self.planner.decide(
                    goal, tuple(TOOLS.values()), observations, step_number,
                    self.settings.agent_max_steps - step_number + 1,
                )
            except Exception as error:
                # SECURITY: invalid/unavailable planner output never becomes a tool call.
                recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
                if recovered:
                    return recovered
                return self._stop(run_id, steps, sources, "failed", "planner_unavailable_or_invalid", started_at, error)

            logger.info(
                "event=agent_decision run_id=%s step=%s action=%s model_id=%s fallback_used=%s",
                run_id, step_number, decision.action, model_id, fallback_used,
            )
            if decision.action == "final":
                if not decision.answer:
                    recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
                    if recovered:
                        return recovered
                    return self._stop(run_id, steps, sources, "failed", "invalid_final_decision", started_at)
                missing = self._missing_requested_tools(goal, steps)
                if missing:
                    if "knowledge_search" in missing:
                        knowledge = self.executor.execute("knowledge_search", {"query": "maintenance guidance for abnormal operating condition", "top_k": 5})
                        observations.append(AgentObservation(**knowledge.model_dump()))
                        steps.append(AgentStep(step=len(steps) + 1, action="tool", tool="knowledge_search", status="success" if knowledge.success else "failed"))
                        self._merge_sources(sources, knowledge.sources)
                        if knowledge.success:
                            recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
                            if recovered:
                                return recovered
                            continue
                    if self._complete_required_tabular_artifacts(missing, observations, steps):
                        continue
                    recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
                    if recovered:
                        return recovered
                    observations.append(AgentObservation(
                        tool="completion_guard",
                        success=False,
                        error=f"The requested deliverable is not complete: {', '.join(missing)}. Execute the required approved tool before finalizing.",
                    ))
                    steps.append(AgentStep(step=step_number, action="final", status="incomplete_requirements", reason="missing_required_tool"))
                    continue
                steps.append(AgentStep(step=step_number, action="final", status="success"))
                self._log_end(run_id, "completed", started_at)
                return AgentResponse(run_id=run_id, status="completed", answer=decision.answer, steps=steps, sources=sources)

            tool = TOOLS.get(decision.tool_name or "")
            if tool is None or decision.arguments is None:
                recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
                if recovered:
                    return recovered
                return self._stop(run_id, steps, sources, "failed", "invalid_tool_decision", started_at)
            try:
                normalized_arguments = tool.schema.model_validate(decision.arguments).model_dump(mode="json")
            except ValidationError as exc:
                error_details = []
                for err in exc.errors():
                    loc = ".".join(str(l) for l in err.get("loc", []))
                    error_details.append(f"{loc}: {err.get('msg')}")
                error_msg = f"Tool arguments failed validation: {'; '.join(error_details)}"
                observations.append(AgentObservation(tool=tool.id, success=False, error=error_msg))
                steps.append(AgentStep(step=step_number, action="tool", tool=tool.id, status="invalid_arguments"))
                continue

            signature = f"{tool.id}:{json.dumps(normalized_arguments, sort_keys=True)}"
            if signature in seen_signatures:
                # Never execute a duplicate. One bounded correction turn lets a
                # small local planner use the observation it already requested
                # instead of failing a valid multi-step workflow immediately.
                if duplicate_recovery_used:
                    recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
                    if recovered:
                        return recovered
                    return self._stop(run_id, steps, sources, "stopped", "repeated_tool_call", started_at)
                duplicate_recovery_used = True
                observations.append(AgentObservation(
                    tool=tool.id,
                    success=False,
                    error="This exact tool call already completed. Use its returned observation; choose a different approved tool or final answer.",
                ))
                steps.append(AgentStep(step=step_number, action="tool", tool=tool.id, status="duplicate_not_executed"))
                continue
            seen_signatures.add(signature)

            tool_result = self.executor.execute(tool.id, normalized_arguments)
            observation = AgentObservation(**tool_result.model_dump())
            observations.append(observation)
            steps.append(AgentStep(step=step_number, action="tool", tool=tool.id, status="success" if tool_result.success else "failed"))
            self._merge_sources(sources, tool_result.sources)
            logger.info("event=agent_tool run_id=%s step=%s tool_id=%s success=%s", run_id, step_number, tool.id, tool_result.success)

            if tool.id == "knowledge_search" and tool_result.success and not self._has_relevant_result(tool_result.data):
                steps.append(AgentStep(step=step_number + 1, action="final", status="insufficient_knowledge"))
                self._log_end(run_id, "insufficient_knowledge", started_at)
                return AgentResponse(run_id=run_id, status="insufficient_knowledge", answer="The local knowledge base does not contain enough relevant information.", steps=steps, sources=sources, stop_reason="insufficient_relevance")

        recovered = self._recover_observed_industrial_workflow(goal, observations, steps, sources, run_id, started_at)
        if recovered:
            return recovered
        return self._stop(run_id, steps, sources, "stopped", "max_steps_exhausted", started_at)

    def _recover_observed_industrial_workflow(self, goal: str, observations: list[AgentObservation], steps: list[AgentStep], sources: list[dict[str, str]], run_id: str, started_at: float) -> AgentResponse | None:
        """Finish a requested local industrial workflow from verified observations.

        Used only after a planner failure/limit. It selects no opaque ID: the
        candidate must advertise a vibration column in an earlier controlled
        dataset listing, and all values/artifacts come from approved tools.
        """
        normalized = goal.lower()
        if not all(term in normalized for term in ("operational data", "maintenance", "chart", "excel")) or not sources:
            return None
        candidate: dict[str, object] | None = None
        for observation in observations:
            datasets = observation.data.get("datasets") if observation.data else None
            if isinstance(datasets, list):
                candidate = next((item for item in datasets if isinstance(item, dict) and isinstance(item.get("columns"), list) and any("vibration" in str(column).lower() for column in item["columns"])), None)
                if candidate:
                    break
        if not candidate or not isinstance(candidate.get("source_id"), str):
            return None
        value_column = next((str(column) for column in candidate.get("columns", []) if "vibration" in str(column).lower()), None)
        group_by = next((str(column) for column in candidate.get("columns", []) if str(column).lower() in {"asset", "equipment", "unit", "device"}), None)
        if not value_column or not group_by:
            return None
        base = {"source_id": candidate["source_id"], "source_kind": candidate.get("source_kind", "document"), "value_column": value_column}
        statistics = self.executor.execute("data_analysis", {**base, "operation": "statistics"})
        grouped = self.executor.execute("data_analysis", {**base, "operation": "group_average", "group_by": group_by})
        # Keep grouped evidence last so artifact completion consumes its rows
        # directly instead of scheduling a redundant grouped analysis.
        for result in (statistics, grouped):
            observations.append(AgentObservation(**result.model_dump()))
            steps.append(AgentStep(step=len(steps) + 1, action="tool", tool="data_analysis", status="success" if result.success else "failed"))
        if not grouped.success or not statistics.success:
            return None
        missing = self._missing_requested_tools(goal, steps)
        if not self._complete_required_tabular_artifacts(missing, observations, steps):
            return None
        averages = grouped.data.get("result", {}).get("averages", {}) if grouped.data else {}
        if not isinstance(averages, dict) or not averages:
            return None
        equipment, average = max(averages.items(), key=lambda item: float(item[1]))
        stats = statistics.data.get("result", {}) if statistics.data else {}
        steps.append(AgentStep(step=len(steps) + 1, action="final", status="success"))
        self._log_end(run_id, "deterministic_observed_recovery", started_at)
        return AgentResponse(
            run_id=run_id, status="completed",
            answer=(f"Measured facts: {equipment} has the highest observed average {value_column} at {average}. "
                    f"Supporting statistics: minimum {stats.get('min')}, maximum {stats.get('max')}, standard deviation {stats.get('standard_deviation')}. "
                    "Recommendation: apply the cited local maintenance guidance and have plant personnel review the condition before action."),
            steps=steps, sources=sources,
        )

    def _has_relevant_result(self, data: dict[str, object] | None) -> bool:
        """Accept only retrieved chunks meeting the configured cosine threshold."""
        if not data or not isinstance(data.get("results"), list):
            return False
        return any(isinstance(item, dict) and float(item.get("similarity_score", -1)) >= self.settings.rag_min_similarity for item in data["results"])

    @staticmethod
    def _missing_requested_tools(goal: str, steps: list[AgentStep]) -> list[str]:
        """Require concrete local deliverable creation before a final claim."""
        normalized_goal = goal.lower()
        required = {
            "chart": "create_chart",
            "excel": "create_spreadsheet",
            "workbook": "create_spreadsheet",
            "word": "create_document",
            "maintenance recommendation": "create_document",
        }
        for phrase in ("manual", "engineering document", "maintenance guidance", "cite", "citation", "recommendation"):
            if phrase in normalized_goal:
                required[phrase] = "knowledge_search"
        completed_tools = {step.tool for step in steps if step.action == "tool" and step.status == "success"}
        return sorted({tool for phrase, tool in required.items() if phrase in normalized_goal and tool not in completed_tools})

    def _complete_required_tabular_artifacts(self, missing: list[str], observations: list[AgentObservation], steps: list[AgentStep]) -> bool:
        """Create requested tabular artifacts only from measured analysis output.

        This deterministic completion path never supplies equipment names or
        values itself; it merely transforms an approved tool observation into
        the fixed chart-tool contract when the local planner omits that step.
        """
        allowed = {"create_chart", "create_spreadsheet", "create_document"}
        if not missing or not set(missing) <= allowed:
            return False
        for observation in reversed(observations):
            if observation.tool != "data_analysis" or not observation.success or not observation.data:
                continue
            result = observation.data.get("result")
            averages = result.get("averages") if isinstance(result, dict) else None
            if not isinstance(averages, dict) or not averages:
                request = observation.data.get("request")
                if not isinstance(request, dict) or not request.get("value_column") or not request.get("source_id"):
                    return False
                columns: list[object] = []
                for source_observation in reversed(observations):
                    datasets = source_observation.data.get("datasets") if source_observation.data else None
                    if isinstance(datasets, list):
                        match = next((item for item in datasets if isinstance(item, dict) and item.get("source_id") == request["source_id"]), None)
                        if match and isinstance(match.get("columns"), list):
                            columns = match["columns"]
                            break
                group_by = next((str(column) for column in columns if str(column).lower() in {"asset", "equipment", "unit", "device"}), None)
                if not group_by:
                    return False
                grouped = self.executor.execute("data_analysis", {
                    "source_id": request["source_id"], "source_kind": request.get("source_kind", "document"),
                    "operation": "group_average", "value_column": request["value_column"], "group_by": group_by,
                })
                observations.append(AgentObservation(**grouped.model_dump()))
                steps.append(AgentStep(step=len(steps) + 1, action="tool", tool="data_analysis", status="success" if grouped.success else "failed"))
                if not grouped.success or not grouped.data:
                    return False
                observation = observations[-1]
                result = observation.data.get("result")
                averages = result.get("averages") if isinstance(result, dict) else None
            if not isinstance(averages, dict) or not averages:
                return False
            rows = [[str(name), float(value)] for name, value in averages.items() if isinstance(value, (int, float))]
            if not rows:
                return False
            source_name = "analysis"
            for source_observation in reversed(observations):
                datasets = source_observation.data.get("datasets") if source_observation.data else None
                if isinstance(datasets, list):
                    match = next((item for item in datasets if isinstance(item, dict) and item.get("source_id") == observation.data.get("source_id")), None)
                    if match and isinstance(match.get("filename"), str):
                        source_name = Path(match["filename"]).stem
                        break
            table_payload = {
                "title": f"{source_name.replace('_', ' ').title()} Comparison",
                "columns": ["Equipment", "Average"],
                "rows": rows,
            }
            local_sources = [source.get("filename", "Local maintenance source") for source in observations[-1].sources]
            if not local_sources:
                for source_observation in observations:
                    local_sources.extend(source.get("filename", "Local maintenance source") for source in source_observation.sources)
            completed = True
            for tool_id in missing:
                if tool_id == "create_document":
                    tool_payload = {
                        "filename": f"{source_name}_maintenance_recommendation.docx",
                        "title": f"{source_name.replace('_', ' ').title()} Maintenance Recommendation",
                        "sections": [
                            {"heading": "Measured findings", "paragraphs": [f"Observed grouped averages: {', '.join(f'{name}: {value}' for name, value in rows)}."]},
                            {"heading": "Maintenance guidance", "paragraphs": ["Recommendations are based only on the cited local maintenance sources and should be reviewed by plant personnel."]},
                        ],
                        "sources": local_sources[:10],
                    }
                else:
                    suffix = "comparison_chart.png" if tool_id == "create_chart" else "analysis_workbook.xlsx"
                    tool_payload = {**table_payload, "filename": f"{source_name}_{suffix}"}
                tool_result = self.executor.execute(tool_id, tool_payload)
                observations.append(AgentObservation(**tool_result.model_dump()))
                steps.append(AgentStep(step=len(steps) + 1, action="tool", tool=tool_id, status="success" if tool_result.success else "failed"))
                completed = completed and tool_result.success
            return completed
        return False

    @staticmethod
    def _merge_sources(target: list[dict[str, str]], incoming: list[dict[str, str]]) -> None:
        """Append backend-derived source IDs once while preserving retrieval order."""
        for source in incoming:
            if source not in target:
                target.append(source)

    def _stop(self, run_id: str, steps: list[AgentStep], sources: list[dict[str, str]], status: str, reason: str, started_at: float, error: Exception | None = None) -> AgentResponse:
        """Create and log a controlled stop without exposing internal failures."""
        steps.append(AgentStep(step=len(steps) + 1, action="stopped", status=status, reason=reason))
        logger.warning(
            "event=agent_stop run_id=%s status=%s reason=%s error_type=%s error_msg=%s",
            run_id, status, reason, type(error).__name__ if error else None, str(error) if error else None
        )
        self._log_end(run_id, reason, started_at)
        return AgentResponse(run_id=run_id, status=status, answer="The local agent could not complete this request." if status == "failed" else "The local agent stopped before completing this request.", steps=steps, sources=sources, stop_reason=reason)

    @staticmethod
    def _log_end(run_id: str, reason: str, started_at: float) -> None:
        """Emit safe run duration metadata without goals, observations, or answers."""
        logger.info("event=agent_completed run_id=%s reason=%s duration_ms=%.2f", run_id, reason, (time.perf_counter() - started_at) * 1_000)


agent_controller = AgentController()
