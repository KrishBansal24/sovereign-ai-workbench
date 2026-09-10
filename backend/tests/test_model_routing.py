"""Unit and route tests for deterministic task classification and model routing."""

from fastapi.testclient import TestClient

from app.api.routes import auto_chat as auto_chat_route
from app.main import app
from app.services.model_manager import ModelManager, RegisteredModel
from app.services.model_router import ModelRouter
from app.services.task_classifier import task_classifier


client = TestClient(app)


def test_registry_contains_general_and_coding_models():
    manager = ModelManager()
    assert manager.get("general").ollama_model
    assert "coding" in manager.get("coding").capabilities


def test_classifier_handles_core_task_families():
    assert task_classifier.classify("Write a Python function for Dijkstra's algorithm.").task_type == "coding"
    assert task_classifier.classify("Fix this TypeError in my FastAPI endpoint.").task_type == "debugging"
    assert task_classifier.classify("Explain what this code function does.").task_type == "code_explanation"
    assert task_classifier.classify("Explain centrifugal pump cavitation.").task_type == "reasoning"
    assert task_classifier.classify("Analyze the uploaded inspection report.").task_type == "document_analysis"
    assert task_classifier.classify("Summarize this inspection document.").task_type == "summarization"


def test_router_selects_coding_and_uses_general_fallback(monkeypatch):
    general = RegisteredModel(
        "general", "General", "general:latest", ("general",), True, 1, None, ""
    )
    coding = RegisteredModel(
        "coding", "Coding", "coding:latest", ("coding",), True, 1, "general", ""
    )
    manager = ModelManager(registry=(general, coding))
    monkeypatch.setattr(manager, "available_ids", lambda: {"coding", "general"})
    router = ModelRouter(manager)
    selected, metadata = router.route(task_classifier.classify("Write a Python function."))
    assert selected.id == "coding" and not metadata.fallback_used
    monkeypatch.setattr(manager, "available_ids", lambda: {"general"})
    selected, metadata = router.route(task_classifier.classify("Write a Python function."))
    assert selected.id == "general" and metadata.fallback_used


def test_auto_chat_allows_registered_override_and_rejects_unknown(monkeypatch):
    manager = ModelManager()
    monkeypatch.setattr(manager, "available_ids", lambda: {"general", "coding"})
    monkeypatch.setattr(auto_chat_route, "model_router", ModelRouter(manager))
    # Avoid real inference while retaining the full request/routing boundary.
    monkeypatch.setattr(
        auto_chat_route.ollama_service,
        "chat_with_model",
        lambda model, message: "local response",
    )
    success = client.post("/api/chat/auto", json={"message": "Hello", "model": "general"})
    assert success.status_code == 200
    assert success.json()["routing"]["selected_model_id"] == "general"
    assert client.post("/api/chat/auto", json={"message": "Hello", "model": "unknown"}).status_code == 400
