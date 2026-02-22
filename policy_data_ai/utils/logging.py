"""Central logging setup."""

from __future__ import annotations

import logging
from typing import Optional

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def get_logger(name: str, level: int = logging.INFO, fmt: Optional[str] = None) -> logging.Logger:
    """Create/retrieve a module logger with a stable console format."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt or _DEFAULT_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger

