"""Local-only HTTP client for Ollama generation and model availability.

All inference stays on the loopback endpoint validated by core configuration;
this service deliberately provides no cloud fallback.
"""

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
    """Encapsulate local Ollama request construction, timeouts, and safe errors."""

    def __init__(self, app_settings: Settings = settings) -> None:
        """Create a client using the supplied localhost-only application settings.

        Args:
            app_settings: Configured local endpoint, model names, and timeout.
        """
        self.settings = app_settings

    def chat(self, message: str) -> str:
        """Generate with the configured default local model.

        Args:
            message: User content to send as one non-streaming chat turn.

        Returns:
            Assistant text returned by local Ollama.
        """
        return self.chat_with_model(self.settings.ollama_model, message)

    def chat_with_model(self, model: str, message: str) -> str:
        """Generate one non-streaming response using a registered local model.

        Args:
            model: Exact approved Ollama model tag selected by the router.
            message: User content to send as one non-streaming chat turn.

        Returns:
            Assistant text returned by local Ollama.
        """
        try:
            # SECURITY: URL originates from localhost-only Settings, not user input.
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
        """Return whether the configured local Ollama server responds.

        Returns:
            ``True`` when the local tags endpoint returns successfully.
        """
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
        """Return whether the configured model appears in Ollama's local model list.

        Returns:
            ``True`` when the configured default model has a local tag.
        """
        try:
            return self.settings.ollama_model in self.get_available_model_names()
        except OllamaUnavailableError:
            return False

    def get_available_model_names(self) -> set[str]:
        """Return exact locally installed Ollama tags or raise a controlled error.

        Returns:
            Set of exact model tags reported by the local Ollama daemon.
        """
        try:
            response = requests.get(
                f"{self.settings.ollama_base_url}/api/tags",
                timeout=min(self.settings.ollama_timeout_seconds, 5),
            )
            response.raise_for_status()
            models = response.json()["models"]
            return {model.get("name") or model.get("model") for model in models if model.get("name") or model.get("model")}
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            raise OllamaUnavailableError("Local Ollama is unavailable.") from error


ollama_service = OllamaService()
