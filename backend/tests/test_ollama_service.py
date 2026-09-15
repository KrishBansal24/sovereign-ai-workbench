"""Contracts for concise, local-only Ollama generation requests."""

from types import SimpleNamespace
from typing import cast

from app.core.config import Settings
from app.services.llm.ollama_service import OllamaService


class _Response:
    """Minimal successful local Ollama response double."""

    status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, object]:
        return {"message": {"content": "Local answer"}}


def test_chat_disables_model_thinking_for_user_facing_answers(monkeypatch) -> None:
    """Qwen reasoning traces remain private and short RAG answers stay usable."""
    captured: dict[str, object] = {}

    def post(url: str, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _Response()

    import app.services.llm.ollama_service as module

    monkeypatch.setattr(module.requests, "post", post)
    service = OllamaService(cast(Settings, SimpleNamespace(ollama_base_url="http://127.0.0.1:11434", ollama_timeout_seconds=12, ollama_model="qwen3:8b")))

    assert service.chat_with_model("qwen3:8b", "Answer from local context.") == "Local answer"
    captured_json = captured.get("json")
    assert isinstance(captured_json, dict)
    assert captured_json.get("think") is False


def test_planner_json_mode_requests_local_structured_output(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def post(url: str, **kwargs):
        captured.update(kwargs)
        return _Response()

    import app.services.llm.ollama_service as module

    monkeypatch.setattr(module.requests, "post", post)
    service = OllamaService(cast(Settings, SimpleNamespace(ollama_base_url="http://127.0.0.1:11434", ollama_timeout_seconds=12, ollama_model="qwen3:8b")))
    assert service.chat_json_with_model("qwen3:8b", "Return an action.") == "Local answer"
    captured_json = captured.get("json")
    assert isinstance(captured_json, dict)
    assert captured_json.get("format") == "json" and captured_json.get("think") is False
