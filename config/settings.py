"""Centralised, type-safe configuration for the Decoding Customer Value platform.

Why this exists
---------------
Hard-coded paths, magic numbers, and credentials scattered across scripts are the
single biggest source of "works on my machine" failures in analytics projects.
We centralise every tunable here behind a validated Pydantic model. Business
thresholds (e.g. what counts as a "premium" customer) live in code review, not
in someone's head.

Resolution order for any value: explicit env var (prefix ``DCV_``) > ``.env``
file > the defaults defined below. The database URL is derived intelligently so
the project runs on SQLite with zero setup but switches to PostgreSQL by setting
a single variable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (config/settings.py -> repo root).
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BusinessThresholds(BaseSettings):
    """Business rules that define the analytical taxonomy.

    These are deliberately *configuration*, not constants buried in functions,
    because they encode commercial policy. A growth lead should be able to ask
    "what if a premium customer is someone in the top 15% rather than 20%?"
    and change one value, re-run, and see the impact — without reading Python.
    """

    model_config = SettingsConfigDict(env_prefix="DCV_THRESH_", extra="ignore")

    # Revenue / value tiers are percentile-based (robust to the dataset's scale).
    premium_value_percentile: float = Field(0.80, ge=0.5, le=0.99)
    high_value_percentile: float = Field(0.60, ge=0.5, le=0.99)

    # A satisfied customer rates at or above this (dataset ratings run 2.5–5.0).
    satisfaction_rating_floor: float = Field(3.8, ge=1.0, le=5.0)

    # "Repeat" behaviour: more historical purchases than this median-anchored cut.
    repeat_purchase_floor: int = Field(10, ge=0)

    # Promo dependency: a customer whose engagement is gated on discounts.
    promo_dependent_threshold: float = Field(0.5, ge=0.0, le=1.0)


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_prefix="DCV_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Paths (relative paths are resolved against PROJECT_ROOT) -------------
    raw_data_path: Path = Field(default=Path("data/raw/Dataset.csv"))
    processed_dir: Path = Field(default=Path("data/processed"))
    reports_dir: Path = Field(default=Path("reports"))
    sql_dir: Path = Field(default=Path("src/sql"))

    # --- Pipeline behaviour --------------------------------------------------
    log_level: str = Field(default="INFO")
    random_seed: int = Field(default=42)
    strict_validation: bool = Field(default=True)
    n_segments: int = Field(default=5, ge=2, le=12)

    # --- Database ------------------------------------------------------------
    db_url: str | None = Field(default=None)
    db_backend: str = Field(default="sqlite")  # "sqlite" | "postgres"
    pg_host: str = Field(default="localhost")
    pg_port: int = Field(default=5432)
    pg_user: str = Field(default="dcv_user")
    pg_password: str = Field(default="change_me")
    pg_database: str = Field(default="dcv")

    thresholds: BusinessThresholds = Field(default_factory=BusinessThresholds)

    # --- Derived absolute paths ---------------------------------------------
    def _abs(self, p: Path) -> Path:
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def raw_data_file(self) -> Path:
        return self._abs(self.raw_data_path)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def processed_path(self) -> Path:
        return self._abs(self.processed_dir)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reports_path(self) -> Path:
        return self._abs(self.reports_dir)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlite_file(self) -> Path:
        return self.processed_path / "customer_value.db"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_db_url(self) -> str:
        """Return the SQLAlchemy URL, deriving a sensible default if unset.

        Precedence: explicit ``DCV_DB_URL`` > Postgres parts (if backend=postgres)
        > local SQLite file. SQLite keeps the project runnable with no services.
        """
        if self.db_url:
            return self.db_url
        if self.db_backend.lower() == "postgres":
            return (
                f"postgresql+psycopg2://{self.pg_user}:{self.pg_password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
            )
        return f"sqlite:///{self.sqlite_file}"

    def ensure_dirs(self) -> None:
        """Create output directories if they do not yet exist (idempotent)."""
        for d in (self.processed_path, self.reports_path, self.reports_path / "figures"):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton accessor — import this everywhere instead of constructing."""
    return Settings()
