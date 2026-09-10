"""HTTP smoke tests for health and basic local-chat routes."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.ollama_service import OllamaUnavailableError, ollama_service


client = TestClient(app)


def test_health_reports_available_local_services(monkeypatch):
    # Isolate the route contract from a running local Ollama daemon.
    monkeypatch.setattr(ollama_service, "is_available", lambda: True)
    monkeypatch.setattr(ollama_service, "is_model_available", lambda: True)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["backend"] == "online"
    assert response.json()["ollama"] == "available"
    assert response.json()["model_status"] == "available"


def test_chat_rejects_empty_message():
    response = client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_returns_mocked_local_response(monkeypatch):
    monkeypatch.setattr(
        ollama_service,
        "chat",
        lambda message: "A P&ID is a piping and instrumentation diagram.",
    )

    response = client.post("/api/chat", json={"message": "What is a P&ID?"})

    assert response.status_code == 200
    assert response.json()["processing"] == "local"
    assert response.json()["response"].startswith("A P&ID")


def test_chat_returns_503_when_ollama_is_unavailable(monkeypatch):
    def unavailable(_: str) -> str:
        raise OllamaUnavailableError("Local Ollama is unavailable.")

    monkeypatch.setattr(ollama_service, "chat", unavailable)

    response = client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Local Ollama is unavailable. Start Ollama and try again."
