"""Shared pytest fixtures.

We build the cleaned + feature-engineered frames ONCE per test session (they are
deterministic and cheap) and hand read-only copies to tests. A small synthetic
frame is also provided for unit tests that should not depend on the real file.
"""

from __future__ import annotations

import pandas as pd
import pytest

from config.settings import get_settings
from src.data_processing.clean import clean_dataset
from src.feature_engineering.build_features import build_features
from src.utils.io import read_csv


@pytest.fixture(scope="session")
def raw_df() -> pd.DataFrame:
    return read_csv(get_settings().raw_data_file)


@pytest.fixture(scope="session")
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    return clean_dataset(raw_df)


@pytest.fixture(scope="session")
def feature_df(clean_df: pd.DataFrame) -> pd.DataFrame:
    return build_features(clean_df)


@pytest.fixture
def synthetic_raw() -> pd.DataFrame:
    """A tiny, hand-built raw frame exercising edge cases (dupes, casing, nulls)."""
    return pd.DataFrame(
        {
            "Customer ID": [1, 2, 3, 3],  # duplicate id (3)
            "Age": [25, 40, 60, 60],
            "Gender": ["Male", "female", "Male", "Male"],  # casing drift
            "Item Purchased": ["Blouse", "Jeans", "Boots", "Boots"],
            "Category": ["Clothing", "Clothing", "Footwear", "Footwear"],
            "Purchase Amount (USD)": [50, 80, 120, 120],
            "Location": ["Maine", "Texas", "Texas", "Texas"],
            "Size": ["M", "L", "S", "S"],
            "Color": ["Gray", "Blue", "Black", "Black"],
            "Season": ["Winter", "Spring", "Fall", "Fall"],
            "Review Rating": [4.5, None, 3.0, 3.0],  # one null
            "Subscription Status": ["Yes", "No", "No", "No"],
            "Shipping Type": ["Express", "Standard", "Store Pickup", "Store Pickup"],
            "Discount Applied": ["No", "Yes", "Yes", "Yes"],
            "Promo Code Used": ["No", "Yes", "Yes", "Yes"],
            "Previous Purchases": [10, 2, 45, 45],
            "Payment Method": ["Credit Card", "Cash", "PayPal", "PayPal"],
            "Frequency of Purchases": ["Weekly", "Annually", "Monthly", "Monthly"],
        }
    )
