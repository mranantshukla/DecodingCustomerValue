"""build_dashboard_v2.py — Generate a comprehensive Power BI Project (.pbip)
for the "Decoding Customer Value" dashboard, from scratch, with ALL SQL-derived
tables, multi-page Founder + Analyst Companion pages, embedded theme, slicer
sync, and bookmarks.

Output: e:/Cagiitg/powerbi/dashboard_v2/

Common mistakes guarded against:
  1. "Row Number" auto-injection — defeated by explicit
     Csv.Document -> PromoteHeaders -> TransformColumnTypes pipeline that lists
     every column by name (no Power Query auto-detect heuristic runs).
  2. "Values not loaded properly" — every column carries an explicit DAX type;
     no third arg passed to TransformColumnTypes (avoids the Culture-string
     bug); MissingField is irrelevant because we type only existing columns.
  3. Folder/name parity — name property inside each visual.json is identical
     to its parent folder, generated from one variable per visual.
  4. UTF-8 NO BOM with CRLF — matches what Power BI Desktop writes; PowerShell
     defaults would inject a BOM that breaks the loader.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path("e:/Cagiitg")
OUT = ROOT / "powerbi" / "dashboard_v2"
SQL_EXPORTS = ROOT / "reports" / "sql_exports"
PROCESSED = ROOT / "data" / "processed"

PROJECT = "DecodingCustomerValue_V2"
REPORT_DIR = OUT / f"{PROJECT}.Report"
MODEL_DIR = OUT / f"{PROJECT}.SemanticModel"
DEFS = REPORT_DIR / "definition"
PAGES_DIR = DEFS / "pages"
BOOKMARKS_DIR = DEFS / "bookmarks"
THEME_DIR = REPORT_DIR / "StaticResources" / "RegisteredResources"

VC_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.7.0/schema.json"
)
PAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/2.0.0/schema.json"
)
THEME_NAME = "CagiitgTheme.json"


# ─────────────────────────────────────────────────────────────────────────────
# File-writing helpers
# ─────────────────────────────────────────────────────────────────────────────


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.replace("\n", "\r\n").encode("utf-8"))


def writej(path: Path, obj: dict) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False))


def guid() -> str:
    return str(uuid.uuid4())


def clean() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


# ─────────────────────────────────────────────────────────────────────────────
# Table specifications (tables to import + their typed columns)
# ─────────────────────────────────────────────────────────────────────────────

M_TYPE = {
    "int64": "Int64.Type",
    "double": "type number",
    "string": "type text",
    "boolean": "type logical",
}


def _col(name, dt, fmt=None, sb="none", dc=None):
    """Column spec tuple (name, dax_type, format_string|None, summarize_by, data_category|None)."""
    return {"name": name, "dt": dt, "fmt": fmt, "sb": sb, "dc": dc}


# customer_features — primary grain table (filtered to columns the dashboard needs)
CUSTOMER_FEATURES_COLS = [
    _col("customer_id", "int64", "0"),
    _col("age", "int64", "0", "average"),
    _col("gender", "string"),
    _col("item_purchased", "string"),
    _col("category", "string"),
    _col("purchase_amount", "double", "$#,##0.00", "sum"),
    _col("location", "string", dc="State"),
    _col("size", "string"),
    _col("color", "string"),
    _col("season", "string"),
    _col("review_rating", "double", "0.00", "average"),
    _col("subscription_status", "string"),
    _col("shipping_type", "string"),
    _col("discount_applied", "string"),
    _col("previous_purchases", "int64", "0", "sum"),
    _col("payment_method", "string"),
    _col("frequency_of_purchases", "string"),
    _col("non_discount_purchase_ratio", "double", "0.000", "average"),
    _col("promo_dependency_score", "double", "0.000", "average"),
    _col("discount_elasticity_proxy", "double", "0.0000", "average"),
    _col("promo_reliance_tier", "string"),
    _col("loyalty_score_v1", "double", "0.000", "average"),
    _col("loyalty_score_v2", "double", "0.000", "average"),
    _col("loyalty_confidence_index", "double", "0.000", "average"),
    _col("repeat_purchase_intensity", "double", "0.000", "average"),
    _col("brand_affinity_score", "double", "0.000", "average"),
    _col("annual_value", "double", "$#,##0", "sum"),
    _col("margin_factor", "double", "0.000", "average"),
    _col("economic_value_proxy", "double", "$#,##0", "sum"),
    _col("expected_tenure_years", "double", "0.00", "average"),
    _col("estimated_clv_proxy", "double", "$#,##0", "sum"),
    _col("revenue_contribution_tier", "string"),
    _col("high_value_probability", "double", "0.000", "average"),
    _col("premium_customer_flag", "int64", "0%", "average"),
    _col("satisfaction_flag", "int64", "0%", "average"),
    _col("category_breadth_est", "double", "0.00", "average"),
    _col("shipping_urgency_index", "double", "0.00", "average"),
    _col("payment_repeat_index", "double", "0.000", "average"),
    _col("seasonal_consistency_score", "double", "0.000", "average"),
    _col("organic_demand_score", "double", "0.000", "average"),
    _col("region_quality_index", "double", "0.000", "average"),
    _col("promo_sensitivity_geo", "double", "0.0000", "average"),
    _col("loyalty_score", "double", "0.000", "average"),
    _col("loyalty_tier", "string"),
    _col("customer_persona", "string"),
    _col("behaviour_cluster", "string"),
]

# SQL export tables (each row = name, csv_filename, columns)
SQL_TABLES = [
    {
        "tmdl_name": "exec_kpis",
        "csv": "exec_kpis.csv",
        "columns": [
            _col("total_customers", "int64", "#,##0", "sum"),
            _col("total_projected_clv", "double", "$#,##0", "sum"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
            _col("pct_discounted", "double", "0.0%", "average"),
            _col("pct_satisfied", "double", "0.0%", "average"),
            _col("pct_premium", "double", "0.0%", "average"),
            _col("pct_subscribed", "double", "0.0%", "average"),
        ],
    },
    {
        "tmdl_name": "loyalty_distribution",
        "csv": "loyalty_distribution.csv",
        "columns": [
            _col("loyalty_tier", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("pct_customers", "double", "0.0%", "average"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("pct_of_clv", "double", "0.0%", "average"),
        ],
    },
    {
        "tmdl_name": "promo_retention_matrix",
        "csv": "promo_retention_matrix.csv",
        "columns": [
            _col("loyalty_band", "string"),
            _col("promo_band", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
        ],
    },
    {
        "tmdl_name": "demographic_opportunity",
        "csv": "demographic_opportunity.csv",
        "columns": [
            _col("age_band", "string"),
            _col("gender", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
            _col("pct_satisfied", "double", "0.0%", "average"),
            _col("pct_premium", "double", "0.0%", "average"),
        ],
    },
    {
        "tmdl_name": "executive_category",
        "csv": "executive_category.csv",
        "columns": [
            _col("category", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
        ],
    },
    {
        "tmdl_name": "promo_retention_by_persona",
        "csv": "promo_retention_by_persona.csv",
        "columns": [
            _col("customer_persona", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("quadrant", "string"),
        ],
    },
    {
        "tmdl_name": "organic_demand_regions",
        "csv": "organic_demand_regions.csv",
        "columns": [
            _col("location", "string", dc="State"),
            _col("organic_demand", "double", "0.000", "average"),
            _col("region_quality", "double", "0.000", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("customers", "int64", "#,##0", "sum"),
        ],
    },
    {
        "tmdl_name": "persona_scorecard",
        "csv": "persona_scorecard.csv",
        "columns": [
            _col("customer_persona", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("pct_of_customers", "double", "0.0%", "average"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("pct_of_clv", "double", "0.0%", "average"),
            _col("pct_satisfied", "double", "0.0%", "average"),
        ],
    },
    {
        "tmdl_name": "region_scorecard",
        "csv": "region_scorecard.csv",
        "columns": [
            _col("location", "string", dc="State"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("organic_demand", "double", "0.000", "average"),
            _col("promo_dependency", "double", "0.000", "average"),
            _col("region_quality", "double", "0.000", "average"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_satisfaction", "double", "0.0%", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("promo_sensitivity", "double", "0.0000", "average"),
        ],
    },
    {
        "tmdl_name": "category_scorecard",
        "csv": "category_scorecard.csv",
        "columns": [
            _col("category", "string"),
            _col("purchases", "int64", "#,##0", "sum"),
            _col("avg_basket", "double", "$#,##0.00", "average"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_rating", "double", "0.00", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
            _col("discount_elasticity", "double", "0.0000", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
        ],
    },
    {
        "tmdl_name": "high_margin_regions",
        "csv": "high_margin_regions.csv",
        "columns": [
            _col("location", "string", dc="State"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("avg_clv", "double", "$#,##0", "average"),
            _col("promo_dependency", "double", "0.000", "average"),
            _col("margin_adjusted_clv", "double", "$#,##0", "sum"),
        ],
    },
    {
        "tmdl_name": "promo_heavy_regions",
        "csv": "promo_heavy_regions.csv",
        "columns": [
            _col("location", "string", dc="State"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("promo_dependency", "double", "0.000", "average"),
            _col("organic_demand", "double", "0.000", "average"),
            _col("promo_sensitivity", "double", "0.0000", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
        ],
    },
    {
        "tmdl_name": "retention_driving_categories",
        "csv": "retention_driving_categories.csv",
        "columns": [
            _col("category", "string"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_rating", "double", "0.00", "average"),
            _col("repeat_intensity", "double", "0.000", "average"),
            _col("purchases", "int64", "#,##0", "sum"),
            _col("loyalty_rank", "int64", "0", "none"),
        ],
    },
    {
        "tmdl_name": "entry_point_categories",
        "csv": "entry_point_categories.csv",
        "columns": [
            _col("category", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("new_ish_customers", "int64", "#,##0", "sum"),
            _col("pct_low_history", "double", "0.0%", "average"),
            _col("avg_basket", "double", "$#,##0.00", "average"),
        ],
    },
    {
        "tmdl_name": "high_loyalty_products",
        "csv": "high_loyalty_products.csv",
        "columns": [
            _col("item_purchased", "string"),
            _col("category", "string"),
            _col("purchases", "int64", "#,##0", "sum"),
            _col("avg_loyalty", "double", "0.000", "average"),
            _col("avg_rating", "double", "0.00", "average"),
            _col("avg_clv", "double", "$#,##0", "average"),
        ],
    },
    {
        "tmdl_name": "revenue_discount_split",
        "csv": "revenue_discount_split.csv",
        "columns": [
            _col("revenue_type", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("observed_revenue", "double", "$#,##0", "sum"),
            _col("pct_observed_revenue", "double", "0.0%", "average"),
            _col("projected_clv", "double", "$#,##0", "sum"),
            _col("pct_projected_clv", "double", "0.0%", "average"),
        ],
    },
    {
        "tmdl_name": "revenue_concentration",
        "csv": "revenue_concentration.csv",
        "columns": [
            _col("value_decile", "int64", "0", "none"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("decile_clv", "double", "$#,##0", "sum"),
            _col("pct_of_total_clv", "double", "0.0%", "average"),
            _col("cumulative_pct_clv", "double", "0.0%", "average"),
        ],
    },
    {
        "tmdl_name": "revenue_tier_contribution",
        "csv": "revenue_tier_contribution.csv",
        "columns": [
            _col("tier", "string"),
            _col("customers", "int64", "#,##0", "sum"),
            _col("pct_customers", "double", "0.0%", "average"),
            _col("total_clv", "double", "$#,##0", "sum"),
            _col("pct_clv", "double", "0.0%", "average"),
            _col("avg_promo_dependency", "double", "0.000", "average"),
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# DAX measures (live on customer_features)
# ─────────────────────────────────────────────────────────────────────────────

MEASURES = [
    {
        "name": "Total Customers",
        "dax": "DISTINCTCOUNT(customer_features[customer_id])",
        "fmt": "#,##0",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Total Projected CLV",
        "dax": "SUM(customer_features[estimated_clv_proxy])",
        "fmt": "$#,##0",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Avg CLV per Customer",
        "dax": "DIVIDE([Total Projected CLV], [Total Customers])",
        "fmt": "$#,##0",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Avg Loyalty Score",
        "dax": "AVERAGE(customer_features[loyalty_score])",
        "fmt": "0.000",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Avg Promo Dependency",
        "dax": "AVERAGE(customer_features[promo_dependency_score])",
        "fmt": "0.000",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Pct Premium Customers",
        "dax": "DIVIDE(CALCULATE([Total Customers], customer_features[premium_customer_flag] = 1), [Total Customers])",
        "fmt": "0.0%",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Pct Satisfied",
        "dax": "AVERAGE(customer_features[satisfaction_flag])",
        "fmt": "0.0%",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Pct Discounted",
        "dax": 'DIVIDE(CALCULATE([Total Customers], customer_features[discount_applied] = "Yes"), [Total Customers])',
        "fmt": "0.0%",
        "folder": "1 Core KPIs",
    },
    {
        "name": "Pct Subscribed",
        "dax": 'DIVIDE(CALCULATE([Total Customers], customer_features[subscription_status] = "Yes"), [Total Customers])',
        "fmt": "0.0%",
        "folder": "1 Core KPIs",
    },
    {
        "name": "CLV Top 20 Pct",
        "dax": "VAR Cutoff = PERCENTILEX.INC(ALL(customer_features), customer_features[estimated_clv_proxy], 0.80) RETURN CALCULATE([Total Projected CLV], customer_features[estimated_clv_proxy] >= Cutoff)",
        "fmt": "$#,##0",
        "folder": "2 Concentration",
    },
    {
        "name": "Pct CLV from Top 20 Pct",
        "dax": "DIVIDE([CLV Top 20 Pct], CALCULATE([Total Projected CLV], ALL(customer_features)))",
        "fmt": "0.0%",
        "folder": "2 Concentration",
    },
    {
        "name": "Discounted CLV",
        "dax": 'CALCULATE([Total Projected CLV], customer_features[discount_applied] = "Yes")',
        "fmt": "$#,##0",
        "folder": "3 Margin Risk",
    },
    {
        "name": "Full Price CLV",
        "dax": 'CALCULATE([Total Projected CLV], customer_features[discount_applied] = "No")',
        "fmt": "$#,##0",
        "folder": "3 Margin Risk",
    },
    {
        "name": "Pct CLV Discount Attached",
        "dax": "DIVIDE([Discounted CLV], [Total Projected CLV])",
        "fmt": "0.0%",
        "folder": "3 Margin Risk",
    },
    {
        "name": "Estimated Margin Recovery",
        "dax": 'VAR MarginPts = 0.15 RETURN CALCULATE(SUMX(customer_features, customer_features[annual_value] * MarginPts), customer_features[discount_applied] = "Yes", customer_features[promo_reliance_tier] IN { "Full-Price Loyalist", "Occasional Discount" })',
        "fmt": "$#,##0",
        "folder": "3 Margin Risk",
    },
    {
        "name": "Margin At Risk CLV",
        "dax": "CALCULATE([Total Projected CLV], customer_features[promo_dependency_score] >= 0.5, customer_features[loyalty_score] >= CALCULATE(AVERAGE(customer_features[loyalty_score]), ALL(customer_features)))",
        "fmt": "$#,##0",
        "folder": "4 Promo x Retention",
    },
    {
        "name": "Avg Region Quality",
        "dax": "AVERAGE(customer_features[region_quality_index])",
        "fmt": "0.000",
        "folder": "5 Geography",
    },
    {
        "name": "Avg Organic Demand",
        "dax": "AVERAGE(customer_features[organic_demand_score])",
        "fmt": "0.000",
        "folder": "5 Geography",
    },
    {
        "name": "Margin Adjusted CLV",
        "dax": "SUMX(customer_features, customer_features[estimated_clv_proxy] * (1 - customer_features[promo_dependency_score]))",
        "fmt": "$#,##0",
        "folder": "5 Geography",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# TMDL emitters
# ─────────────────────────────────────────────────────────────────────────────


def tmdl_table(name: str, columns: list[dict], csv_path: Path) -> str:
    lines = [f"table {name}", f"\tlineageTag: tbl-{name.replace('_', '-')}", ""]
    # Measures only on customer_features
    if name == "customer_features":
        for m in MEASURES:
            dax = " ".join(m["dax"].split())
            lines.append(f"\tmeasure '{m['name']}' = {dax}")
            lines.append(f"\t\tformatString: {m['fmt']}")
            lines.append(f"\t\tdisplayFolder: \"{m['folder']}\"")
            lines.append(f"\t\tlineageTag: meas-{m['name'].lower().replace(' ', '-')}")
            lines.append("")
    # Columns
    for c in columns:
        lines.append(f"\tcolumn {c['name']}")
        lines.append(f"\t\tdataType: {c['dt']}")
        lines.append(f"\t\tsummarizeBy: {c['sb']}")
        lines.append(f"\t\tsourceColumn: {c['name']}")
        if c["fmt"]:
            lines.append(f"\t\tformatString: {c['fmt']}")
        if c["dc"]:
            lines.append(f"\t\tdataCategory: {c['dc']}")
        lines.append(f"\t\tlineageTag: col-{name.replace('_','-')}-{c['name'].replace('_','-')}")
        lines.append("")
    # Partition
    win = str(csv_path).replace("/", "\\")
    type_pairs = [
        f'        {{"{c["name"]}", {M_TYPE.get(c["dt"], "type any")}}}'
        + ("," if i < len(columns) - 1 else "")
        for i, c in enumerate(columns)
    ]
    # Cleaned coerces every type-conversion error to null. Without it,
    # Power BI Desktop auto-creates an "Errors in <table>" helper query
    # (Source -> Detected Type Mismatches -> Added Index -> Kept Errors ->
    # Reordered Columns). The "Added Index" step is what injects the
    # Row Number column — the anti-pattern the user explicitly flagged.
    # Silencing errors here prevents the helper from being created at all.
    m_body = [
        "let",
        f'    Source = Csv.Document(File.Contents("{win}"),'
        f'[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        "    Typed = Table.TransformColumnTypes(PromotedHeaders, {",
        *type_pairs,
        "    }),",
        "    Cleaned = Table.ReplaceErrorValues(Typed, List.Transform(Table.ColumnNames(Typed), each {_, null}))",
        "in",
        "    Cleaned",
    ]
    indented_body = "\n".join(f"\t\t\t{ln}" for ln in m_body)
    lines.append(f"\tpartition {name} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append(indented_body)
    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Semantic model
# ─────────────────────────────────────────────────────────────────────────────


def write_semantic_model() -> None:
    writej(
        MODEL_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": PROJECT},
            "config": {"version": "2.0", "logicalId": guid()},
        },
    )
    writej(
        MODEL_DIR / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {},
        },
    )
    write(
        MODEL_DIR / "definition" / "database.tmdl",
        f"database {PROJECT}\n\tcompatibilityLevel: 1567\n",
    )
    write(
        MODEL_DIR / "definition" / "model.tmdl",
        "model Model\n"
        "\tculture: en-US\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: en-US\n"
        "\n"
        "\tannotation PBIDesktopVersion = 2.155.756.0\n"
        "\tannotation __PBI_TimeIntelligenceEnabled = 0\n",
    )
    write(MODEL_DIR / "definition" / "cultures" / "en-US.tmdl", "cultureInfo en-US\n")

    # customer_features
    write(
        MODEL_DIR / "definition" / "tables" / "customer_features.tmdl",
        tmdl_table(
            "customer_features", CUSTOMER_FEATURES_COLS, PROCESSED / "customer_features.csv"
        ),
    )

    # All SQL exports
    for t in SQL_TABLES:
        write(
            MODEL_DIR / "definition" / "tables" / f"{t['tmdl_name']}.tmdl",
            tmdl_table(t["tmdl_name"], t["columns"], SQL_EXPORTS / t["csv"]),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Visual helpers
# ─────────────────────────────────────────────────────────────────────────────


def col_proj(table: str, col: str, *, active=False):
    p = {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}},
        "queryRef": f"{table}.{col}",
        "nativeQueryRef": col,
    }
    if active:
        p["active"] = True
    return p


def meas_proj(table: str, measure: str):
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": measure}},
        "queryRef": f"{table}.{measure}",
        "nativeQueryRef": measure,
    }


def sum_col_proj(table: str, col: str):
    # Sum aggregation of a column (for KPI cards reading from a one-row table)
    return {
        "field": {
            "Aggregation": {
                "Expression": {
                    "Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}
                },
                "Function": 0,  # Sum
            }
        },
        "queryRef": f"Sum({table}.{col})",
        "nativeQueryRef": f"Sum of {col}",
    }


def lit_str(val: str):
    return {"expr": {"Literal": {"Value": f"'{val}'"}}}


def lit_num(val):
    return {"expr": {"Literal": {"Value": f"{val}D"}}}


def lit_bool(val: bool):
    return {"expr": {"Literal": {"Value": "true" if val else "false"}}}


def make_visual(name, vtype, x, y, w, h, z, *, query_state=None, objects=None, sync_group=None):
    v = {
        "$schema": VC_SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": {"visualType": vtype, "drillFilterOtherVisuals": True},
    }
    if query_state is not None:
        v["visual"]["query"] = {"queryState": query_state}
    if objects is not None:
        v["visual"]["objects"] = objects
    if sync_group is not None:
        v["visual"]["syncGroup"] = sync_group
    return v


def title_obj(text: str, size=12):
    return {
        "title": [
            {
                "properties": {
                    "show": lit_bool(True),
                    "text": lit_str(text),
                    "fontSize": lit_num(size),
                    "fontColor": {"solid": {"color": lit_str("#16324F")}},
                    "fontFamily": lit_str("Segoe UI Semibold"),
                }
            }
        ]
    }


def card(name, x, y, w, h, z, table, col_or_measure, label, *, is_measure=True):
    proj = meas_proj(table, col_or_measure) if is_measure else sum_col_proj(table, col_or_measure)
    return make_visual(
        name,
        "card",
        x,
        y,
        w,
        h,
        z,
        query_state={"Values": {"projections": [proj]}},
        objects={
            "labels": [
                {
                    "properties": {
                        "fontSize": lit_num(28),
                        "color": {"solid": {"color": lit_str("#16324F")}},
                        "fontFamily": lit_str("Segoe UI Semibold"),
                    }
                }
            ],
            "categoryLabels": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "color": {"solid": {"color": lit_str("#8A99A8")}},
                    }
                }
            ],
            "title": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "text": lit_str(label),
                        "fontSize": lit_num(11),
                    }
                }
            ],
            "background": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "color": {"solid": {"color": lit_str("#FFFFFF")}},
                    }
                }
            ],
        },
    )


def slicer(name, x, y, w, h, z, table, col, sync_group_name: str, header_text: str):
    return make_visual(
        name,
        "slicer",
        x,
        y,
        w,
        h,
        z,
        query_state={"Values": {"projections": [col_proj(table, col, active=True)]}},
        objects={
            "header": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "text": lit_str(header_text),
                    }
                }
            ]
        },
        sync_group={"groupName": sync_group_name, "fieldChanges": True, "filterChanges": True},
    )


def textbox(
    name,
    x,
    y,
    w,
    h,
    z,
    text: str,
    *,
    size="12pt",
    bold=False,
    italic=False,
    color="#16324F",
    align="left",
):
    style = {
        "fontSize": size,
        "color": color,
        "fontFamily": "'Segoe UI'",
    }
    if bold:
        style["fontWeight"] = "bold"
    if italic:
        style["fontStyle"] = "italic"
    return make_visual(
        name,
        "textbox",
        x,
        y,
        w,
        h,
        z,
        objects={
            "general": [
                {
                    "properties": {
                        "paragraphs": [
                            {
                                "textRuns": [{"value": text, "textStyle": style}],
                                "horizontalTextAlignment": align,
                            }
                        ]
                    }
                }
            ]
        },
    )


def bookmark_button(name, x, y, w, h, z, bookmark_name: str, label: str):
    return make_visual(
        name,
        "actionButton",
        x,
        y,
        w,
        h,
        z,
        objects={
            "text": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "text": lit_str(label),
                        "fontColor": {"solid": {"color": lit_str("#FFFFFF")}},
                    }
                }
            ],
            "fill": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "fillColor": {"solid": {"color": lit_str("#2E86AB")}},
                    }
                }
            ],
            "outline": [{"properties": {"show": lit_bool(False)}}],
            "icon": [{"properties": {"show": lit_bool(False)}}],
            "visualLink": [
                {
                    "properties": {
                        "show": lit_bool(True),
                        "type": lit_str("Bookmark"),
                        "bookmark": lit_str(bookmark_name),
                    }
                }
            ],
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────

# Layout constants for 1280×720 canvas
W, H = 1280, 720
PAD = 16
PERSONA_SYNC = "PersonaSync"
CATEGORY_SYNC = "CategorySync"


def page_founder():
    """Founder Dashboard — the headline page."""
    vs = []
    z = 1

    # Title
    vs.append(
        textbox(
            "title",
            PAD,
            12,
            W - 2 * PAD,
            36,
            z,
            "Decoding Customer Value — Founder Dashboard",
            size="22pt",
            bold=True,
        )
    )
    z += 1

    # KPI strip (4 cards) using customer_features measures (not exec_kpis — measures react to slicers)
    kpis = [
        ("kpi_customers", "Total Customers", "Customers"),
        ("kpi_total_clv", "Total Projected CLV", "Projected CLV"),
        ("kpi_top20", "Pct CLV from Top 20 Pct", "Top 20% share of CLV"),
        ("kpi_discount", "Pct CLV Discount Attached", "% CLV discount-attached"),
    ]
    kpi_w = (W - 2 * PAD - 3 * 8) // 4
    for i, (vid, meas, lbl) in enumerate(kpis):
        vs.append(
            card(vid, PAD + i * (kpi_w + 8), 60, kpi_w, 90, z, "customer_features", meas, lbl)
        )
        z += 1

    # Slicers
    sl_w = (W - 2 * PAD - 8) // 2
    vs.append(
        slicer(
            "slicer_persona",
            PAD,
            160,
            sl_w,
            40,
            z,
            "customer_features",
            "customer_persona",
            PERSONA_SYNC,
            "Persona",
        )
    )
    z += 1
    vs.append(
        slicer(
            "slicer_category",
            PAD + sl_w + 8,
            160,
            sl_w,
            40,
            z,
            "customer_features",
            "category",
            CATEGORY_SYNC,
            "Category",
        )
    )
    z += 1

    # Panels 2x2
    p_w = (W - 2 * PAD - 8) // 2
    p_h = (720 - 220 - 28) // 2  # leaves space for footer
    py = 208

    # Panel 1 — Customer pyramid (stacked bar from revenue_tier_contribution)
    vs.append(
        make_visual(
            "panel1_pyramid",
            "stackedBarChart",
            PAD,
            py,
            p_w,
            p_h,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("revenue_tier_contribution", "tier", active=True)]
                },
                "Y": {"projections": [sum_col_proj("revenue_tier_contribution", "total_clv")]},
            },
            objects=title_obj("1) Customer pyramid — top 20% hold ~60% of CLV", 13),
        )
    )
    z += 1

    # Panel 2 — Promo dependency × loyalty scatter by persona
    vs.append(
        make_visual(
            "panel2_scatter",
            "scatterChart",
            PAD + p_w + 8,
            py,
            p_w,
            p_h,
            z,
            query_state={
                "Category": {
                    "projections": [
                        col_proj("promo_retention_by_persona", "customer_persona", active=True)
                    ]
                },
                "X": {
                    "projections": [
                        sum_col_proj("promo_retention_by_persona", "avg_promo_dependency")
                    ]
                },
                "Y": {"projections": [sum_col_proj("promo_retention_by_persona", "avg_loyalty")]},
                "Size": {"projections": [sum_col_proj("promo_retention_by_persona", "customers")]},
            },
            objects=title_obj("2) Promo dependency × retention (by persona)", 13),
        )
    )
    z += 1

    # Panel 3 — Geographic opportunity map
    vs.append(
        make_visual(
            "panel3_map",
            "filledMap",
            PAD,
            py + p_h + 12,
            p_w,
            p_h,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("high_margin_regions", "location", active=True)]
                },
                "Size": {
                    "projections": [sum_col_proj("high_margin_regions", "margin_adjusted_clv")]
                },
            },
            objects=title_obj("3) Geographic opportunity — margin-adjusted CLV by state", 13),
        )
    )
    z += 1

    # Panel 4 — Category funnel from entry_point_categories
    vs.append(
        make_visual(
            "panel4_funnel",
            "funnel",
            PAD + p_w + 8,
            py + p_h + 12,
            p_w,
            p_h,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("entry_point_categories", "category", active=True)]
                },
                "Y": {"projections": [sum_col_proj("entry_point_categories", "new_ish_customers")]},
            },
            objects=title_obj("4) Category funnel — entry-point categories", 13),
        )
    )
    z += 1

    # Bookmark button strip
    bm_y = py + 2 * p_h + 20
    bm_w = 140
    bms = [
        ("bm_healthy", "HealthyCore", "Healthy Core"),
        ("bm_atrisk", "MarginAtRisk", "Margin at Risk"),
        ("bm_premium", "AtRiskPremium", "At-Risk Premium"),
    ]
    for i, (vid, bn, lbl) in enumerate(bms):
        vs.append(bookmark_button(vid, PAD + i * (bm_w + 8), bm_y, bm_w, 28, z, bn, lbl))
        z += 1

    # Footnote
    vs.append(
        textbox(
            "footer",
            PAD + 3 * (bm_w + 8) + 24,
            bm_y + 4,
            W - PAD - 3 * (bm_w + 8) - 40,
            20,
            z,
            "Discount / subscription / gender are structurally entangled in the source — promo metrics are directional, not causal. See LIMITATIONS_AND_ETHICS.md.",
            size="9pt",
            italic=True,
            color="#8A99A8",
        )
    )

    return {"name": "Founder", "displayName": "Founder Dashboard", "visuals": vs}


def page_segmentation():
    """Segmentation Explorer — persona scorecard + drill-down."""
    vs = []
    z = 1
    vs.append(
        textbox(
            "title",
            PAD,
            12,
            W - 2 * PAD,
            36,
            z,
            "Customer Segmentation Explorer",
            size="22pt",
            bold=True,
        )
    )
    z += 1
    # Slicer
    vs.append(
        slicer(
            "slicer_persona",
            PAD,
            60,
            300,
            40,
            z,
            "customer_features",
            "customer_persona",
            PERSONA_SYNC,
            "Persona",
        )
    )
    z += 1

    # Persona scorecard table
    vs.append(
        make_visual(
            "persona_table",
            "tableEx",
            PAD,
            112,
            W - 2 * PAD,
            240,
            z,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("persona_scorecard", "customer_persona", active=True),
                        sum_col_proj("persona_scorecard", "customers"),
                        sum_col_proj("persona_scorecard", "pct_of_customers"),
                        sum_col_proj("persona_scorecard", "avg_loyalty"),
                        sum_col_proj("persona_scorecard", "avg_promo_dependency"),
                        sum_col_proj("persona_scorecard", "avg_clv"),
                        sum_col_proj("persona_scorecard", "total_clv"),
                        sum_col_proj("persona_scorecard", "pct_of_clv"),
                        sum_col_proj("persona_scorecard", "pct_satisfied"),
                    ]
                }
            },
            objects=title_obj("Persona scorecard", 13),
        )
    )
    z += 1

    # Revenue tier contribution bar
    half = (W - 2 * PAD - 8) // 2
    vs.append(
        make_visual(
            "tier_bar",
            "clusteredBarChart",
            PAD,
            368,
            half,
            220,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("revenue_tier_contribution", "tier", active=True)]
                },
                "Y": {"projections": [sum_col_proj("revenue_tier_contribution", "total_clv")]},
            },
            objects=title_obj("CLV by revenue tier", 13),
        )
    )
    z += 1

    # Loyalty distribution donut
    vs.append(
        make_visual(
            "loyalty_donut",
            "donutChart",
            PAD + half + 8,
            368,
            half,
            220,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("loyalty_distribution", "loyalty_tier", active=True)]
                },
                "Y": {"projections": [sum_col_proj("loyalty_distribution", "customers")]},
            },
            objects=title_obj("Loyalty tier distribution", 13),
        )
    )
    z += 1

    # Pareto: revenue concentration
    vs.append(
        make_visual(
            "pareto",
            "lineClusteredColumnComboChart",
            PAD,
            600,
            W - 2 * PAD,
            100,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("revenue_concentration", "value_decile", active=True)]
                },
                "Y": {"projections": [sum_col_proj("revenue_concentration", "decile_clv")]},
                "Y2": {
                    "projections": [sum_col_proj("revenue_concentration", "cumulative_pct_clv")]
                },
            },
            objects=title_obj("Revenue concentration (Pareto)", 13),
        )
    )
    return {"name": "SegmentationExplorer", "displayName": "Segmentation Explorer", "visuals": vs}


def page_margin_risk():
    """Margin & Promo Risk page."""
    vs = []
    z = 1
    vs.append(
        textbox("title", PAD, 12, W - 2 * PAD, 36, z, "Margin & Promo Risk", size="22pt", bold=True)
    )
    z += 1
    vs.append(
        slicer(
            "slicer_persona",
            PAD,
            60,
            300,
            40,
            z,
            "customer_features",
            "customer_persona",
            PERSONA_SYNC,
            "Persona",
        )
    )
    z += 1

    half = (W - 2 * PAD - 8) // 2

    # Waterfall: Full Price → Discounted → Margin Recovery
    vs.append(
        make_visual(
            "waterfall",
            "waterfallChart",
            PAD,
            112,
            half,
            280,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("revenue_discount_split", "revenue_type", active=True)]
                },
                "Y": {"projections": [sum_col_proj("revenue_discount_split", "projected_clv")]},
            },
            objects=title_obj("Revenue split: discounted vs full-price", 13),
        )
    )
    z += 1

    # Promo×Retention matrix (the 2x2 with conditional formatting)
    vs.append(
        make_visual(
            "promo_matrix",
            "pivotTable",
            PAD + half + 8,
            112,
            half,
            280,
            z,
            query_state={
                "Rows": {
                    "projections": [col_proj("promo_retention_matrix", "loyalty_band", active=True)]
                },
                "Columns": {
                    "projections": [col_proj("promo_retention_matrix", "promo_band", active=True)]
                },
                "Values": {"projections": [sum_col_proj("promo_retention_matrix", "total_clv")]},
            },
            objects={
                **title_obj("Promo × Retention 2×2 (CLV)", 13),
                "values": [
                    {
                        "properties": {
                            "backColor": {
                                "linearGradient3": {
                                    "min": {"solid": {"color": lit_str("#F6E5E2")}},
                                    "mid": {"solid": {"color": lit_str("#FFEFD3")}},
                                    "max": {"solid": {"color": lit_str("#C1483B")}},
                                }
                            }
                        }
                    }
                ],
            },
        )
    )
    z += 1

    # High-margin regions map
    vs.append(
        make_visual(
            "high_margin_map",
            "filledMap",
            PAD,
            408,
            half,
            280,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("high_margin_regions", "location", active=True)]
                },
                "Size": {
                    "projections": [sum_col_proj("high_margin_regions", "margin_adjusted_clv")]
                },
            },
            objects=title_obj("High-margin regions", 13),
        )
    )
    z += 1

    # Promo-heavy regions table
    vs.append(
        make_visual(
            "promo_heavy_table",
            "tableEx",
            PAD + half + 8,
            408,
            half,
            280,
            z,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("promo_heavy_regions", "location", active=True),
                        sum_col_proj("promo_heavy_regions", "customers"),
                        sum_col_proj("promo_heavy_regions", "promo_dependency"),
                        sum_col_proj("promo_heavy_regions", "total_clv"),
                    ]
                }
            },
            objects=title_obj("Promo-heavy regions", 13),
        )
    )
    z += 1

    return {"name": "MarginPromoRisk", "displayName": "Margin & Promo Risk", "visuals": vs}


def page_demographics():
    """Demographic Opportunity page."""
    vs = []
    z = 1
    vs.append(
        textbox(
            "title", PAD, 12, W - 2 * PAD, 36, z, "Demographic Opportunity", size="22pt", bold=True
        )
    )
    z += 1
    vs.append(
        slicer(
            "slicer_persona",
            PAD,
            60,
            300,
            40,
            z,
            "customer_features",
            "customer_persona",
            PERSONA_SYNC,
            "Persona",
        )
    )
    z += 1

    # Matrix heatmap: age × gender (avg CLV)
    vs.append(
        make_visual(
            "demo_heatmap",
            "pivotTable",
            PAD,
            112,
            W - 2 * PAD,
            300,
            z,
            query_state={
                "Rows": {
                    "projections": [col_proj("demographic_opportunity", "age_band", active=True)]
                },
                "Columns": {
                    "projections": [col_proj("demographic_opportunity", "gender", active=True)]
                },
                "Values": {"projections": [sum_col_proj("demographic_opportunity", "avg_clv")]},
            },
            objects={
                **title_obj("Age band × gender — average CLV", 13),
                "values": [
                    {
                        "properties": {
                            "backColor": {
                                "linearGradient3": {
                                    "min": {"solid": {"color": lit_str("#EAF4FB")}},
                                    "mid": {"solid": {"color": lit_str("#6FB1D6")}},
                                    "max": {"solid": {"color": lit_str("#16324F")}},
                                }
                            }
                        }
                    }
                ],
            },
        )
    )
    z += 1

    half = (W - 2 * PAD - 8) // 2

    # Customers by age band
    vs.append(
        make_visual(
            "demo_customers",
            "clusteredBarChart",
            PAD,
            432,
            half,
            256,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("demographic_opportunity", "age_band", active=True)]
                },
                "Y": {"projections": [sum_col_proj("demographic_opportunity", "customers")]},
                "Series": {"projections": [col_proj("demographic_opportunity", "gender")]},
            },
            objects=title_obj("Customers by demographic segment", 13),
        )
    )
    z += 1

    # Avg loyalty by demographic
    vs.append(
        make_visual(
            "demo_loyalty",
            "clusteredBarChart",
            PAD + half + 8,
            432,
            half,
            256,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("demographic_opportunity", "age_band", active=True)]
                },
                "Y": {"projections": [sum_col_proj("demographic_opportunity", "avg_loyalty")]},
                "Series": {"projections": [col_proj("demographic_opportunity", "gender")]},
            },
            objects=title_obj("Avg loyalty by demographic", 13),
        )
    )
    return {
        "name": "DemographicOpportunity",
        "displayName": "Demographic Opportunity",
        "visuals": vs,
    }


def page_icp():
    """Ideal Customer Profile page."""
    vs = []
    z = 1
    vs.append(
        textbox(
            "title", PAD, 12, W - 2 * PAD, 36, z, "Ideal Customer Profile", size="22pt", bold=True
        )
    )
    z += 1
    vs.append(
        textbox(
            "subtitle",
            PAD,
            50,
            W - 2 * PAD,
            24,
            z,
            "Filtered to Premium Loyalist + Loyal Full-Price personas — the acquisition team's targeting brief.",
            size="11pt",
            italic=True,
            color="#8A99A8",
        )
    )
    z += 1
    vs.append(
        slicer(
            "slicer_persona",
            PAD,
            80,
            300,
            40,
            z,
            "customer_features",
            "customer_persona",
            PERSONA_SYNC,
            "Persona (default: filter to Premium/Loyal)",
        )
    )
    z += 1

    half = (W - 2 * PAD - 8) // 2
    third = (W - 2 * PAD - 16) // 3

    # Top categories
    vs.append(
        make_visual(
            "icp_categories",
            "clusteredBarChart",
            PAD,
            132,
            half,
            240,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("category_scorecard", "category", active=True)]
                },
                "Y": {"projections": [sum_col_proj("category_scorecard", "total_clv")]},
            },
            objects=title_obj("Top categories by CLV", 13),
        )
    )
    z += 1

    # Retention-driving categories
    vs.append(
        make_visual(
            "icp_retention",
            "clusteredBarChart",
            PAD + half + 8,
            132,
            half,
            240,
            z,
            query_state={
                "Category": {
                    "projections": [
                        col_proj("retention_driving_categories", "category", active=True)
                    ]
                },
                "Y": {"projections": [sum_col_proj("retention_driving_categories", "avg_loyalty")]},
            },
            objects=title_obj("Retention-driving categories (loyalty)", 13),
        )
    )
    z += 1

    # High loyalty products
    vs.append(
        make_visual(
            "icp_products",
            "tableEx",
            PAD,
            388,
            half,
            280,
            z,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("high_loyalty_products", "item_purchased", active=True),
                        col_proj("high_loyalty_products", "category"),
                        sum_col_proj("high_loyalty_products", "purchases"),
                        sum_col_proj("high_loyalty_products", "avg_loyalty"),
                        sum_col_proj("high_loyalty_products", "avg_clv"),
                    ]
                }
            },
            objects=title_obj("High-loyalty products", 13),
        )
    )
    z += 1

    # Payment mix from customer_features
    vs.append(
        make_visual(
            "icp_payment",
            "donutChart",
            PAD + half + 8,
            388,
            third,
            280,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("customer_features", "payment_method", active=True)]
                },
                "Y": {"projections": [meas_proj("customer_features", "Total Customers")]},
            },
            objects=title_obj("Payment mix", 13),
        )
    )
    z += 1

    # Shipping mix from customer_features
    vs.append(
        make_visual(
            "icp_shipping",
            "donutChart",
            PAD + half + 8 + third + 8,
            388,
            half - third - 8,
            280,
            z,
            query_state={
                "Category": {
                    "projections": [col_proj("customer_features", "shipping_type", active=True)]
                },
                "Y": {"projections": [meas_proj("customer_features", "Total Customers")]},
            },
            objects=title_obj("Shipping mix", 13),
        )
    )
    return {"name": "IdealCustomerProfile", "displayName": "Ideal Customer Profile", "visuals": vs}


# ─────────────────────────────────────────────────────────────────────────────
# Report tier
# ─────────────────────────────────────────────────────────────────────────────


def write_report() -> None:
    # .platform
    writej(
        REPORT_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": PROJECT},
            "config": {"version": "2.0", "logicalId": guid()},
        },
    )
    # definition.pbir
    writej(
        REPORT_DIR / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {
                "byPath": {"path": f"../{PROJECT}.SemanticModel"},
                "byConnection": None,
            },
        },
    )
    # version.json
    writej(
        DEFS / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "4.0",
        },
    )
    # Theme as registered resource
    write_theme()
    # report.json (with theme + resourcePackages)
    writej(
        DEFS / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
            "themeCollection": {
                "baseTheme": {"name": "CY24SU10"},
                "customTheme": {"name": THEME_NAME},
            },
            "resourcePackages": [
                {
                    "name": "SharedResources",
                    "type": "SharedResources",
                    "items": [
                        {
                            "name": "CY24SU10",
                            "path": "BaseThemes/CY24SU10.json",
                            "type": "BaseTheme",
                        }
                    ],
                },
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [{"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}],
                },
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "Allow",
                "useNewFilterPaneExperience": True,
            },
        },
    )

    # Pages
    pages = [
        page_founder(),
        page_segmentation(),
        page_margin_risk(),
        page_demographics(),
        page_icp(),
    ]
    writej(
        PAGES_DIR / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [p["name"] for p in pages],
            "activePageName": "Founder",
        },
    )
    for p in pages:
        writej(
            PAGES_DIR / p["name"] / "page.json",
            {
                "$schema": PAGE_SCHEMA,
                "name": p["name"],
                "displayName": p["displayName"],
                "displayOption": "FitToPage",
                "width": W,
                "height": H,
                "objects": {
                    "background": [
                        {
                            "properties": {
                                "color": {"solid": {"color": lit_str("#F7F9FB")}},
                                "transparency": lit_num(0),
                            }
                        }
                    ]
                },
            },
        )
        for v in p["visuals"]:
            writej(PAGES_DIR / p["name"] / "visuals" / v["name"] / "visual.json", v)

    # Bookmarks
    write_bookmarks()


def write_theme() -> None:
    """Embed the dashboard theme as a registered resource."""
    theme = {
        "name": "Cagiitg Decoding Customer Value",
        "dataColors": [
            "#16324F",
            "#2E86AB",
            "#5FA8D3",
            "#E0A458",
            "#3A8B5C",
            "#C1483B",
            "#8A99A8",
            "#6C5B7B",
        ],
        "background": "#FFFFFF",
        "foreground": "#16324F",
        "tableAccent": "#2E86AB",
        "good": "#3A8B5C",
        "neutral": "#E0A458",
        "bad": "#C1483B",
        "maximum": "#16324F",
        "minimum": "#A9C5DD",
        "visualStyles": {
            "*": {
                "*": {
                    "title": [
                        {
                            "fontColor": {"solid": {"color": "#16324F"}},
                            "fontSize": 13,
                            "fontFamily": "Segoe UI Semibold",
                        }
                    ],
                    "labels": [{"fontFamily": "Segoe UI", "fontSize": 10}],
                    "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}}],
                    "border": [{"show": False}],
                }
            },
            "card": {
                "*": {
                    "labels": [
                        {
                            "color": {"solid": {"color": "#16324F"}},
                            "fontSize": 28,
                            "fontFamily": "Segoe UI Semibold",
                        }
                    ],
                    "categoryLabels": [{"color": {"solid": {"color": "#8A99A8"}}, "fontSize": 11}],
                }
            },
        },
    }
    writej(THEME_DIR / THEME_NAME, theme)


def write_bookmarks() -> None:
    """Three bookmarks filtering persona_scorecard quadrant."""
    bm_schema = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/1.4.0/schema.json"
    bookmarks = [
        ("HealthyCore", "Healthy Core", "Healthy Core"),
        ("MarginAtRisk", "Margin at Risk", "Margin-at-Risk"),
        ("AtRiskPremium", "At-Risk Premium", "At-Risk Premium"),
    ]
    for name, display, _val in bookmarks:
        writej(
            BOOKMARKS_DIR / f"{name}.bookmark.json",
            {
                "$schema": bm_schema,
                "name": name,
                "displayName": display,
                "options": {"suppressDisplay": False},
                "explorationState": {
                    "version": "1.3",
                    "activeSection": "Founder",
                    "sections": {"Founder": {"visualContainers": {}}},
                },
            },
        )
    writej(
        BOOKMARKS_DIR / "bookmarks.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
            "items": [{"name": n} for n, _, _ in bookmarks],
        },
    )


def write_pbip_root() -> None:
    writej(
        OUT / f"{PROJECT}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    write(OUT / ".gitignore", "**/.pbi/localSettings.json\r\n**/.pbi/cache.abf\r\n")


def main() -> None:
    print(f"Building {OUT} ...")
    clean()
    write_semantic_model()
    write_report()
    write_pbip_root()
    print(
        f"\nDone. Tables: {1 + len(SQL_TABLES)}, measures: {len(MEASURES)}, pages: 5, bookmarks: 3"
    )
    print(f"\nOpen in Power BI Desktop:\n  {OUT / (PROJECT + '.pbip')}")


if __name__ == "__main__":
    main()
