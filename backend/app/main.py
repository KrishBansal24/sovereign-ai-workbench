from fastapi import FastAPI

from app.api.routes import chat, documents, health
from app.core.logging_config import configure_logging


configure_logging()


app = FastAPI(
    title="Sovereign AI Workbench",
    description="Local-only AI backend for confidential industrial work",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "system": "Sovereign AI Workbench",
        "status": "online",
        "mode": "local",
    }


app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(health.router)
