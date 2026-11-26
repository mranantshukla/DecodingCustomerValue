"""Optional Pandera data contract (declarative equivalent of validate.py).

This module is imported lazily and only if `pandera` is installed (it is an
optional extra: `pip install '.[validation]'`). The core pipeline runs without
it. Teams that standardise on Pandera can call `validate_with_pandera(df)` to
enforce the same contract declaratively and get Pandera's rich error frames.
"""

from __future__ import annotations

import pandas as pd

from src.utils.schema import CATEGORY_DOMAINS


def build_schema():  # pragma: no cover - exercised only when pandera installed
    """Construct and return a pandera DataFrameSchema for the cleaned data."""
    import pandera as pa
    from pandera import Check, Column

    return pa.DataFrameSchema(
        {
            "customer_id": Column(int, unique=True, nullable=False),
            "age": Column("Int64", Check.in_range(0, 120), nullable=False),
            "purchase_amount": Column(float, Check.in_range(0, 100_000), nullable=False),
            "review_rating": Column(float, Check.in_range(1.0, 5.0), nullable=False),
            "previous_purchases": Column("Int64", Check.ge(0), nullable=False),
            "gender": Column(str, Check.isin(CATEGORY_DOMAINS["gender"])),
            "category": Column(str, Check.isin(CATEGORY_DOMAINS["category"])),
            "season": Column(str, Check.isin(CATEGORY_DOMAINS["season"])),
            "subscription_status": Column(str, Check.isin(CATEGORY_DOMAINS["subscription_status"])),
        },
        strict=False,
        coerce=True,
    )


def validate_with_pandera(df: pd.DataFrame) -> pd.DataFrame:  # pragma: no cover
    """Validate `df` against the Pandera schema, returning it unchanged on success."""
    schema = build_schema()
    return schema.validate(df, lazy=True)
