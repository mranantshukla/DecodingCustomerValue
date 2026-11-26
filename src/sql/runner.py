"""SQL analytics orchestration: load the feature table, build views, export results.

This is the bridge between the Python feature layer and the SQL analytics layer.
It (1) prepares an analytics-clean frame, (2) loads it into ``customer_features``,
(3) applies the schema and every view file in order, and (4) materialises each
analytical view to a CSV in ``reports/sql_exports`` so non-SQL stakeholders (and
Power BI) can consume the results without a live database connection.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import Settings, get_settings
from src.sql.database import DatabaseManager
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# The curated analytics contract (mirrors src/sql/schema/01_schema.sql).
ANALYTICS_COLUMNS = [
    "customer_id",
    "age",
    "gender",
    "item_purchased",
    "category",
    "purchase_amount",
    "location",
    "size",
    "color",
    "season",
    "review_rating",
    "subscription_status",
    "shipping_type",
    "discount_applied",
    "previous_purchases",
    "payment_method",
    "frequency_of_purchases",
    "loyalty_score",
    "loyalty_score_v1",
    "loyalty_score_v2",
    "loyalty_tier",
    "loyalty_confidence_index",
    "repeat_purchase_intensity",
    "brand_affinity_score",
    "promo_dependency_score",
    "non_discount_purchase_ratio",
    "discount_elasticity_proxy",
    "promo_reliance_tier",
    # --- Value decomposition (loyalty-free building blocks first) -------------
    "annual_value",
    "margin_factor",
    "economic_value_proxy",
    "expected_tenure_years",
    "estimated_clv_proxy",
    "revenue_contribution_tier",
    "high_value_probability",
    "premium_customer_flag",
    "satisfaction_flag",
    "category_breadth_est",
    "shipping_urgency_index",
    "payment_repeat_index",
    "seasonal_consistency_score",
    "organic_demand_score",
    "region_quality_index",
    "promo_sensitivity_geo",
    "customer_persona",
    "behaviour_cluster",
]

BOOL_COLUMNS = ["premium_customer_flag", "satisfaction_flag"]

# View -> export filename. These are the analytical deliverables.
VIEW_EXPORTS = {
    "v_executive_kpis": "exec_kpis",
    "v_loyalty_distribution": "loyalty_distribution",
    "v_promo_retention_matrix": "promo_retention_matrix",
    "v_promo_retention_by_persona": "promo_retention_by_persona",
    "v_demographic_opportunity": "demographic_opportunity",
    "v_executive_category": "executive_category",
    "v_persona_scorecard": "persona_scorecard",
    "v_region_scorecard": "region_scorecard",
    "v_organic_demand_regions": "organic_demand_regions",
    "v_high_margin_regions": "high_margin_regions",
    "v_promo_heavy_regions": "promo_heavy_regions",
    "v_category_scorecard": "category_scorecard",
    "v_retention_driving_categories": "retention_driving_categories",
    "v_entry_point_categories": "entry_point_categories",
    "v_high_loyalty_products": "high_loyalty_products",
    "v_revenue_discount_split": "revenue_discount_split",
    "v_revenue_concentration": "revenue_concentration",
    "v_revenue_tier_contribution": "revenue_tier_contribution",
}


def prepare_analytics_frame(feat: pd.DataFrame) -> pd.DataFrame:
    """Select the analytics columns and coerce dtypes for portable SQL storage."""
    df = feat[[c for c in ANALYTICS_COLUMNS if c in feat.columns]].copy()
    for col in BOOL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(int)
    # Nullable Int64 -> plain int for driver compatibility.
    for col in df.select_dtypes(include=["Int64"]).columns:
        df[col] = df[col].astype("int64")
    # pandas "string" dtype -> object so sqlite3 stores TEXT cleanly.
    for col in df.select_dtypes(include=["string"]).columns:
        df[col] = df[col].astype(object)
    return df


def build_database(feat: pd.DataFrame, settings: Settings | None = None) -> DatabaseManager:
    """Load features and build the full analytical view layer. Returns the manager."""
    settings = settings or get_settings()
    db = DatabaseManager(settings.resolved_db_url)

    analytics = prepare_analytics_frame(feat)
    db.write_dataframe(analytics, "customer_features", if_exists="replace")

    sql_root = (
        Path(settings.sql_dir)
        if Path(settings.sql_dir).is_absolute()
        else (Path(__file__).resolve().parents[2] / settings.sql_dir)
    )
    # Apply schema (indexes) then views in lexical order.
    for sql_file in sorted((sql_root / "schema").glob("*.sql")):
        db.execute_sql_file(sql_file)
    for sql_file in sorted((sql_root / "views").glob("*.sql")):
        db.execute_sql_file(sql_file)
    return db


def export_views(db: DatabaseManager, settings: Settings | None = None) -> dict[str, Path]:
    """Materialise each analytical view to CSV under reports/sql_exports."""
    settings = settings or get_settings()
    out_dir = settings.reports_path / "sql_exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for view, name in VIEW_EXPORTS.items():
        try:
            frame = db.read_query(f"SELECT * FROM {view}")
            path = out_dir / f"{name}.csv"
            frame.to_csv(path, index=False)
            written[view] = path
        except Exception as exc:  # keep going; report the failure
            log.error("Failed to export %s: %s", view, exc)
    log.info("Exported %d analytical views to %s", len(written), out_dir)
    return written
