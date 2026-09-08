"""Logging configuration that avoids confidential prompt and response content."""

import logging

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
        force=True,
    )
