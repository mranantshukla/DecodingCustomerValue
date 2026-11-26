"""Geography feature family — region-level signals attached to each customer.

These power the "where is demand healthy vs propped-up by promotions?" view that
leadership uses for market expansion and rationalisation decisions.

Caveat carried from the promotion module: regional discount rates partly reflect
the dataset's gender/subscription confound, not pure regional behaviour. The
analysis layer reports these alongside gender mix so the confound stays visible.
"""

from __future__ import annotations

import pandas as pd

from src.feature_engineering.base import minmax


def add_geography_features(df: pd.DataFrame) -> pd.DataFrame:
    """Requires ``loyalty_score_v2`` and ``estimated_clv_proxy`` to already exist."""
    df = df.copy()

    loc = df.groupby("location")
    loc_discount_rate = loc["discount_applied_flag"].transform("mean")
    loc_avg_loyalty = loc["loyalty_score_v2"].transform("mean")
    loc_avg_sat = loc["review_rating"].transform("mean")
    loc_avg_clv = loc["estimated_clv_proxy"].transform("mean")

    # Organic demand: full-price share of a region's activity.
    df["organic_demand_score"] = (1.0 - loc_discount_rate).clip(0, 1)

    # Region quality: blended health score (loyalty, satisfaction, organic, value).
    df["region_quality_index"] = (
        0.25 * minmax(loc_avg_loyalty)
        + 0.25 * minmax(loc_avg_sat)
        + 0.25 * df["organic_demand_score"]
        + 0.25 * minmax(loc_avg_clv)
    ).clip(0, 1)

    # Regional promo sensitivity (discount elasticity within the region).
    sens = _region_elasticity(df)
    df["promo_sensitivity_geo"] = df["location"].map(sens).astype(float)
    return df


def _region_elasticity(df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    for loc, g in df.groupby("location"):
        full = g.loc[~g["discount_applied_flag"], "purchase_amount"].mean()
        disc = g.loc[g["discount_applied_flag"], "purchase_amount"].mean()
        if pd.notna(full) and full != 0 and pd.notna(disc):
            out[loc] = float((disc - full) / full)
        else:
            out[loc] = 0.0
    return out
