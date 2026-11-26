"""Loyalty feature family.

Two competing loyalty scores are produced here on purpose. Definition A
(``loyalty_score_v1``) is volume-led and intuitive. Definition B
(``loyalty_score_v2``) is margin-aware: it rewards full-price, satisfied,
frequent buyers and discounts discount-driven activity. The loyalty framework
(``src/business_logic/loyalty_framework.py``) formally compares the two and
selects one — this module just computes both honestly.
"""

from __future__ import annotations

import pandas as pd

from src.feature_engineering.base import minmax

# Weights are module-level constants so they are reviewable and testable, not
# buried as literals inside the formulas.
V1_WEIGHTS = {"prev": 0.50, "freq": 0.30, "sub": 0.20}
V2_WEIGHTS = {"prev": 0.35, "freq": 0.25, "sub": 0.15, "sat": 0.15, "ndr": 0.10}


def add_loyalty_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all loyalty-family features. Requires base derived columns:
    ``freq_rank_norm``, ``satisfaction_norm``, ``annual_purchase_freq``,
    ``subscription_status_flag``, ``non_discount_purchase_ratio``.
    """
    df = df.copy()
    prev_norm = minmax(df["previous_purchases"])
    freq_norm = df["freq_rank_norm"]
    sub = df["subscription_status_flag"].astype(float)
    sat = df["satisfaction_norm"]
    # non_discount_purchase_ratio is created in the promotion module; if features
    # are computed in registry order it exists. Guard for standalone use.
    ndr = (
        df["non_discount_purchase_ratio"]
        if "non_discount_purchase_ratio" in df
        else (1.0 - df["discount_applied_flag"].astype(float))
    )

    # Definition A — volume-led.
    df["loyalty_score_v1"] = (
        V1_WEIGHTS["prev"] * prev_norm + V1_WEIGHTS["freq"] * freq_norm + V1_WEIGHTS["sub"] * sub
    ).clip(0, 1)

    # Definition B — margin-aware quality of loyalty.
    df["loyalty_score_v2"] = (
        V2_WEIGHTS["prev"] * prev_norm
        + V2_WEIGHTS["freq"] * freq_norm
        + V2_WEIGHTS["sub"] * sub
        + V2_WEIGHTS["sat"] * sat
        + V2_WEIGHTS["ndr"] * ndr
    ).clip(0, 1)

    # Confidence: trust the score more when there is real history and an observed
    # (not imputed) satisfaction reading.
    not_imputed = 1.0 - df.get("review_rating_imputed", pd.Series(False, index=df.index)).astype(
        float
    )
    df["loyalty_confidence_index"] = (0.60 * prev_norm + 0.40 * not_imputed).clip(0, 1)

    # Repeat purchase intensity: momentum = lifetime volume * current cadence.
    intensity_raw = df["previous_purchases"].astype(float) * df["annual_purchase_freq"]
    df["repeat_purchase_intensity"] = minmax(intensity_raw)

    # Brand affinity: attitudinal closeness, distinct from raw volume.
    df["brand_affinity_score"] = (0.30 * sub + 0.30 * sat + 0.20 * freq_norm + 0.20 * ndr).clip(
        0, 1
    )

    return df
