"""Shared, well-behaved transforms used across all feature modules.

Centralising normalisation matters: if loyalty min-max scales one way and value
scales another, the scores are not comparable and every blended index is subtly
wrong. One implementation, used everywhere, keeps features on a common footing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def minmax(s: pd.Series) -> pd.Series:
    """Scale to [0, 1]. Constant series -> 0.5 (neutral) to avoid divide-by-zero."""
    s = pd.to_numeric(s, errors="coerce").astype(float)
    lo, hi = s.min(), s.max()
    if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
        return pd.Series(np.full(len(s), 0.5), index=s.index)
    return (s - lo) / (hi - lo)


def zscore(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").astype(float)
    std = s.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.mean()) / std


def sigmoid(s: pd.Series) -> pd.Series:
    return 1.0 / (1.0 + np.exp(-pd.to_numeric(s, errors="coerce").astype(float)))


def percentile_rank(s: pd.Series) -> pd.Series:
    """Empirical percentile in [0, 1]; robust to scale and outliers."""
    return pd.to_numeric(s, errors="coerce").rank(pct=True)


def tier_from_percentile(
    s: pd.Series, labels: list[str], quantiles: list[float] | None = None
) -> pd.Series:
    """Bucket a continuous score into named tiers by quantile.

    Uses rank-based quantiles so ties and skew never produce empty bins.
    """
    n = len(labels)
    q = quantiles or list(np.linspace(0, 1, n + 1))
    ranks = s.rank(pct=True, method="first")
    cuts = pd.cut(ranks, bins=q, labels=labels, include_lowest=True)
    return cuts.astype("string")


def safe_div(num: pd.Series, den: pd.Series, fill: float = 0.0) -> pd.Series:
    out = num / den.replace(0, np.nan)
    return out.fillna(fill)
