"""Local Ollama embedding integration for the knowledge base."""

import requests

from app.core.config import settings
from app.services.ollama_service import OllamaUnavailableError


class EmbeddingError(Exception):
    """Raised when Ollama returns a malformed embedding payload."""


class EmbeddingService:
    """Generate dense vector representations through the configured Ollama model."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed each supplied text with the configured local embedding model.

        Args:
            texts: Ordered document chunks or user queries to embed.

        Returns:
            One floating-point vector per supplied text, in the same order.

        Raises:
            OllamaUnavailableError: If the local Ollama endpoint cannot serve
                the embedding request.
            EmbeddingError: If the endpoint response lacks usable embeddings.
        """
        try:
            # SECURITY: settings points to the project's local Ollama endpoint;
            # embeddings are never sent to a cloud provider by this service.
            response = requests.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": texts},
                timeout=settings.ollama_timeout_seconds,
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]
            # The vector store establishes the dimension from these vectors;
            # here we only ensure Ollama returned one non-empty result per input.
            if len(embeddings) != len(texts) or not embeddings:
                raise ValueError("Invalid embedding response.")
            return embeddings
        except requests.RequestException as error:
            raise OllamaUnavailableError("Local Ollama embedding model is unavailable.") from error
        except (KeyError, TypeError, ValueError) as error:
            raise EmbeddingError("Local embedding response was invalid.") from error


embedding_service = EmbeddingService()
