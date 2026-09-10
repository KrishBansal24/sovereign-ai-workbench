"""Application logging configuration for safe operational observability.

The shared format supports metadata-based events while routes and services
avoid logging confidential prompts, documents, retrieved chunks, or answers.
"""

import logging

from app.core.config import settings


def configure_logging() -> None:
    """Configure the process logger using the configured level and safe format."""
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
        force=True,
    )
