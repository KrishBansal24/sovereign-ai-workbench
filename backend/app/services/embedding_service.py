import requests

from app.core.config import settings
from app.services.ollama_service import OllamaUnavailableError


class EmbeddingError(Exception):
    pass


class EmbeddingService:
    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = requests.post(f"{settings.ollama_base_url}/api/embed", json={"model": settings.embedding_model, "input": texts}, timeout=settings.ollama_timeout_seconds)
            response.raise_for_status()
            vectors = response.json()["embeddings"]
            if len(vectors) != len(texts) or not vectors:
                raise ValueError("Invalid embedding response.")
            return vectors
        except requests.RequestException as error:
            raise OllamaUnavailableError("Local Ollama embedding model is unavailable.") from error
        except (KeyError, TypeError, ValueError) as error:
            raise EmbeddingError("Local embedding response was invalid.") from error


embedding_service = EmbeddingService()
