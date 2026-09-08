"""Local Ollama client used by the API layer."""

import requests

from app.core.config import Settings, settings


class OllamaServiceError(Exception):
    """Base exception for failures communicating with Ollama."""


class OllamaUnavailableError(OllamaServiceError):
    """Ollama cannot be reached or did not respond in time."""


class OllamaModelNotFoundError(OllamaServiceError):
    """The configured Ollama model is not installed locally."""


class OllamaResponseError(OllamaServiceError):
    """Ollama returned an unexpected or unsuccessful response."""


class OllamaService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def chat(self, message: str) -> str:
        return self.chat_with_model(self.settings.ollama_model, message)

    def chat_with_model(self, model: str, message: str) -> str:
        try:
            response = requests.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "stream": False,
                },
                timeout=self.settings.ollama_timeout_seconds,
            )
        except (requests.ConnectionError, requests.Timeout) as error:
            raise OllamaUnavailableError("Local Ollama is unavailable.") from error
        except requests.RequestException as error:
            raise OllamaResponseError("Local Ollama request failed.") from error

        if response.status_code == 404:
            raise OllamaModelNotFoundError(
                f"Configured model '{self.settings.ollama_model}' was not found in Ollama."
            )

        try:
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except (requests.HTTPError, KeyError, TypeError, ValueError) as error:
            raise OllamaResponseError("Local Ollama returned an invalid response.") from error

    def is_available(self) -> bool:
        """Return whether the configured local Ollama server responds."""
        try:
            response = requests.get(
                f"{self.settings.ollama_base_url}/api/tags",
                timeout=min(self.settings.ollama_timeout_seconds, 5),
            )
            response.raise_for_status()
        except requests.RequestException:
            return False
        return True

    def is_model_available(self) -> bool:
        """Return whether the configured model appears in Ollama's local model list."""
        try:
            return self.settings.ollama_model in self.get_available_model_names()
        except OllamaUnavailableError:
            return False

    def get_available_model_names(self) -> set[str]:
        try:
            response = requests.get(f"{self.settings.ollama_base_url}/api/tags", timeout=min(self.settings.ollama_timeout_seconds, 5))
            response.raise_for_status()
            models = response.json()["models"]
            return {model.get("name") or model.get("model") for model in models if model.get("name") or model.get("model")}
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            raise OllamaUnavailableError("Local Ollama is unavailable.") from error


ollama_service = OllamaService()
