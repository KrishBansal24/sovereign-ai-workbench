"""Bounded local-agent loop connecting planner decisions to controlled tools.

The controller never executes planner prose. Each JSON decision is validated,
resolved through the fixed tool registry, executed by ``ToolExecutor``, and fed
back as a delimited untrusted observation until a final answer or safe stop.
"""

import json
import logging
import time
import uuid
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

        for step_number in range(1, self.settings.agent_max_steps + 1):
            try:
                decision, model_id, fallback_used = self.planner.decide(
                    goal, tuple(TOOLS.values()), observations, step_number,
                    self.settings.agent_max_steps - step_number + 1,
                )
            except Exception as error:
                # SECURITY: invalid/unavailable planner output never becomes a tool call.
                return self._stop(run_id, steps, sources, "failed", "planner_unavailable_or_invalid", started_at, error)

            logger.info(
                "event=agent_decision run_id=%s step=%s action=%s model_id=%s fallback_used=%s",
                run_id, step_number, decision.action, model_id, fallback_used,
            )
            if decision.action == "final":
                if not decision.answer:
                    return self._stop(run_id, steps, sources, "failed", "invalid_final_decision", started_at)
                steps.append(AgentStep(step=step_number, action="final", status="success"))
                self._log_end(run_id, "completed", started_at)
                return AgentResponse(run_id=run_id, status="completed", answer=decision.answer, steps=steps, sources=sources)

            tool = TOOLS.get(decision.tool_name or "")
            if tool is None or decision.arguments is None:
                return self._stop(run_id, steps, sources, "failed", "invalid_tool_decision", started_at)
            try:
                normalized_arguments = tool.schema.model_validate(decision.arguments).model_dump(mode="json")
            except ValidationError:
                observations.append(AgentObservation(tool=tool.id, success=False, error="Tool arguments failed validation."))
                steps.append(AgentStep(step=step_number, action="tool", tool=tool.id, status="invalid_arguments"))
                continue

            signature = f"{tool.id}:{json.dumps(normalized_arguments, sort_keys=True)}"
            if signature in seen_signatures:
                return self._stop(run_id, steps, sources, "stopped", "repeated_tool_call", started_at)
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

        return self._stop(run_id, steps, sources, "stopped", "max_steps_exhausted", started_at)

    def _has_relevant_result(self, data: dict[str, object] | None) -> bool:
        """Accept only retrieved chunks meeting the configured cosine threshold."""
        if not data or not isinstance(data.get("results"), list):
            return False
        return any(isinstance(item, dict) and float(item.get("similarity_score", -1)) >= self.settings.rag_min_similarity for item in data["results"])

    @staticmethod
    def _merge_sources(target: list[dict[str, str]], incoming: list[dict[str, str]]) -> None:
        """Append backend-derived source IDs once while preserving retrieval order."""
        for source in incoming:
            if source not in target:
                target.append(source)

    def _stop(self, run_id: str, steps: list[AgentStep], sources: list[dict[str, str]], status: str, reason: str, started_at: float, error: Exception | None = None) -> AgentResponse:
        """Create and log a controlled stop without exposing internal failures."""
        steps.append(AgentStep(step=len(steps) + 1, action="stopped", status=status, reason=reason))
        logger.warning("event=agent_stop run_id=%s status=%s reason=%s error_type=%s", run_id, status, reason, type(error).__name__ if error else "none")
        self._log_end(run_id, reason, started_at)
        return AgentResponse(run_id=run_id, status=status, answer="The local agent could not complete this request." if status == "failed" else "The local agent stopped before completing this request.", steps=steps, sources=sources, stop_reason=reason)

    @staticmethod
    def _log_end(run_id: str, reason: str, started_at: float) -> None:
        """Emit safe run duration metadata without goals, observations, or answers."""
        logger.info("event=agent_completed run_id=%s reason=%s duration_ms=%.2f", run_id, reason, (time.perf_counter() - started_at) * 1_000)


agent_controller = AgentController()
