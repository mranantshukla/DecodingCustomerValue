"""Thin, well-logged I/O helpers so every read/write is consistent and traceable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logging_config import get_logger

log = get_logger(__name__)


def read_csv(path: Path | str, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV, stripping any UTF-8 BOM from the header (the raw file has one)."""
    df = pd.read_csv(path, encoding="utf-8-sig", **kwargs)
    log.info("Read %s rows x %s cols from %s", *df.shape, path)
    return df


def write_csv(df: pd.DataFrame, path: Path | str, index: bool = False) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    log.info("Wrote %s rows x %s cols -> %s", *df.shape, path)
    return path


def write_json(obj: Any, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)
    log.info("Wrote JSON -> %s", path)
    return path
