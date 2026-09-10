"""FastAPI composition root for the Sovereign AI Workbench.

This module configures process-wide logging and mounts independent route
modules. Business logic remains in services so future phases can evolve
without turning the application entry point into a controller.
"""

from fastapi import FastAPI

from app.api.routes import agent, auto_chat, chat, documents, health, knowledge, models
from app.core.logging_config import configure_logging


# Configure once at startup so every subsystem emits the same safe format.
configure_logging()


app = FastAPI(
    title="Sovereign AI Workbench",
    description="Local-only AI backend for confidential industrial work",
    version="0.4.0",
)


@app.get("/")
def root() -> dict[str, str]:
    """Return a minimal local-backend identity response for diagnostics."""
    return {
        "system": "Sovereign AI Workbench",
        "status": "online",
        "mode": "local",
    }


app.include_router(chat.router)
app.include_router(auto_chat.router)
app.include_router(documents.router)
app.include_router(health.router)
app.include_router(models.router)
app.include_router(knowledge.router)
app.include_router(agent.router)
