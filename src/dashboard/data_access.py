"""Cached data access for the Streamlit dashboard.

The dashboard reads the pipeline's output (`customer_features.csv`). If it is
missing, we run the pipeline once on demand so a fresh clone is never a blank
screen. All loaders are cached so navigating between pages is instant.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Make `src`/`config` importable when Streamlit is launched from the repo root.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from config.settings import get_settings  # noqa: E402


@st.cache_data(show_spinner="Loading customer intelligence…")
def load_features() -> pd.DataFrame:
    """Load the engineered, segmented customer table; build it if absent."""
    settings = get_settings()
    path = settings.processed_path / "customer_features.csv"
    if not path.exists():
        from src.pipeline import run_pipeline

        run_pipeline(settings, build_sql=True)
    return pd.read_csv(path)


@st.cache_data
def load_view(name: str) -> pd.DataFrame:
    """Load a materialised SQL view export by short name (e.g. 'persona_scorecard')."""
    settings = get_settings()
    path = settings.reports_path / "sql_exports" / f"{name}.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_report_text(filename: str) -> str:
    settings = get_settings()
    path = settings.reports_path / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def kpis(df: pd.DataFrame) -> dict:
    """Headline KPIs computed directly from the feature table (always fresh)."""
    total_clv = float(df["estimated_clv_proxy"].sum())
    cut = df["estimated_clv_proxy"].quantile(0.80)
    return {
        "customers": len(df),
        "total_clv": total_clv,
        "avg_clv": total_clv / len(df),
        "avg_loyalty": float(df["loyalty_score"].mean()),
        "avg_promo": float(df["promo_dependency_score"].mean()),
        "pct_premium": 100 * float(df["premium_customer_flag"].mean()),
        "pct_satisfied": 100 * float(df["satisfaction_flag"].mean()),
        "top20_share": 100
        * float(df.loc[df["estimated_clv_proxy"] >= cut, "estimated_clv_proxy"].sum() / total_clv),
    }
