"""Customer-value feature family.

Two value metrics are produced on purpose:

  economic_value_proxy   = annual_value * margin_factor
                         = (purchase_amount * annual_purchase_freq) * (1 - 0.15 * discount_flag)
      Current-period, margin-adjusted value. **Contains no loyalty term**, so it
      can be used as the *orthogonal* target when validating the loyalty model
      (see ``src/business_logic/loyalty_framework.py``).

  expected_tenure_years  = 1 + 4 * loyalty_score_v2          (range 1–5)
      Exposed as its own column so the assumption is auditable, not hidden.

  estimated_clv_proxy    = economic_value_proxy * expected_tenure_years
      Forward-looking composite. CLV is *meant* to reflect retention prospects,
      so it uses loyalty by design — that's why we evaluate the loyalty model
      against `economic_value_proxy`, not `estimated_clv_proxy`.

This decomposition fixes a subtle but real circularity in the previous version:
loyalty fed into tenure, tenure fed into CLV, and the loyalty framework then
compared loyalty to CLV — which was partly self-correlation. The split keeps the
business framing (a forward CLV) without contaminating the validation target.

``high_value_probability`` is a transparent logistic transform of *non-spend*
behavioural signals — so it can score low-history customers without leakage from
the value they are trying to predict.
"""

from __future__ import annotations

import pandas as pd

from config.settings import get_settings
from src.feature_engineering.base import sigmoid, tier_from_percentile, zscore

MARGIN_HAIRCUT = 0.15  # assumed gross-margin erosion when a discount is applied
MIN_TENURE_YEARS = 1.0
MAX_TENURE_BONUS = 4.0  # loyalty maps tenure into [1, 5] years


def add_value_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    settings = get_settings()

    # --- Loyalty-free building blocks ---------------------------------------
    annual_value = df["purchase_amount"].astype(float) * df["annual_purchase_freq"]
    margin_factor = 1.0 - MARGIN_HAIRCUT * df["discount_applied_flag"].astype(float)

    df["annual_value"] = annual_value
    df["margin_factor"] = margin_factor.round(4)
    # The orthogonal value metric used by the loyalty framework.
    df["economic_value_proxy"] = (annual_value * margin_factor).round(2)

    # --- Forward-looking CLV (uses loyalty) ---------------------------------
    df["expected_tenure_years"] = (
        MIN_TENURE_YEARS + MAX_TENURE_BONUS * df["loyalty_score_v2"]
    ).round(3)
    df["estimated_clv_proxy"] = (df["economic_value_proxy"] * df["expected_tenure_years"]).round(2)

    # --- Tiers / flags -------------------------------------------------------
    # Quartiles of CLV (the forward composite — what leadership budgets against).
    df["revenue_contribution_tier"] = tier_from_percentile(
        df["estimated_clv_proxy"],
        labels=["Bronze", "Silver", "Gold", "Platinum"],
        quantiles=[0.0, 0.25, 0.50, 0.75, 1.0],
    )

    # High-value propensity built from non-spend, loyalty-free behavioural signals.
    # Lets us score new/thin-history customers without circularity.
    z = (
        0.40 * zscore(df["annual_purchase_freq"])
        + 0.35 * zscore(df["previous_purchases"])
        + 0.15 * zscore(df["freq_rank_norm"])
        + 0.10 * zscore(df["subscription_status_flag"].astype(float))
    )
    df["high_value_probability"] = sigmoid(z).round(4)

    # Premium flag remains on the forward CLV (it IS a retention/value cohort).
    cutoff = df["estimated_clv_proxy"].quantile(settings.thresholds.premium_value_percentile)
    df["premium_customer_flag"] = df["estimated_clv_proxy"] >= cutoff

    return df
