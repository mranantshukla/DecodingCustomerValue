"""Structured, consistent logging for the whole pipeline.

Why: an analytics pipeline that fails silently is worse than one that crashes.
Every stage logs what it read, what it changed, and what it wrote, so a failed
run can be diagnosed from the log alone — no rerun-with-print-statements.
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s"
_DATEFMT = "%H:%M:%S"


@lru_cache(maxsize=1)
def _configure_root(level: str = "INFO") -> None:
    """Attach a single stdout handler to the root logger exactly once."""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a namespaced logger, configuring the root handler on first use."""
    _configure_root(level)
    return logging.getLogger(name)
