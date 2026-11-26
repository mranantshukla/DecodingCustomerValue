"""SQL Viewer — run the project's analytical views/queries live and export them.

Demonstrates the SQL analytics layer transparently: pick a view, see the exact
SQL behind it, run it against the database, and download the result.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.settings import get_settings
from src.dashboard.data_access import load_view
from src.sql.database import DatabaseManager

st.set_page_config(page_title="SQL Viewer", page_icon="🗄️", layout="wide")
st.title("🗄️ SQL Analytics Viewer")
st.caption("The analytical views that power every chart — inspect the SQL and the results.")

VIEW_CATALOG = {
    "Executive KPIs": ("v_executive_kpis", "exec_kpis"),
    "Loyalty distribution": ("v_loyalty_distribution", "loyalty_distribution"),
    "Promo × retention matrix": ("v_promo_retention_matrix", "promo_retention_matrix"),
    "Persona scorecard": ("v_persona_scorecard", "persona_scorecard"),
    "Region scorecard": ("v_region_scorecard", "region_scorecard"),
    "Organic-demand regions": ("v_organic_demand_regions", "organic_demand_regions"),
    "High-margin regions": ("v_high_margin_regions", "high_margin_regions"),
    "Promo-heavy regions": ("v_promo_heavy_regions", "promo_heavy_regions"),
    "Category scorecard": ("v_category_scorecard", "category_scorecard"),
    "Retention-driving categories": (
        "v_retention_driving_categories",
        "retention_driving_categories",
    ),
    "Entry-point categories": ("v_entry_point_categories", "entry_point_categories"),
    "Revenue: discount split": ("v_revenue_discount_split", "revenue_discount_split"),
    "Revenue concentration (deciles)": ("v_revenue_concentration", "revenue_concentration"),
}

choice = st.selectbox("Choose an analytical view", list(VIEW_CATALOG))
view_name, export_name = VIEW_CATALOG[choice]

# Show the SQL definition (read from the view files for authenticity).
sql_root = Path(get_settings().sql_dir)
if not sql_root.is_absolute():
    sql_root = Path(__file__).resolve().parents[3] / sql_root
sql_text = ""
for f in sorted((sql_root / "views").glob("*.sql")):
    body = f.read_text(encoding="utf-8")
    if f"CREATE VIEW {view_name}" in body:
        # Extract just this view's statement.
        idx = body.find(f"CREATE VIEW {view_name}")
        end = body.find(";", idx)
        sql_text = body[idx : end + 1]
        break

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown("**View definition**")
    st.code(sql_text or "-- definition not found", language="sql")
with col2:
    st.markdown("**Run it live**")
    if st.button("▶ Execute against database"):
        try:
            db = DatabaseManager(get_settings().resolved_db_url)
            result = db.read_query(f"SELECT * FROM {view_name}")
        except Exception as exc:  # fall back to the cached export
            st.info(f"Live DB unavailable ({exc}); showing exported snapshot.")
            result = load_view(export_name)
    else:
        result = load_view(export_name)

st.divider()
st.dataframe(result, use_container_width=True)
if not result.empty:
    st.download_button(
        "⬇ Download result (CSV)", result.to_csv(index=False), f"{export_name}.csv", "text/csv"
    )
