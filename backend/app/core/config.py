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


def get_settings() -> Settings:
    load_env_file()
    base_url = require_local_ollama_url(
        os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
    timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    max_upload_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    if not model:
        raise ValueError("OLLAMA_MODEL cannot be empty.")
    if timeout_seconds <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero.")
    if max_upload_size_mb <= 0:
        raise ValueError("MAX_UPLOAD_SIZE_MB must be greater than zero.")

    return Settings(
        ollama_base_url=base_url,
        ollama_model=model,
        ollama_timeout_seconds=timeout_seconds,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        max_upload_size_mb=max_upload_size_mb,
        data_directory=ENV_FILE.parent / "data",
    )


settings = get_settings()
