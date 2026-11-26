"""The canonical data contract: raw column names and their clean snake_case forms.

Why a single contract module: every downstream stage (cleaning, features, SQL
load, tests) must agree on column names. Centralising them here means a column
rename is a one-line change, and typos become import errors instead of silent
empty DataFrames.
"""

from __future__ import annotations

from typing import Final

# Raw header (as shipped in data/raw/Dataset.csv) -> clean snake_case name.
RAW_TO_CLEAN: Final[dict[str, str]] = {
    "Customer ID": "customer_id",
    "Age": "age",
    "Gender": "gender",
    "Item Purchased": "item_purchased",
    "Category": "category",
    "Purchase Amount (USD)": "purchase_amount",
    "Location": "location",
    "Size": "size",
    "Color": "color",
    "Season": "season",
    "Review Rating": "review_rating",
    "Subscription Status": "subscription_status",
    "Shipping Type": "shipping_type",
    "Discount Applied": "discount_applied",
    "Promo Code Used": "promo_code_used",
    "Previous Purchases": "previous_purchases",
    "Payment Method": "payment_method",
    "Frequency of Purchases": "frequency_of_purchases",
}

# Convenience groupings used by validation and feature engineering.
ID_COL: Final[str] = "customer_id"

NUMERIC_COLS: Final[list[str]] = [
    "age",
    "purchase_amount",
    "review_rating",
    "previous_purchases",
]

YES_NO_COLS: Final[list[str]] = [
    "subscription_status",
    "discount_applied",
    "promo_code_used",
]

# Allowed category domains. Anything outside these is a data-quality defect.
CATEGORY_DOMAINS: Final[dict[str, set[str]]] = {
    "gender": {"Male", "Female"},
    "category": {"Clothing", "Accessories", "Footwear", "Outerwear"},
    "season": {"Spring", "Summer", "Fall", "Winter"},
    "size": {"S", "M", "L", "XL"},
    "subscription_status": {"Yes", "No"},
    "discount_applied": {"Yes", "No"},
    "promo_code_used": {"Yes", "No"},
    "shipping_type": {
        "Express",
        "Free Shipping",
        "Next Day Air",
        "Standard",
        "Store Pickup",
        "2-Day Shipping",
    },
    "payment_method": {"Venmo", "Cash", "Credit Card", "PayPal", "Debit Card", "Bank Transfer"},
    "frequency_of_purchases": {
        "Weekly",
        "Fortnightly",
        "Bi-Weekly",
        "Monthly",
        "Every 3 Months",
        "Quarterly",
        "Annually",
    },
}

# Map purchase cadence to an annualised purchase count. This is the single most
# important business assumption in the project: with no timestamps, cadence is
# our only proxy for *velocity*. Values are deliberate, documented estimates.
#   - "Bi-Weekly" is treated as "every two weeks" (26/yr); "Fortnightly" is its
#     synonym (the dataset ships both — we map them identically and flag it).
FREQUENCY_TO_ANNUAL: Final[dict[str, float]] = {
    "Weekly": 52.0,
    "Bi-Weekly": 26.0,
    "Fortnightly": 26.0,
    "Monthly": 12.0,
    "Every 3 Months": 4.0,
    "Quarterly": 4.0,
    "Annually": 1.0,
}

# Ordinal rank of cadence (1 = slowest, 7 = fastest) for monotonic features.
FREQUENCY_RANK: Final[dict[str, int]] = {
    "Annually": 1,
    "Quarterly": 2,
    "Every 3 Months": 3,
    "Monthly": 4,
    "Fortnightly": 5,
    "Bi-Weekly": 6,
    "Weekly": 7,
}
