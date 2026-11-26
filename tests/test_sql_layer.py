"""Tests for the SQL analytics layer (runs against an in-memory/temp SQLite DB)."""

from __future__ import annotations

import pytest

from src.business_logic.loyalty_framework import (
    attach_canonical_loyalty,
    evaluate_loyalty_definitions,
)
from src.business_logic.segmentation import segment_customers
from src.sql.database import split_sql_statements
from src.sql.runner import build_database, export_views, prepare_analytics_frame


@pytest.fixture(scope="module")
def db(feature_df, tmp_path_factory):
    """Build a real database in a temp dir from the full feature set.

    A FRESH Settings instance is used (not the cached singleton) so the temp DB
    and report paths never leak into other tests.
    """
    from config.settings import Settings

    tmp = tmp_path_factory.mktemp("dcv_sql")
    settings = Settings(db_url=f"sqlite:///{tmp / 'test.db'}", reports_dir=tmp)

    result = evaluate_loyalty_definitions(feature_df)
    df = segment_customers(attach_canonical_loyalty(feature_df, result.winner))
    manager = build_database(df, settings)
    yield manager, settings


def test_split_sql_statements_strips_comments():
    sql = "-- a comment\nSELECT 1;\nSELECT 2; -- trailing\n"
    stmts = split_sql_statements(sql)
    assert stmts == ["SELECT 1", "SELECT 2"]


def test_analytics_frame_has_no_bool_dtype(feature_df):
    df = segment_customers(
        attach_canonical_loyalty(feature_df, evaluate_loyalty_definitions(feature_df).winner)
    )
    prepared = prepare_analytics_frame(df)
    assert prepared["premium_customer_flag"].dtype.kind in ("i", "u")
    assert prepared["satisfaction_flag"].dtype.kind in ("i", "u")


def test_executive_kpis_view(db):
    manager, _ = db
    out = manager.read_query("SELECT * FROM v_executive_kpis")
    assert len(out) == 1
    assert out.loc[0, "total_customers"] == 3900
    assert 0 <= out.loc[0, "avg_loyalty"] <= 1


def test_revenue_concentration_is_monotonic(db):
    manager, _ = db
    out = manager.read_query("SELECT * FROM v_revenue_concentration ORDER BY value_decile")
    # Cumulative % must be non-decreasing and end at ~100.
    cum = out["cumulative_pct_clv"].tolist()
    assert cum == sorted(cum)
    assert abs(cum[-1] - 100.0) < 0.5


def test_persona_scorecard_covers_all_customers(db):
    manager, _ = db
    out = manager.read_query("SELECT SUM(customers) AS n FROM v_persona_scorecard")
    assert out.loc[0, "n"] == 3900


def test_all_views_exportable(db):
    manager, settings = db
    written = export_views(manager, settings)
    assert len(written) >= 15  # all defined views materialised
