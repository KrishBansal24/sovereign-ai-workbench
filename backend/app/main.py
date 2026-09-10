from fastapi import FastAPI

from app.api.routes import auto_chat, chat, documents, health, models, knowledge
from app.core.logging_config import configure_logging


configure_logging()


app = FastAPI(
    title="Sovereign AI Workbench",
    description="Local-only AI backend for confidential industrial work",
    version="0.4.0",
)


@app.get("/")
def root():
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
