"""Bounded local-agent routes delegating execution to ``AgentController``."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.controller import agent_controller
from app.agents.schemas import AgentResponse
from app.tools.registry import TOOLS


router = APIRouter(prefix="/api", tags=["agent"])


class AgentRequest(BaseModel):
    """Validated goal for the bounded, local agent workflow."""

    goal: str = Field(
        min_length=1,
        max_length=10_000,
        description="Goal handled only through registered local tools.",
    )


@router.get("/tools")
def list_tools() -> list[dict[str, str | bool]]:
    """List enabled-state and permission metadata for registered local tools.

    The route exposes registry descriptions only; it does not expose callable
    internals or permit a client to register arbitrary tools.
    """
    return [
        {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "enabled": tool.enabled,
            "permission": tool.permission,
        }
        for tool in TOOLS.values()
    ]


@router.post(
    "/agent/run",
    response_model=AgentResponse,
    summary="Run a bounded local planner and controlled tools",
)
def run_agent(request: AgentRequest) -> AgentResponse:
    """Run a request-scoped workflow using only registered local tools.

    Args:
        request: Validated goal for ``AgentController``.

    Returns:
        Local workflow result and an operational trace.
    """
    # SECURITY: AgentController delegates through the fixed tool registry,
    # never direct client-directed shell, filesystem, or Python execution.
    return agent_controller.run(request.goal)
