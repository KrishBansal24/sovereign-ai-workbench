"""Configuration loading and local-only safety validation.

This module converts environment variables and the optional backend `.env`
file into one immutable Settings object used by routes and services. It keeps
runtime/model configuration outside application logic and rejects remote
Ollama endpoints to preserve the sovereign local-processing boundary.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def load_env_file() -> None:
    """Load simple `.env` values without replacing actual environment values.

    Operating-system variables take precedence so deployments can override
    local development defaults without changing a file.
    """
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_local_ollama_url(base_url: str) -> str:
    """Validate and normalize a loopback-only Ollama base URL.

    Args:
        base_url: Configured HTTP(S) endpoint for the Ollama runtime.

    Returns:
        URL without a trailing slash.

    Raises:
        ValueError: If the endpoint is not a supported localhost address.
    """
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
        raise ValueError("OLLAMA_BASE_URL must point to localhost, 127.0.0.1, or ::1.")
    return base_url.rstrip("/")


@dataclass(frozen=True)
class Settings:
    """Immutable settings shared by local AI, documents, RAG, and logging.

    Keeping these values together makes configuration discoverable and avoids
    scattering model names, upload limits, and storage paths across services.
    """
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    log_level: str
    max_upload_size_mb: int
    data_directory: Path
    general_model: str
    coding_model: str
    embedding_model: str
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_top_k: int
    rag_min_similarity: float
    agent_max_steps: int
    vision_model: str
    vision_timeout_seconds: float
    ocr_max_pages: int
    tesseract_cmd: str | None
    ocr_max_attempts: int


def get_settings() -> Settings:
    """Build validated application settings from environment-based configuration.

    Returns:
        A fully validated immutable settings instance.

    Raises:
        ValueError: If numeric limits, model names, or local URL policy fail.
    """
    load_env_file()
    base_url = require_local_ollama_url(
        os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
    general_model = os.getenv("GENERAL_MODEL", model).strip()
    coding_model = os.getenv("CODING_MODEL", "qwen2.5-coder:7b").strip()
    embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text").strip()
    rag_chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "3000"))
    rag_chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "400"))
    rag_top_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_min_similarity = float(os.getenv("RAG_MIN_SIMILARITY", "0.45"))
    agent_max_steps = int(os.getenv("AGENT_MAX_STEPS", "6"))
    vision_model = os.getenv("VISION_MODEL", "llava:7b").strip()
    vision_timeout_seconds = float(os.getenv("VISION_TIMEOUT_SECONDS", "120"))
    ocr_max_pages = int(os.getenv("OCR_MAX_PAGES", "20"))
    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip() or None
    ocr_max_attempts = int(os.getenv("OCR_MAX_ATTEMPTS", "2"))
    timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    max_upload_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    if not model or not general_model or not coding_model or not embedding_model or not vision_model:
        raise ValueError("Configured model names cannot be empty.")
    if timeout_seconds <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero.")
    if max_upload_size_mb <= 0:
        raise ValueError("MAX_UPLOAD_SIZE_MB must be greater than zero.")
    # Overlap must remain smaller than a chunk or chunking could stop advancing.
    if rag_chunk_size <= 0 or rag_chunk_overlap < 0 or rag_chunk_overlap >= rag_chunk_size or rag_top_k <= 0:
        raise ValueError("Invalid RAG chunking or retrieval configuration.")
    if not -1 <= rag_min_similarity <= 1 or agent_max_steps <= 0 or vision_timeout_seconds <= 0 or ocr_max_pages <= 0 or not 1 <= ocr_max_attempts <= 3:
        raise ValueError("Invalid RAG relevance threshold or agent step limit.")

    return Settings(
        ollama_base_url=base_url,
        ollama_model=model,
        ollama_timeout_seconds=timeout_seconds,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        max_upload_size_mb=max_upload_size_mb,
        data_directory=ENV_FILE.parent / "data",
        general_model=general_model,
        coding_model=coding_model,
        embedding_model=embedding_model,
        rag_chunk_size=rag_chunk_size,
        rag_chunk_overlap=rag_chunk_overlap,
        rag_top_k=rag_top_k,
        rag_min_similarity=rag_min_similarity,
        agent_max_steps=agent_max_steps,
        vision_model=vision_model,
        vision_timeout_seconds=vision_timeout_seconds,
        ocr_max_pages=ocr_max_pages,
        tesseract_cmd=tesseract_cmd,
        ocr_max_attempts=ocr_max_attempts,
    )


settings = get_settings()
