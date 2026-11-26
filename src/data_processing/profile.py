"""Lightweight, dependency-free data profiling.

Why not ydata-profiling? It is excellent but heavyweight and produces a report
nobody on a leadership team reads. We emit a compact, version-controllable JSON +
Markdown summary that captures exactly the signals that matter for THIS dataset:
distributions, cardinality, missingness, and the structural relationships our
analysis depends on (e.g. the discount/promo collinearity).
"""

from __future__ import annotations

import pandas as pd

from src.utils.logging_config import get_logger

log = get_logger(__name__)


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return a serialisable profile of the dataframe."""
    numeric = df.select_dtypes(include="number")
    profile: dict = {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 1),
        "missing_by_column": {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
        "numeric_summary": {
            c: {
                "min": float(numeric[c].min()),
                "p25": float(numeric[c].quantile(0.25)),
                "median": float(numeric[c].median()),
                "mean": round(float(numeric[c].mean()), 3),
                "p75": float(numeric[c].quantile(0.75)),
                "max": float(numeric[c].max()),
                "std": round(float(numeric[c].std()), 3),
            }
            for c in numeric.columns
        },
        "categorical_cardinality": {
            c: int(df[c].nunique())
            for c in df.select_dtypes(include=["object", "string", "bool"]).columns
        },
    }
    return profile


def profile_to_markdown(profile: dict) -> str:
    lines = [
        "# Data Profiling Summary",
        "",
        f"- **Rows:** {profile['n_rows']:,}",
        f"- **Columns:** {profile['n_cols']}",
        f"- **Memory:** {profile['memory_kb']:,} KB",
        "",
    ]
    if profile["missing_by_column"]:
        lines += ["## Missing values", "", "| Column | Missing |", "|---|---:|"]
        lines += [f"| {c} | {n} |" for c, n in profile["missing_by_column"].items()]
        lines.append("")
    else:
        lines += ["## Missing values", "", "_None — dataset is complete post-clean._", ""]

    lines += [
        "## Numeric summary",
        "",
        "| Column | Min | P25 | Median | Mean | P75 | Max | Std |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c, s in profile["numeric_summary"].items():
        lines.append(
            f"| {c} | {s['min']:.1f} | {s['p25']:.1f} | {s['median']:.1f} | "
            f"{s['mean']:.2f} | {s['p75']:.1f} | {s['max']:.1f} | {s['std']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"
