"""build_dashboard_v2_legacy.py — Build a PBIP in *PBIR-Legacy* format with
the 4 KPI cards + 4 founder panels pre-authored into the report.json
visualContainers array.

Why PBIR-Legacy: PBI Desktop Microsoft Store edition ships with
`PBI_enhancedReportFormat` DISABLED. With that flag off, the new per-visual
PBIR JSON layout crashes with `Cannot read properties of undefined (reading
'visualContainers')`. PBIR-Legacy is the single-file `report.json` format
which works regardless of preview flags.

Layout (1280×720 canvas):
    KPI strip:  4 cards in a row, y=20  h=80
    Panel grid: 2×2,  y=120 h=270  +  y=410 h=270

Output: e:/Cagiitg/powerbi/dashboard_v2_legacy/
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path("e:/Cagiitg")

# Re-use v2's TMDL emitter
spec = importlib.util.spec_from_file_location("bv2", ROOT / "scripts" / "build_dashboard_v2.py")
assert spec and spec.loader
bv2 = importlib.util.module_from_spec(spec)
sys.modules["bv2"] = bv2

ALT_OUT = ROOT / "powerbi" / "dashboard_v2_legacy"
ALT_PROJECT = "DecodingCustomerValue_V2_Legacy"

bv2.OUT = ALT_OUT
bv2.PROJECT = ALT_PROJECT
bv2.REPORT_DIR = ALT_OUT / f"{ALT_PROJECT}.Report"
bv2.MODEL_DIR = ALT_OUT / f"{ALT_PROJECT}.SemanticModel"

spec.loader.exec_module(bv2)


# ─────────────────────────────────────────────────────────────────────────────
# PBIR-Legacy visualContainer authoring helpers
# ─────────────────────────────────────────────────────────────────────────────


def _src(short: str) -> dict:
    return {"SourceRef": {"Source": short}}


def col_select(table: str, column: str, alias: str | None = None) -> dict:
    short = table[0]
    return {
        "Column": {"Expression": _src(short), "Property": column},
        "Name": alias or f"{table}.{column}",
    }


def sum_select(table: str, column: str, alias: str | None = None) -> dict:
    short = table[0]
    return {
        "Aggregation": {
            "Expression": {"Column": {"Expression": _src(short), "Property": column}},
            "Function": 0,
        },
        "Name": alias or f"Sum({table}.{column})",
    }


def measure_select(table: str, measure: str) -> dict:
    short = table[0]
    return {
        "Measure": {"Expression": _src(short), "Property": measure},
        "Name": f"{table}.{measure}",
    }


def build_visual_container(
    *,
    x: float,
    y: float,
    z: float,
    width: float,
    height: float,
    visual_type: str,
    table: str,
    projections: dict[str, list[dict]],
    prototype_selects: list[dict],
    title_text: str | None = None,
    is_measure_only: bool = False,
) -> dict:
    """Author one PBIR-Legacy visualContainer.

    `projections` maps role name (Category / Y / X / Size / Values) to a list
    of {"queryRef": "<name>", "active"?: bool} entries.
    `prototype_selects` is the underlying Select-list for prototypeQuery —
    each entry produced by col_select / sum_select / measure_select.
    """
    name = "v" + uuid.uuid4().hex[:18]
    short = table[0]

    prototype_query = {
        "Version": 2,
        "From": [{"Name": short, "Entity": table, "Type": 0}],
        "Select": prototype_selects,
        "OrderBy": [],
    }

    single_visual: dict = {
        "visualType": visual_type,
        "projections": projections,
        "prototypeQuery": prototype_query,
        "drillFilterOtherVisuals": True,
    }
    if title_text:
        single_visual["vcObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}},
                        "fontColor": {
                            "solid": {"color": {"expr": {"Literal": {"Value": "'#16324F'"}}}}
                        },
                        "fontFamily": {"expr": {"Literal": {"Value": "'Segoe UI Semibold'"}}},
                        "fontSize": {"expr": {"Literal": {"Value": "12D"}}},
                    }
                }
            ]
        }

    config = {
        "name": name,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": float(x),
                    "y": float(y),
                    "z": float(z),
                    "width": float(width),
                    "height": float(height),
                    "tabOrder": int(z),
                },
            }
        ],
        "singleVisual": single_visual,
    }

    # PBIR-Legacy stores config / query / dataTransforms as JSON STRINGS
    # nested inside the visualContainer JSON object.
    container: dict = {
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "width": float(width),
        "height": float(height),
        "config": json.dumps(config, separators=(",", ":")),
        "filters": "[]",
    }

    # query — derived form Desktop expects alongside config
    query = {
        "Commands": [
            {
                "SemanticQueryDataShapeCommand": {
                    "Query": prototype_query,
                    "Binding": {
                        "Primary": {
                            "Groupings": [{"Projections": list(range(len(prototype_selects)))}]
                        },
                        "DataReduction": {
                            "DataVolume": 4,
                            "Primary": {"Window": {"Count": 1000}},
                        },
                        "Version": 1,
                    },
                }
            }
        ]
    }
    container["query"] = json.dumps(query, separators=(",", ":"))

    # dataTransforms — let Desktop compute on first render by writing an empty
    # but well-formed object. Including a minimum projectionOrdering tells
    # Desktop which role each Select position maps to.
    role_ordering: dict[str, list[int]] = {}
    idx = 0
    for role, _projs in projections.items():
        role_ordering[role] = []
    # Best-effort mapping of selects -> roles by position
    for role, projs in projections.items():
        for _ in projs:
            role_ordering[role].append(idx)
            idx += 1
    data_transforms = {
        "objects": {},
        "projectionOrdering": role_ordering,
        "queryMetadata": {
            "Filters": [],
            "Select": [
                {
                    "Restatement": p["Name"].split(".")[-1],
                    "Type": 1 if "Aggregation" in p or "Measure" in p else 2,
                    "Name": p["Name"],
                }
                for p in prototype_selects
            ],
        },
        "visualElements": [{"DataRoles": [{"Name": r, "Projection": 0} for r in projections]}],
    }
    container["dataTransforms"] = json.dumps(data_transforms, separators=(",", ":"))

    return container


# ─────────────────────────────────────────────────────────────────────────────
# Visual specs
# ─────────────────────────────────────────────────────────────────────────────


def kpi_card(*, x: float, y: float, w: float, h: float, z: int, measure: str, label: str) -> dict:
    return build_visual_container(
        x=x,
        y=y,
        z=z,
        width=w,
        height=h,
        visual_type="card",
        table="customer_features",
        projections={"Values": [{"queryRef": f"customer_features.{measure}"}]},
        prototype_selects=[measure_select("customer_features", measure)],
        title_text=label,
    )


def panel_pyramid(x: float, y: float, w: float, h: float, z: int) -> dict:
    return build_visual_container(
        x=x,
        y=y,
        z=z,
        width=w,
        height=h,
        visual_type="barChart",
        table="revenue_tier_contribution",
        projections={
            "Category": [{"queryRef": "revenue_tier_contribution.tier", "active": True}],
            "Y": [{"queryRef": "Sum(revenue_tier_contribution.total_clv)"}],
        },
        prototype_selects=[
            col_select("revenue_tier_contribution", "tier"),
            sum_select("revenue_tier_contribution", "total_clv"),
        ],
        title_text="1) Customer pyramid — CLV by revenue tier",
    )


def panel_scatter(x: float, y: float, w: float, h: float, z: int) -> dict:
    return build_visual_container(
        x=x,
        y=y,
        z=z,
        width=w,
        height=h,
        visual_type="scatterChart",
        table="promo_retention_by_persona",
        projections={
            "Category": [
                {"queryRef": "promo_retention_by_persona.customer_persona", "active": True}
            ],
            "X": [{"queryRef": "Sum(promo_retention_by_persona.avg_promo_dependency)"}],
            "Y": [{"queryRef": "Sum(promo_retention_by_persona.avg_loyalty)"}],
            "Size": [{"queryRef": "Sum(promo_retention_by_persona.customers)"}],
        },
        prototype_selects=[
            col_select("promo_retention_by_persona", "customer_persona"),
            sum_select("promo_retention_by_persona", "avg_promo_dependency"),
            sum_select("promo_retention_by_persona", "avg_loyalty"),
            sum_select("promo_retention_by_persona", "customers"),
        ],
        title_text="2) Promo dependency × loyalty (by persona)",
    )


def panel_map(x: float, y: float, w: float, h: float, z: int) -> dict:
    return build_visual_container(
        x=x,
        y=y,
        z=z,
        width=w,
        height=h,
        visual_type="filledMap",
        table="high_margin_regions",
        projections={
            "Category": [{"queryRef": "high_margin_regions.location", "active": True}],
            "Size": [{"queryRef": "Sum(high_margin_regions.margin_adjusted_clv)"}],
        },
        prototype_selects=[
            col_select("high_margin_regions", "location"),
            sum_select("high_margin_regions", "margin_adjusted_clv"),
        ],
        title_text="3) Geographic opportunity — margin-adjusted CLV by state",
    )


def panel_funnel(x: float, y: float, w: float, h: float, z: int) -> dict:
    return build_visual_container(
        x=x,
        y=y,
        z=z,
        width=w,
        height=h,
        visual_type="funnel",
        table="entry_point_categories",
        projections={
            "Category": [{"queryRef": "entry_point_categories.category", "active": True}],
            "Y": [{"queryRef": "Sum(entry_point_categories.new_ish_customers)"}],
        },
        prototype_selects=[
            col_select("entry_point_categories", "category"),
            sum_select("entry_point_categories", "new_ish_customers"),
        ],
        title_text="4) Category funnel — entry-point categories",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    bv2.OUT = ALT_OUT
    bv2.PROJECT = ALT_PROJECT
    bv2.REPORT_DIR = ALT_OUT / f"{ALT_PROJECT}.Report"
    bv2.MODEL_DIR = ALT_OUT / f"{ALT_PROJECT}.SemanticModel"

    print(f"Building PBIR-Legacy PBIP with embedded visuals at {ALT_OUT}")
    if ALT_OUT.exists():
        shutil.rmtree(ALT_OUT)
    ALT_OUT.mkdir(parents=True)

    # 1) Semantic model (TMDL — same as v2)
    bv2.write_semantic_model()

    # 2) Legacy Report tier
    bv2.writej(
        bv2.REPORT_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": ALT_PROJECT},
            "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
        },
    )
    bv2.writej(
        bv2.REPORT_DIR / "definition.pbir",
        {
            "version": "1.0",
            "datasetReference": {
                "byPath": {"path": f"../{ALT_PROJECT}.SemanticModel"},
                "byConnection": None,
            },
        },
    )

    # Build visualContainers
    visuals: list[dict] = []

    # KPI strip — 4 cards
    kpi_y, kpi_h = 20, 80
    kpi_w = 300
    kpi_gap = 16
    kpis = [
        ("Total Customers", "Customers"),
        ("Total Projected CLV", "Projected CLV"),
        ("Pct CLV from Top 20 Pct", "Top 20% share of CLV"),
        ("Pct CLV Discount Attached", "% CLV discount-attached"),
    ]
    for i, (measure, label) in enumerate(kpis):
        visuals.append(
            kpi_card(
                x=20 + i * (kpi_w + kpi_gap),
                y=kpi_y,
                w=kpi_w,
                h=kpi_h,
                z=i + 1,
                measure=measure,
                label=label,
            )
        )

    # Panels 2×2
    p_top_y = 120
    p_bot_y = 410
    p_w_left = 620
    p_w_right = 600
    p_h = 270
    p_x_right = 660

    visuals.append(panel_pyramid(20, p_top_y, p_w_left, p_h, 5))
    visuals.append(panel_scatter(p_x_right, p_top_y, p_w_right, p_h, 6))
    visuals.append(panel_map(20, p_bot_y, p_w_left, p_h, 7))
    visuals.append(panel_funnel(p_x_right, p_bot_y, p_w_right, p_h, 8))

    # report.json — PBIR-Legacy
    page_id = uuid.uuid4().hex[:20]
    legacy_report = {
        "config": json.dumps(
            {
                "version": "5.43",
                "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
                "activeSectionIndex": 0,
                "defaultDrillFilterOtherVisuals": True,
            },
            separators=(",", ":"),
        ),
        "layoutOptimization": 0,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "name": "SharedResources",
                    "type": 2,
                    "items": [
                        {
                            "name": "CY24SU10",
                            "path": "BaseThemes/CY24SU10.json",
                            "type": 202,
                        }
                    ],
                    "disabled": False,
                }
            }
        ],
        "sections": [
            {
                "name": page_id,
                "displayName": "Founder Dashboard",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": visuals,
                "config": json.dumps(
                    {"layouts": [{"id": 0, "position": {}}]}, separators=(",", ":")
                ),
                "displayOption": 1,
                "height": 720,
                "width": 1280,
            }
        ],
    }
    bv2.writej(bv2.REPORT_DIR / "report.json", legacy_report)

    # PBIP root
    bv2.writej(
        ALT_OUT / f"{ALT_PROJECT}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{ALT_PROJECT}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    bv2.write(ALT_OUT / ".gitignore", "**/.pbi/localSettings.json\r\n**/.pbi/cache.abf\r\n")

    print(f"\nDone. 19 tables, 19 measures, {len(visuals)} visuals on Founder Dashboard page.")
    print("\nOpen in Power BI Desktop:")
    print(f"  {ALT_OUT / (ALT_PROJECT + '.pbip')}")


if __name__ == "__main__":
    main()
