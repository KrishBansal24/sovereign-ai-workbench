"""HTTP smoke tests for health and basic local-chat routes."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.llm.ollama_service import OllamaUnavailableError, ollama_service
from app.api.routes import knowledge as knowledge_route


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


def test_temporary_verification_page_and_assets_load() -> None:
    """The local developer client loads without replacing the OpenAPI UI."""
    assert client.get("/verify").status_code == 200
    assert client.get("/verify/static/verify.js").status_code == 200
    assert client.get("/docs").status_code == 200


def test_knowledge_answer_bounds_local_model_context(monkeypatch) -> None:
    """Generation uses only the strongest evidence fitting local model context."""
    requested: dict[str, int] = {}

    def search(_: str, top_k: int):
        requested["top_k"] = top_k
        return []

    monkeypatch.setattr(knowledge_route.knowledge_service, "search", search)
    response = client.post("/api/knowledge/ask", json={"question": "What does the manual say?"})

    assert response.status_code == 200
    assert requested["top_k"] == 2


def test_knowledge_answer_preserves_pdf_page_markers_in_sources(monkeypatch) -> None:
    """The UI can cite a source page without parsing opaque chunk IDs."""
    result = {"document_id": "source-id", "filename": "pump.pdf", "chunk_id": "source-id:1", "text": "[Page 12]\nInspection guidance", "character_count": 31, "chunk_index": 1, "similarity_score": 0.9}
    monkeypatch.setattr(knowledge_route.knowledge_service, "search", lambda *_: [result])
    monkeypatch.setattr(knowledge_route.ollama_service, "chat_with_model", lambda *_: "Grounded answer")

    response = client.post("/api/knowledge/ask", json={"question": "What guidance applies?"})

    assert response.status_code == 200
    assert response.json()["sources"][0]["page_numbers"] == [12]


def test_knowledge_answer_refuses_weak_retrieval_evidence(monkeypatch) -> None:
    """An unrelated nearest neighbour cannot be turned into a fabricated answer."""
    weak_result = {"document_id": "source-id", "filename": "pump.pdf", "chunk_id": "source-id:1", "text": "Pump maintenance", "character_count": 16, "chunk_index": 1, "similarity_score": 0.50}
    monkeypatch.setattr(knowledge_route.knowledge_service, "search", lambda *_: [weak_result])
    monkeypatch.setattr(knowledge_route.ollama_service, "chat_with_model", lambda *_: (_ for _ in ()).throw(AssertionError("model must not run")))

    response = client.post("/api/knowledge/ask", json={"question": "What was facility expenditure?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "The local knowledge base does not provide sufficient information."


def test_knowledge_answer_refuses_unmatched_date_and_expenditure_claim(monkeypatch) -> None:
    """A semantically nearby manual cannot support an absent time-bound fact."""
    nearby_result = {
        "document_id": "source-id", "filename": "pump.pdf", "chunk_id": "source-id:1",
        "text": "[Page 8] Inspect the pump annually and complete routine maintenance.",
        "character_count": 68, "chunk_index": 1, "similarity_score": 0.9,
    }
    monkeypatch.setattr(knowledge_route.knowledge_service, "search", lambda *_: [nearby_result])
    monkeypatch.setattr(
        knowledge_route.ollama_service, "chat_with_model",
        lambda *_: (_ for _ in ()).throw(AssertionError("model must not run")),
    )

    response = client.post(
        "/api/knowledge/ask",
        json={"question": "What was the total maintenance expenditure for the facility in August 2026?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "The local knowledge base does not provide sufficient information."


def test_knowledge_answer_does_not_treat_requested_format_as_missing_evidence(monkeypatch) -> None:
    """Presentation instructions are not factual anchors that sources must repeat."""
    result = {
        "document_id": "source-id", "filename": "pump.pdf", "chunk_id": "source-id:1",
        "text": "[Page 3] Inspect the pump regularly and perform routine maintenance.",
        "character_count": 68, "chunk_index": 1, "similarity_score": 0.9,
    }
    monkeypatch.setattr(knowledge_route.knowledge_service, "search", lambda *_: [result])
    monkeypatch.setattr(knowledge_route.ollama_service, "chat_with_model", lambda *_: "Grounded answer")

    response = client.post(
        "/api/knowledge/ask",
        json={"question": "Summarize pump inspection and maintenance guidance in two short bullet points using only local evidence."},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Grounded answer"
