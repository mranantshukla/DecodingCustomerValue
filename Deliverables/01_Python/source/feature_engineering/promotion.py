"""Promotion / discount-dependency feature family.

A consulting caveat baked into the code: in this dataset ``discount_applied`` and
``promo_code_used`` are perfectly collinear, and discounting is structurally
entangled with subscription and gender (every subscriber is discounted; every
discounted customer is male). We therefore:

  * use ``discount_applied`` as the single canonical promo signal (the redundant
    ``promo_code_used`` is dropped in build_features),
  * blend the individual discount flag with a *segment* discount rate so the
    dependency score is not a bare 0/1, and
  * compute elasticity at the category/region level (where it is identifiable)
    rather than pretending we can measure it per single transaction.
"""

from __future__ import annotations

import pandas as pd

from src.feature_engineering.base import tier_from_percentile

SEGMENT_WEIGHT = 0.30  # weight on the micro-segment rate vs the individual flag


def add_promotion_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    disc = df["discount_applied_flag"].astype(float)

    # Non-discount purchase ratio: cleanest full-price signal (used by loyalty v2).
    df["non_discount_purchase_ratio"] = 1.0 - disc

    # Segment discount rate: discount penetration within (location, category).
    seg = df.groupby(["location", "category"])["discount_applied_flag"].transform("mean")
    # Promo dependency: blend the individual with their micro-segment baseline.
    df["promo_dependency_score"] = ((1 - SEGMENT_WEIGHT) * disc + SEGMENT_WEIGHT * seg).clip(0, 1)

    # Discount elasticity proxy (category level, attached per customer): does
    # discounting associate with bigger or smaller baskets within the category?
    elasticity = _category_elasticity(df)
    df["discount_elasticity_proxy"] = df["category"].map(elasticity).astype(float)

    # Plain-English reliance tier for the sunset plan.
    df["promo_reliance_tier"] = tier_from_percentile(
        df["promo_dependency_score"],
        labels=["Full-Price Loyalist", "Occasional Discount", "Discount-Dependent"],
        quantiles=[0.0, 0.34, 0.66, 1.0],
    )
    return df


def _category_elasticity(df: pd.DataFrame) -> dict[str, float]:
    """(mean spend among discounted - mean among full) / mean among full, by category."""
    out: dict[str, float] = {}
    for cat, g in df.groupby("category"):
        full = g.loc[~g["discount_applied_flag"], "purchase_amount"].mean()
        disc = g.loc[g["discount_applied_flag"], "purchase_amount"].mean()
        if pd.notna(full) and full != 0 and pd.notna(disc):
            out[cat] = float((disc - full) / full)
        else:
            out[cat] = 0.0
    return out
