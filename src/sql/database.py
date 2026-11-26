"""Database access layer.

Targets PostgreSQL in production via SQLAlchemy, but degrades gracefully to the
Python standard-library ``sqlite3`` driver when SQLAlchemy is not installed and
the URL is SQLite. This is what lets the project run end-to-end on a bare
``pip install pandas`` while still being a one-env-var switch to Postgres.

The class exposes exactly what the analytics layer needs: write a DataFrame,
execute a SQL script (multiple statements), and read a query into a DataFrame.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logging_config import get_logger

log = get_logger(__name__)

try:  # Prefer SQLAlchemy when available (required for Postgres).
    from sqlalchemy import create_engine, text

    _HAS_SQLALCHEMY = True
except Exception:  # pragma: no cover - exercised in minimal installs
    _HAS_SQLALCHEMY = False


def split_sql_statements(script: str) -> list[str]:
    """Split a multi-statement SQL script into individual statements.

    Strips ``--`` line comments and blank lines, then splits on ``;``. The
    project's SQL never embeds semicolons inside string literals, so this simple
    splitter is safe and keeps us free of a heavyweight SQL parser.
    """
    no_comments = re.sub(r"--[^\n]*", "", script)
    parts = [s.strip() for s in no_comments.split(";")]
    return [p for p in parts if p]


class DatabaseManager:
    """Thin engine wrapper with SQLAlchemy / sqlite3 parity."""

    def __init__(self, url: str):
        self.url = url
        self.is_sqlite = url.startswith("sqlite")
        if _HAS_SQLALCHEMY:
            self._engine = create_engine(url, future=True)
            self._backend = "sqlalchemy"
        elif self.is_sqlite:
            self._sqlite_path = url.replace("sqlite:///", "")
            Path(self._sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            self._engine = None
            self._backend = "sqlite3"
        else:
            raise RuntimeError(
                "SQLAlchemy is required for non-SQLite databases. "
                "Install it with `pip install SQLAlchemy psycopg2-binary`."
            )
        log.info("Database backend: %s (%s)", self._backend, url)

    # -- connections ----------------------------------------------------------
    def _raw_sqlite(self) -> sqlite3.Connection:
        return sqlite3.connect(self._sqlite_path)

    # -- write ----------------------------------------------------------------
    def write_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "replace") -> None:
        if self._backend == "sqlalchemy":
            with self._engine.begin() as conn:  # type: ignore[union-attr]
                df.to_sql(table, conn, if_exists=if_exists, index=False)
        else:
            with self._raw_sqlite() as conn:
                df.to_sql(table, conn, if_exists=if_exists, index=False)
        log.info("Loaded %d rows into table '%s'", len(df), table)

    # -- execute scripts ------------------------------------------------------
    def execute_script(self, script: str) -> None:
        statements = split_sql_statements(script)
        if self._backend == "sqlalchemy":
            with self._engine.begin() as conn:  # type: ignore[union-attr]
                for stmt in statements:
                    conn.execute(text(stmt))
        else:
            with self._raw_sqlite() as conn:
                conn.executescript(script)
        log.info("Executed SQL script (%d statements)", len(statements))

    def execute_sql_file(self, path: Path | str) -> None:
        path = Path(path)
        self.execute_script(path.read_text(encoding="utf-8"))
        log.info("Applied %s", path.name)

    # -- read -----------------------------------------------------------------
    def read_query(self, query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        if self._backend == "sqlalchemy":
            with self._engine.connect() as conn:  # type: ignore[union-attr]
                return pd.read_sql_query(text(query), conn, params=params)
        with self._raw_sqlite() as conn:
            return pd.read_sql_query(query, conn, params=params)
