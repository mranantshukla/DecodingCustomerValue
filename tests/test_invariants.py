"""Property / invariant tests, noise-robustness, and lightweight fuzz.

These check things that should always be true regardless of the specific row mix:
monotonicity of scores, stability under small input noise, and ordering invariants
between derived columns. They catch a class of regression that point-value tests
miss (e.g. a sign flip that still keeps values inside [0, 1]).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.business_logic.loyalty_framework import evaluate_loyalty_definitions
from src.feature_engineering.build_features import build_features

# --- 1. Score monotonicity ---------------------------------------------------


def test_loyalty_v1_monotone_in_previous_purchases(clean_df: pd.DataFrame):
    """Holding cadence & subscription fixed, more lifetime purchases must not
    DECREASE loyalty_v1 (it's a positive coefficient in the formula)."""
    feat = build_features(clean_df)
    # Pick a stable comparable cohort: subscribers on weekly cadence.
    cohort = feat[
        (feat["subscription_status"] == "Yes") & (feat["frequency_of_purchases"] == "Weekly")
    ].copy()
    cohort = cohort.sort_values("previous_purchases")
    # Monotone non-decreasing in previous_purchases (the dominant v1 term).
    assert (
        cohort["loyalty_score_v1"].is_monotonic_increasing
        or (cohort["loyalty_score_v1"].diff().dropna() >= -1e-9).all()
    )


def test_clv_increases_with_economic_value(feature_df: pd.DataFrame):
    """CLV = economic_value * tenure, both non-negative => correlation must be positive."""
    r = feature_df["estimated_clv_proxy"].corr(feature_df["economic_value_proxy"])
    assert r > 0.5  # strong positive, not necessarily 1 (tenure introduces variance)


def test_tier_ordering_matches_clv(feature_df: pd.DataFrame):
    """The mean CLV in Platinum > Gold > Silver > Bronze."""
    means = feature_df.groupby("revenue_contribution_tier")["estimated_clv_proxy"].mean().to_dict()
    assert means["Platinum"] > means["Gold"] > means["Silver"] > means["Bronze"]


# --- 2. Orthogonality of the loyalty validation target ----------------------


def test_economic_value_does_not_use_loyalty(feature_df: pd.DataFrame):
    """economic_value_proxy must equal annual_value * margin_factor exactly —
    proving loyalty plays NO role in the loyalty-framework validation target."""
    expected = (feature_df["annual_value"] * feature_df["margin_factor"]).round(2)
    pd.testing.assert_series_equal(
        feature_df["economic_value_proxy"].round(2), expected, check_names=False
    )


def test_clv_decomposition_holds(feature_df: pd.DataFrame):
    """estimated_clv_proxy = economic_value_proxy * expected_tenure_years (within rounding)."""
    reconstructed = (
        feature_df["economic_value_proxy"] * feature_df["expected_tenure_years"]
    ).round(2)
    # Allow a tiny rounding cushion (both inputs are pre-rounded).
    diff = (reconstructed - feature_df["estimated_clv_proxy"]).abs()
    assert (diff <= 0.02).all(), f"CLV decomposition broken (max diff {diff.max()})"


# --- 3. Noise robustness ----------------------------------------------------


def test_top_quintile_stable_under_small_noise(clean_df: pd.DataFrame):
    """A ±1% multiplicative perturbation of purchase_amount must not move >25%
    of customers in/out of the top CLV quintile. This guards the headline
    'protect the top 20%' against being an artefact of micro-precision."""
    rng = np.random.default_rng(42)
    base = build_features(clean_df)
    top_n = max(1, len(base) // 5)
    base_top = set(base.nlargest(top_n, "estimated_clv_proxy")["customer_id"])

    noisy = clean_df.copy()
    noise = rng.uniform(0.99, 1.01, size=len(noisy))
    noisy["purchase_amount"] = noisy["purchase_amount"] * noise
    noisy_feat = build_features(noisy)
    noisy_top = set(noisy_feat.nlargest(top_n, "estimated_clv_proxy")["customer_id"])

    jaccard = len(base_top & noisy_top) / len(base_top | noisy_top)
    assert jaccard >= 0.75, f"top quintile unstable under 1% noise (jaccard={jaccard:.3f})"


def test_loyalty_winner_stable_under_small_noise(clean_df: pd.DataFrame):
    """The loyalty A/B winner shouldn't flip under 1% multiplicative noise."""
    rng = np.random.default_rng(7)
    base_winner = evaluate_loyalty_definitions(build_features(clean_df)).winner
    noisy = clean_df.copy()
    noisy["purchase_amount"] = noisy["purchase_amount"] * rng.uniform(0.99, 1.01, len(noisy))
    noisy_winner = evaluate_loyalty_definitions(build_features(noisy)).winner
    assert base_winner == noisy_winner


# --- 4. Fuzz on subset selection --------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_random_subset_features_still_in_unit_range(clean_df: pd.DataFrame, seed: int):
    """For random subsets of the customer base, all unit-scaled features stay in [0,1]."""
    rng = np.random.default_rng(seed)
    sample = clean_df.sample(n=600, random_state=int(rng.integers(0, 1_000_000)))
    feat = build_features(sample)
    for col in [
        "loyalty_score_v1",
        "loyalty_score_v2",
        "promo_dependency_score",
        "shipping_urgency_index",
        "payment_repeat_index",
    ]:
        assert feat[col].between(0, 1).all(), f"{col} escaped [0,1] on seed {seed}"


# --- 5. Negative cases ------------------------------------------------------


def test_cleaning_rejects_missing_required_column(synthetic_raw: pd.DataFrame):
    """Removing a required column must surface as a clear ValueError, not silent drift."""
    from src.data_processing.clean import clean_dataset

    broken = synthetic_raw.drop(columns=["Customer ID"])
    with pytest.raises(ValueError, match="missing expected columns"):
        clean_dataset(broken)


def test_validation_flags_broken_discount_promo_relationship(clean_df: pd.DataFrame):
    """If a future data drop has Discount/Promo divergence, the soft-check should fire."""
    from src.data_processing.validate import validate

    tampered = clean_df.copy()
    tampered.loc[tampered.index[:5], "promo_code_used"] = "No"
    tampered.loc[tampered.index[:5], "discount_applied"] = "Yes"
    rep = validate(tampered)
    check = next(r for r in rep.results if r.name == "discount_promo_collinear")
    assert not check.passed
