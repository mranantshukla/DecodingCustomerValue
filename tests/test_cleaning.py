"""Tests for the data-cleaning pipeline and validation engine."""

from __future__ import annotations

import pandas as pd

from src.data_processing.clean import clean_dataset
from src.data_processing.validate import Severity, validate
from src.utils.schema import RAW_TO_CLEAN


def test_columns_standardised(clean_df: pd.DataFrame):
    for clean_name in RAW_TO_CLEAN.values():
        assert clean_name in clean_df.columns, f"missing {clean_name}"


def test_no_duplicate_customer_ids(synthetic_raw: pd.DataFrame):
    cleaned = clean_dataset(synthetic_raw)
    assert cleaned["customer_id"].is_unique
    assert len(cleaned) == 3  # one duplicate removed


def test_casing_normalised(synthetic_raw: pd.DataFrame):
    cleaned = clean_dataset(synthetic_raw)
    assert set(cleaned["gender"].unique()) <= {"Male", "Female"}


def test_review_rating_imputed_with_flag(synthetic_raw: pd.DataFrame):
    cleaned = clean_dataset(synthetic_raw)
    assert cleaned["review_rating"].isna().sum() == 0
    assert "review_rating_imputed" in cleaned.columns
    assert cleaned["review_rating_imputed"].sum() == 1  # exactly the one null


def test_yes_no_flags_created(clean_df: pd.DataFrame):
    assert clean_df["subscription_status_flag"].dtype == bool
    assert clean_df["discount_applied_flag"].sum() == (clean_df["discount_applied"] == "Yes").sum()


def test_validation_passes_on_clean_data(clean_df: pd.DataFrame):
    report = validate(clean_df)
    assert not report.has_errors, "clean data must pass all ERROR-severity checks"


def test_validation_catches_bad_data(clean_df: pd.DataFrame):
    broken = clean_df.copy()
    broken.loc[broken.index[0], "age"] = 999  # out of range
    report = validate(broken)
    age_check = next(r for r in report.results if r.name == "range__age")
    assert not age_check.passed
    assert age_check.severity is Severity.ERROR


def test_discount_promo_collinearity_detected(clean_df: pd.DataFrame):
    report = validate(clean_df)
    check = next(r for r in report.results if r.name == "discount_promo_collinear")
    assert check.passed  # they ARE collinear in source, so the assertion holds
