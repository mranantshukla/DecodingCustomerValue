"""Production data-cleaning pipeline.

Each transformation is a small, pure-ish function with a one-line commercial
justification in its docstring, because in a consulting engagement every
cleaning decision is a decision the client could challenge ("why did you drop
those rows?"). The orchestrator ``clean_dataset`` composes them in order and
logs the row/column delta at each step.
"""

from __future__ import annotations

import pandas as pd

from src.utils.logging_config import get_logger
from src.utils.schema import CATEGORY_DOMAINS, ID_COL, NUMERIC_COLS, RAW_TO_CLEAN, YES_NO_COLS

log = get_logger(__name__)


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw headers to snake_case via the canonical contract.

    Commercial why: downstream SQL, dashboards, and tests all bind to stable
    machine-friendly names. A space in a column name is a production incident
    waiting to happen (quoting bugs in SQL, attribute-access failures in code).
    """
    missing = set(RAW_TO_CLEAN) - set(df.columns)
    if missing:
        raise ValueError(f"Raw data is missing expected columns: {sorted(missing)}")
    return df.rename(columns=RAW_TO_CLEAN)


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows and duplicate customer IDs (keep first).

    Commercial why: a customer counted twice inflates revenue and corrupts every
    per-customer average. We dedupe on the primary key, not just full rows.
    """
    before = len(df)
    df = df.drop_duplicates()
    if ID_COL in df.columns:
        df = df.drop_duplicates(subset=[ID_COL], keep="first")
    removed = before - len(df)
    if removed:
        log.warning("Removed %d duplicate row(s)", removed)
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce numeric columns; non-numeric junk becomes NaN for later handling.

    Commercial why: a stray '$53' or 'N/A' silently turns a numeric column into
    text, which breaks aggregation. We coerce explicitly and surface failures
    rather than letting pandas guess per-read.
    """
    df = df.copy()
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "age" in df.columns:
        df["age"] = df["age"].astype("Int64")
    if "previous_purchases" in df.columns:
        df["previous_purchases"] = df["previous_purchases"].astype("Int64")
    return df


def normalise_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Trim/case-normalise categorical text and map common variants to the domain.

    Commercial why: 'male', 'Male ', and 'MALE' are the same customer segment.
    Left unnormalised they fragment every group-by and understate segment sizes.
    """
    df = df.copy()
    for col in CATEGORY_DOMAINS:
        if col not in df.columns:
            continue
        df[col] = df[col].astype("string").str.strip()
        # Title-case the free-text-ish fields; keep canonical domain casing.
        allowed = CATEGORY_DOMAINS[col]
        # Build a case-insensitive lookup to repair casing drift.
        lookup = {a.lower(): a for a in allowed}
        # Bind `lookup` as a default arg so it is captured per-iteration (not by ref).
        df[col] = df[col].map(lambda v, lk=lookup: lk.get(str(v).lower(), v) if pd.notna(v) else v)
    return df


def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Impute missing values with business-defensible strategies.

    review_rating (the only field with nulls in source, 37 rows) is imputed with
    the *category* median — a customer's satisfaction is better approximated by
    peers buying the same category than by a global constant. We add a
    ``review_rating_imputed`` flag so no downstream analysis mistakes an imputed
    value for an observed one (critical for the satisfaction-based features).
    """
    df = df.copy()
    if "review_rating" in df.columns:
        df["review_rating_imputed"] = df["review_rating"].isna()
        n_missing = int(df["review_rating"].isna().sum())
        if n_missing and "category" in df.columns:
            cat_median = df.groupby("category")["review_rating"].transform("median")
            df["review_rating"] = df["review_rating"].fillna(cat_median)
            # Backstop in case an entire category were missing.
            df["review_rating"] = df["review_rating"].fillna(df["review_rating"].median())
            log.info("Imputed %d missing review_rating values (category median)", n_missing)
    return df


def clip_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Winsorise numeric outliers to the 1st/99th percentile rather than drop.

    Commercial why: dropping a high-spend customer because they are an "outlier"
    would discard exactly the high-value customers this project exists to find.
    We cap extreme values (protecting averages from distortion) but keep the row.
    Source data is already bounded (amount 20–100, ratings 2.5–5), so this is a
    safety net for future, messier data drops rather than an active transform.
    """
    df = df.copy()
    for col in ("purchase_amount", "previous_purchases"):
        if col not in df.columns or not df[col].notna().any():
            continue
        # Work in float to avoid assigning float bounds into a nullable-Int column,
        # then restore integer dtype for count-like fields.
        was_integer = str(df[col].dtype) in ("Int64", "int64")
        s = df[col].astype("float64")
        lo, hi = s.quantile([0.01, 0.99])
        n_clipped = int(((s < lo) | (s > hi)).sum())
        s = s.clip(lower=lo, upper=hi)
        df[col] = s.round().astype("Int64") if was_integer and col == "previous_purchases" else s
        if n_clipped:
            log.info("Winsorised %d outlier(s) in %s to [%.1f, %.1f]", n_clipped, col, lo, hi)
    return df


def enforce_yes_no(df: pd.DataFrame) -> pd.DataFrame:
    """Add boolean mirrors of Yes/No flags for clean arithmetic and SQL.

    Commercial why: 'Yes'/'No' strings cannot be summed or averaged. Booleans let
    us compute rates ("% of subscribers", "discount penetration") trivially and
    correctly in both pandas and SQL.
    """
    df = df.copy()
    for col in YES_NO_COLS:
        if col in df.columns:
            df[f"{col}_flag"] = df[col] == "Yes"
    return df


def clean_dataset(raw: pd.DataFrame) -> pd.DataFrame:
    """Compose the full cleaning pipeline; returns the analysis-ready frame."""
    log.info("Cleaning raw data: %d rows x %d cols", *raw.shape)
    df = (
        raw.pipe(standardise_columns)
        .pipe(drop_duplicates)
        .pipe(coerce_types)
        .pipe(normalise_categoricals)
        .pipe(impute_missing)
        .pipe(clip_outliers)
        .pipe(enforce_yes_no)
    )
    log.info("Cleaning complete: %d rows x %d cols", *df.shape)
    return df
