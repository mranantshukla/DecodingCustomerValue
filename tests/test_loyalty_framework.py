"""Tests for the loyalty A/B framework and segmentation."""

from __future__ import annotations

import pandas as pd

from src.business_logic.loyalty_framework import (
    CRITERIA_WEIGHTS,
    attach_canonical_loyalty,
    evaluate_loyalty_definitions,
)
from src.business_logic.segmentation import assign_personas, persona_summary, segment_customers


def test_framework_selects_a_valid_winner(feature_df: pd.DataFrame):
    result = evaluate_loyalty_definitions(feature_df)
    assert result.winner in {"loyalty_score_v1", "loyalty_score_v2"}
    assert len(result.scores) == 2


def test_criteria_weights_sum_to_one():
    assert abs(sum(CRITERIA_WEIGHTS.values()) - 1.0) < 1e-9


def test_all_criteria_scored_in_unit_range(feature_df: pd.DataFrame):
    result = evaluate_loyalty_definitions(feature_df)
    for s in result.scores:
        for name, val in s.criteria.items():
            assert 0.0 <= val <= 1.0, f"{s.name}.{name}={val} out of range"


def test_canonical_loyalty_attached(feature_df: pd.DataFrame):
    result = evaluate_loyalty_definitions(feature_df)
    df = attach_canonical_loyalty(feature_df, result.winner)
    assert "loyalty_score" in df.columns
    assert "loyalty_tier" in df.columns
    pd.testing.assert_series_equal(df["loyalty_score"], df[result.winner], check_names=False)


def test_personas_are_mutually_exclusive(feature_df: pd.DataFrame):
    result = evaluate_loyalty_definitions(feature_df)
    df = attach_canonical_loyalty(feature_df, result.winner)
    df = assign_personas(df)
    # Exactly one persona per customer (it's a single string column).
    assert df["customer_persona"].notna().all()
    assert df["customer_persona"].nunique() <= 7


def test_persona_summary_shares_sum_to_one(feature_df: pd.DataFrame):
    result = evaluate_loyalty_definitions(feature_df)
    df = segment_customers(attach_canonical_loyalty(feature_df, result.winner))
    summary = persona_summary(df)
    # Shares are rounded to 4dp for display, so allow a small rounding tolerance.
    assert abs(summary["clv_share"].sum() - 1.0) < 2e-3
    assert abs(summary["customer_share"].sum() - 1.0) < 2e-3
