"""Tests for the feature-engineering system."""

from __future__ import annotations

import pandas as pd

from src.feature_engineering.registry import feature_names


def test_all_registered_features_present(feature_df: pd.DataFrame):
    missing = [f for f in feature_names() if f not in feature_df.columns]
    assert not missing, f"registered but not produced: {missing}"


def test_normalised_scores_in_unit_range(feature_df: pd.DataFrame):
    unit_features = [
        "loyalty_score_v1",
        "loyalty_score_v2",
        "loyalty_confidence_index",
        "repeat_purchase_intensity",
        "brand_affinity_score",
        "promo_dependency_score",
        "non_discount_purchase_ratio",
        "high_value_probability",
        "organic_demand_score",
        "region_quality_index",
        "shipping_urgency_index",
        "payment_repeat_index",  # renamed from payment_stability_score
        "seasonal_consistency_score",
    ]
    for col in unit_features:
        assert feature_df[col].between(0, 1).all(), f"{col} escaped [0,1]"


def test_clv_is_positive(feature_df: pd.DataFrame):
    assert (feature_df["estimated_clv_proxy"] > 0).all()


def test_premium_flag_is_top_quintile(feature_df: pd.DataFrame):
    # Premium ~ top 20% by construction (P80 cutoff).
    share = feature_df["premium_customer_flag"].mean()
    assert 0.15 <= share <= 0.25


def test_promo_code_column_dropped(feature_df: pd.DataFrame):
    # Redundant collinear column must be removed in feature engineering.
    assert "promo_code_used" not in feature_df.columns


def test_loyalty_v2_rewards_full_price(feature_df: pd.DataFrame):
    """At similar volume, full-price customers should not score below discount-driven ones."""
    full = feature_df[feature_df["non_discount_purchase_ratio"] == 1]["loyalty_score_v2"].mean()
    disc = feature_df[feature_df["non_discount_purchase_ratio"] == 0]["loyalty_score_v2"].mean()
    assert full >= disc


def test_tiers_have_expected_cardinality(feature_df: pd.DataFrame):
    assert feature_df["revenue_contribution_tier"].nunique() == 4
    assert feature_df["promo_reliance_tier"].nunique() == 3


def test_features_are_deterministic(clean_df: pd.DataFrame):
    from src.feature_engineering.build_features import build_features

    a = build_features(clean_df)["estimated_clv_proxy"]
    b = build_features(clean_df)["estimated_clv_proxy"]
    pd.testing.assert_series_equal(a, b)
