"""Behavioural feature family.

Refinement notes (vs the v1 implementation):
  * ``shipping_urgency_index`` is now a uniform ordinal rank rather than
    hand-picked gaps — the previous 0.3 / 0.4 step was opinion, not data.
  * ``payment_stability_score`` -> ``payment_repeat_index`` is now derived
    *empirically* from the observed mean previous-purchases per payment method,
    instead of hand-coded "Credit Card = 1.0, Cash = 0.4". If the signal turns
    out to be weak in this data, the feature is *honestly* weak — which is the
    right outcome of a data-driven approach.
  * ``category_breadth_est`` uses percentile rank instead of min-max scaling,
    so it is robust to outliers in ``previous_purchases``.

Honesty caveat unchanged: the source is one transaction per customer, so a few
behavioural constructs cannot be measured directly and are computed as clearly-
labelled estimates. Each feature's ``proxy_quality`` (in the registry) tells
consumers whether it is observed, derived, or estimated.
"""

from __future__ import annotations

import pandas as pd

from config.settings import get_settings
from src.feature_engineering.base import percentile_rank
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# Speed ordering of shipping options. Universally true (Next Day is the fastest;
# Store Pickup involves no shipping). Values are derived as uniform ordinal
# steps below, NOT hand-chosen — see _ordinal_index().
SHIPPING_SPEED_ORDER = [
    "Store Pickup",  # 0.0
    "Free Shipping",  # 0.2
    "Standard",  # 0.4
    "2-Day Shipping",  # 0.6
    "Express",  # 0.8
    "Next Day Air",  # 1.0
]


def _ordinal_index(order: list[str]) -> dict[str, float]:
    """Map an ordered list to a [0, 1] index with uniform steps."""
    n = len(order) - 1
    return {label: round(i / n, 4) for i, label in enumerate(order)}


def _empirical_payment_index(df: pd.DataFrame) -> dict[str, float]:
    """Mean ``previous_purchases`` per payment method, min-max scaled to [0, 1].

    The interpretation is "how repeat-prone are customers using this method, on
    average?". This replaces the hand-coded stability scores.
    """
    by_method = df.groupby("payment_method")["previous_purchases"].mean()
    if by_method.max() == by_method.min():
        # No variation -> flat, neutral score. Honest about lack of signal.
        return dict.fromkeys(by_method.index, 0.5)
    scaled = (by_method - by_method.min()) / (by_method.max() - by_method.min())
    return scaled.round(4).to_dict()


def add_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    settings = get_settings()

    df["satisfaction_flag"] = df["review_rating"] >= settings.thresholds.satisfaction_rating_floor

    # Percentile-rank breadth proxy (rank-based, robust to extremes).
    df["category_breadth_est"] = (1.0 + 3.0 * percentile_rank(df["previous_purchases"])).round(2)

    # Shipping urgency from uniform ordinal positions (no hand-picked gaps).
    shipping_index = _ordinal_index(SHIPPING_SPEED_ORDER)
    df["shipping_urgency_index"] = df["shipping_type"].map(shipping_index).fillna(0.5)

    # Payment repeat index: empirical, not opinion.
    payment_index = _empirical_payment_index(df)
    df["payment_repeat_index"] = df["payment_method"].map(payment_index).fillna(0.5)
    # Back-compat alias (older notebooks/dashboards may still reference this name).
    df["payment_stability_score"] = df["payment_repeat_index"]
    log.info("Empirical payment_repeat_index: %s", payment_index)

    # Seasonal consistency: P(observed season | category).
    share_lookup = (
        df.groupby(["category", "season"])
        .size()
        .div(df.groupby("category").size(), level="category")
    )
    df["seasonal_consistency_score"] = [
        float(share_lookup.get((c, s), 0.0)) for c, s in zip(df["category"], df["season"])
    ]

    return df
