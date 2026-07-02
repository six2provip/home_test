from __future__ import annotations

import logging
import sys

_LOG_NAME = "optibot"
_DEFAULT_FORMAT = "%(levelname)s %(message)s"
_DEFAULT_LEVEL = logging.INFO


def setup_logger(
    *,
    level: int = _DEFAULT_LEVEL,
    fmt: str = _DEFAULT_FORMAT,
    stream: type = sys.stdout,
) -> logging.Logger:
    """Configure the root optibot logger with the given level and format."""
    logging.basicConfig(level=level, format=fmt, stream=stream)
    return get_logger()


def get_logger() -> logging.Logger:
    """Return the named optibot logger instance."""
    return logging.getLogger(_LOG_NAME)
