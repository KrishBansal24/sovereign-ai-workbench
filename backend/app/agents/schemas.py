"""Strict planner decisions and safe operational records for the agent loop."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlannerDecision(BaseModel):
    """Validated next action requested by the local planning model.

    This contract contains no executable callable. Tool names and arguments are
    subsequently checked against the fixed registry and schema by the controller.
    """

    action: Literal["tool", "final"]
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    answer: str | None = None
    reason: str | None = Field(default=None, max_length=500)


class AgentStep(BaseModel):
    """Safe audit event describing an action, never hidden model reasoning."""

    step: int
    action: Literal["tool", "final", "stopped"]
    status: str
    tool: str | None = None
    reason: str | None = None


class AgentObservation(BaseModel):
    """Delimited untrusted data returned by one controlled tool invocation."""

    tool: str
    success: bool
    data: dict[str, object] | None = None
    error: str | None = None
    sources: list[dict[str, str]] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Public response for a bounded local agent run."""

    run_id: str
    status: Literal["completed", "insufficient_knowledge", "stopped", "failed"]
    answer: str | None
    steps: list[AgentStep]
    sources: list[dict[str, str]]
    processing: Literal["local"] = "local"
    stop_reason: str | None = None
