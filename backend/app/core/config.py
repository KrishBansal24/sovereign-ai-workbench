"""Central configuration for the local-only backend."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def load_env_file() -> None:
    """Load simple KEY=VALUE entries without overwriting real environment variables."""
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_local_ollama_url(base_url: str) -> str:
    """Prevent accidental use of a cloud or remote inference endpoint."""
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
        raise ValueError("OLLAMA_BASE_URL must point to localhost, 127.0.0.1, or ::1.")
    return base_url.rstrip("/")


@dataclass(frozen=True)
class Settings:
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


def get_settings() -> Settings:
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
    timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    max_upload_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    if not model or not general_model or not coding_model or not embedding_model:
        raise ValueError("Configured model names cannot be empty.")
    if timeout_seconds <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero.")
    if max_upload_size_mb <= 0:
        raise ValueError("MAX_UPLOAD_SIZE_MB must be greater than zero.")
    if rag_chunk_size <= 0 or rag_chunk_overlap < 0 or rag_chunk_overlap >= rag_chunk_size or rag_top_k <= 0:
        raise ValueError("Invalid RAG chunking or retrieval configuration.")

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
    )


settings = get_settings()
