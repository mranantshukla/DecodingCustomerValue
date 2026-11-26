"""Feature-engineering orchestrator.

Composes the five feature families in strict dependency order:

    base derived cols
      -> promotion (creates non_discount_purchase_ratio used by loyalty)
      -> loyalty   (creates loyalty_score_v2 used by value + geography)
      -> value     (creates estimated_clv_proxy used by geography)
      -> behavioural
      -> geography (consumes loyalty_v2 + clv)

Ordering is explicit and documented because silent column-not-found bugs are the
classic failure mode of feature pipelines. The redundant ``promo_code_used``
column is dropped here (it is perfectly collinear with ``discount_applied``).
"""

from __future__ import annotations

import pandas as pd

from src.feature_engineering.base import minmax
from src.feature_engineering.behavioral import add_behavioral_features
from src.feature_engineering.geography import add_geography_features
from src.feature_engineering.loyalty import add_loyalty_features
from src.feature_engineering.promotion import add_promotion_features
from src.feature_engineering.registry import feature_names
from src.feature_engineering.value import add_value_features
from src.utils.logging_config import get_logger
from src.utils.schema import FREQUENCY_RANK, FREQUENCY_TO_ANNUAL

log = get_logger(__name__)


def _add_base_derivations(df: pd.DataFrame) -> pd.DataFrame:
    """Shared derived columns every family relies on."""
    df = df.copy()
    df["annual_purchase_freq"] = df["frequency_of_purchases"].map(FREQUENCY_TO_ANNUAL).fillna(1.0)
    df["freq_rank"] = df["frequency_of_purchases"].map(FREQUENCY_RANK).fillna(1).astype(int)
    df["freq_rank_norm"] = df["freq_rank"] / max(FREQUENCY_RANK.values())
    # Satisfaction normalised from the 1–5 rating scale to [0, 1].
    df["satisfaction_norm"] = ((df["review_rating"] - 1.0) / 4.0).clip(0, 1)
    df["age_norm"] = minmax(df["age"])
    return df


def build_features(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Return the analysis-ready feature table (one row per customer)."""
    log.info("Engineering features for %d customers", len(clean_df))

    df = _add_base_derivations(clean_df)

    # Drop the redundant promo column (collinear with discount_applied). Keep the
    # flag form for reference but remove the duplicate string column.
    if "promo_code_used" in df.columns:
        df = df.drop(columns=["promo_code_used"])

    df = add_promotion_features(df)  # -> non_discount_purchase_ratio, promo_*
    df = add_loyalty_features(df)  # -> loyalty_score_v1/v2, etc.
    df = add_value_features(df)  # -> estimated_clv_proxy, premium flag, etc.
    df = add_behavioral_features(df)
    df = add_geography_features(df)  # consumes loyalty_v2 + clv

    _assert_registry_complete(df)
    log.info("Feature engineering complete: %d features registered", len(feature_names()))
    return df


def _assert_registry_complete(df: pd.DataFrame) -> None:
    """Fail loudly if a registered feature was not produced (docs/code drift guard)."""
    missing = [f for f in feature_names() if f not in df.columns]
    if missing:
        raise RuntimeError(
            f"Registered features missing from output: {missing}. "
            "Update build order or registry.py."
        )
