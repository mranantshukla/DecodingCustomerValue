"""build_pbip.py — Generate a complete Power BI Project (.pbip) for the
"Decoding Customer Value" dashboard.

Output: e:/Cagiitg/powerbi/dashboard/  (folder)
  DecodingCustomerValue.pbip                     -> open this in Power BI Desktop
  DecodingCustomerValue.SemanticModel/           -> TMDL semantic model
  DecodingCustomerValue.Report/                  -> PBIR report definition

Translates the existing TMSL model.bim into TMDL and authors the four-panel
Founder Dashboard in PBIR JSON. Files are written UTF-8 *without* BOM with
CRLF line endings, matching what Power BI Desktop emits.

Why a script: the PBIR format is folder-name-sensitive (the inner `name`
property must equal the parent folder name), and PowerShell's default
encodings ship a BOM that PBI Desktop rejects. Python keeps both invariants
trivially.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path("e:/Cagiitg")
SRC_BIM = ROOT / "powerbi" / "model.bim"
CSV_ABS = ROOT / "data" / "processed" / "customer_features.csv"
OUT = ROOT / "powerbi" / "dashboard"

PROJECT = "DecodingCustomerValue"
TABLE = "customer_features"

REPORT_DIR = OUT / f"{PROJECT}.Report"
MODEL_DIR = OUT / f"{PROJECT}.SemanticModel"
DEFS = REPORT_DIR / "definition"
PAGES = DEFS / "pages"
PAGE = PAGES / "Founder"
VISUALS = PAGE / "visuals"

VC_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.7.0/schema.json"
)


def write(path: Path, content: str) -> None:
    """Write text as UTF-8 (no BOM), CRLF line endings — what PBI Desktop emits."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    final = normalized.replace("\n", "\r\n")
    path.write_bytes(final.encode("utf-8"))


def writej(path: Path, obj: dict) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False))


def guid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Semantic model (TMDL)
# ─────────────────────────────────────────────────────────────────────────────

M_TYPE = {
    "int64": "Int64.Type",
    "double": "type number",
    "string": "type text",
    "boolean": "type logical",
    "dateTime": "type datetime",
}


def build_columns_tmdl(columns: list[dict]) -> str:
    out: list[str] = []
    for c in columns:
        out.append(f"\tcolumn {c['name']}")
        out.append(f"\t\tdataType: {c['dataType']}")
        out.append(f"\t\tsummarizeBy: {c.get('summarizeBy', 'none')}")
        out.append(f"\t\tsourceColumn: {c['sourceColumn']}")
        if "formatString" in c:
            # TMDL keeps the format string raw; \$ becomes $ when shown
            fmt = c["formatString"].replace("\\$", "$")
            out.append(f"\t\tformatString: {fmt}")
        if "dataCategory" in c:
            out.append(f"\t\tdataCategory: {c['dataCategory']}")
        out.append(f"\t\tlineageTag: col-{c['name'].replace('_', '-')}")
        out.append("")
    return "\n".join(out)


def build_measures_tmdl(measures: list[dict]) -> str:
    out: list[str] = []
    for m in measures:
        # Use single-line measure form; collapse whitespace so it stays one line
        expr = " ".join(m["expression"].split())
        out.append(f"\tmeasure '{m['name']}' = {expr}")
        if "formatString" in m:
            fmt = m["formatString"].replace("\\$", "$")
            out.append(f"\t\tformatString: {fmt}")
        if "displayFolder" in m:
            out.append(f'\t\tdisplayFolder: "{m["displayFolder"]}"')
        slug = m["name"].lower().replace(" ", "-")
        out.append(f"\t\tlineageTag: meas-{slug}")
        out.append("")
    return "\n".join(out)


def build_partition_tmdl(columns: list[dict], csv_path: Path) -> str:
    win_path = str(csv_path).replace("/", "\\")
    # Each tuple is a separate M body line so the leading-tab prefix is applied
    # uniformly (the previous version embedded "\n" inside one element which
    # left subsequent lines un-prefixed and broke indentation parity).
    type_pairs = [
        f'        {{"{c["sourceColumn"]}", {M_TYPE.get(c["dataType"], "type any")}}}'
        + ("," if i < len(columns) - 1 else "")
        for i, c in enumerate(columns)
    ]
    # Do NOT pin Columns=N — the pipeline emits intermediate columns that
    # widen the CSV beyond the documented schema. Letting Power Query
    # auto-detect column count keeps refresh robust to schema drift.
    m_lines = [
        "let",
        f'    Source = Csv.Document(File.Contents("{win_path}"),'
        f'[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        "    Typed = Table.TransformColumnTypes(PromotedHeaders, {",
        *type_pairs,
        "    })",
        "in",
        "    Typed",
    ]
    indented = "\n".join(f"\t\t\t{ml}" for ml in m_lines)
    return f"\tpartition {TABLE} = m\n" f"\t\tmode: import\n" f"\t\tsource =\n" f"{indented}\n"


def build_table_tmdl(bim: dict, csv_path: Path) -> str:
    table = bim["model"]["tables"][0]
    parts = [
        f"table {table['name']}",
        f"\tlineageTag: tbl-{table['name'].replace('_', '-')}",
        "",
        build_columns_tmdl(table["columns"]),
        build_measures_tmdl(table["measures"]),
        build_partition_tmdl(table["columns"], csv_path),
    ]
    return "\n".join(parts) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Visual generators (PBIR)
# ─────────────────────────────────────────────────────────────────────────────


def col_projection(col: str, *, active: bool = False) -> dict:
    proj = {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": TABLE}},
                "Property": col,
            }
        },
        "queryRef": f"{TABLE}.{col}",
        "nativeQueryRef": col,
    }
    if active:
        proj["active"] = True
    return proj


def meas_projection(measure: str) -> dict:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": TABLE}},
                "Property": measure,
            }
        },
        "queryRef": f"{TABLE}.{measure}",
        "nativeQueryRef": measure,
    }


def visual(
    name: str,
    visual_type: str,
    pos: dict,
    query_state: dict | None = None,
    objects: dict | None = None,
) -> dict:
    v: dict = {
        "$schema": VC_SCHEMA,
        "name": name,
        "position": pos,
        "visual": {
            "visualType": visual_type,
            "drillFilterOtherVisuals": True,
        },
    }
    if query_state is not None:
        v["visual"]["query"] = {"queryState": query_state}
    if objects is not None:
        v["visual"]["objects"] = objects
    return v


def card_visual(name: str, measure: str, pos: dict, label: str) -> dict:
    return visual(
        name,
        "card",
        pos,
        query_state={"Values": {"projections": [meas_projection(measure)]}},
        objects={
            "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
            "labels": [
                {
                    "properties": {
                        "fontSize": {"expr": {"Literal": {"Value": "28D"}}},
                        "color": {
                            "solid": {"color": {"expr": {"Literal": {"Value": "'#16324F'"}}}}
                        },
                    }
                }
            ],
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{label}'"}}},
                        "fontSize": {"expr": {"Literal": {"Value": "11D"}}},
                    }
                }
            ],
        },
    )


def slicer_visual(name: str, column: str, pos: dict, label: str) -> dict:
    return visual(
        name,
        "slicer",
        pos,
        query_state={"Values": {"projections": [col_projection(column, active=True)]}},
        objects={
            "header": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{label}'"}}},
                    }
                }
            ]
        },
    )


def textbox_visual(name: str, runs: list[dict], pos: dict, align: str = "left") -> dict:
    return visual(
        name,
        "textbox",
        pos,
        objects={
            "general": [
                {
                    "properties": {
                        "paragraphs": [{"textRuns": runs, "horizontalTextAlignment": align}]
                    }
                }
            ]
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Build script
# ─────────────────────────────────────────────────────────────────────────────


def clean() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


def write_semantic_model(bim: dict) -> None:
    # .platform
    writej(
        MODEL_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {
                "type": "SemanticModel",
                "displayName": PROJECT,
                "description": "Decoding Customer Value — semantic model",
            },
            "config": {"version": "2.0", "logicalId": guid()},
        },
    )

    # definition.pbism (model marker)
    writej(
        MODEL_DIR / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {},
        },
    )

    # definition/database.tmdl
    write(
        MODEL_DIR / "definition" / "database.tmdl",
        f"database {PROJECT}\n\tcompatibilityLevel: 1567\n",
    )

    # definition/model.tmdl  (model-level config)
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

    # definition/cultures/en-US.tmdl
    write(
        MODEL_DIR / "definition" / "cultures" / "en-US.tmdl",
        "cultureInfo en-US\n",
    )

    # definition/tables/customer_features.tmdl
    write(
        MODEL_DIR / "definition" / "tables" / f"{TABLE}.tmdl",
        build_table_tmdl(bim, CSV_ABS),
    )


def write_report() -> None:
    # .platform
    writej(
        REPORT_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {
                "type": "Report",
                "displayName": PROJECT,
                "description": "Decoding Customer Value — Founder Dashboard",
            },
            "config": {"version": "2.0", "logicalId": guid()},
        },
    )

    # definition.pbir  (points at the sibling SemanticModel)
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

    # definition/version.json
    writej(
        DEFS / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "4.0",
        },
    )

    # definition/report.json  (report-level)
    writej(
        DEFS / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
            "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
            "resourcePackages": [],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "Allow",
                "useNewFilterPaneExperience": True,
                "allowChangeFilterTypes": True,
                "useDefaultAggregations": True,
            },
        },
    )

    # definition/pages/pages.json
    writej(
        PAGES / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": ["Founder"],
            "activePageName": "Founder",
        },
    )

    # definition/pages/Founder/page.json
    writej(
        PAGE / "page.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
            "name": "Founder",
            "displayName": "Founder Dashboard",
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
            "objects": {
                "background": [
                    {
                        "properties": {
                            "color": {
                                "solid": {"color": {"expr": {"Literal": {"Value": "'#F7F9FB'"}}}}
                            },
                            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
                        }
                    }
                ]
            },
        },
    )

    # ── Visuals ──────────────────────────────────────────────────────────────
    # Layout (1280 × 720 canvas):
    #   Title      0..60     y=0
    #   KPI strip  4 cards   y=70, h=110, w=320 each
    #   Slicers    2         y=190, h=42
    #   Panels 2×2           y=244..464 and y=472..692, h=220 each, w=632
    #   Footer               y=695, h=25

    visuals = []

    # Title
    visuals.append(
        textbox_visual(
            "title_main",
            [
                {
                    "value": "Decoding Customer Value",
                    "textStyle": {
                        "fontSize": "26pt",
                        "fontWeight": "bold",
                        "color": "#16324F",
                        "fontFamily": "'Segoe UI Semibold'",
                    },
                },
                {
                    "value": "   —   Founder Dashboard",
                    "textStyle": {
                        "fontSize": "18pt",
                        "color": "#2E86AB",
                        "fontFamily": "'Segoe UI'",
                    },
                },
            ],
            {"x": 24, "y": 12, "z": 0, "height": 56, "width": 1232, "tabOrder": 0},
        )
    )

    # KPI strip — four cards
    kpis = [
        ("kpi_customers", "Total Customers", "Customers"),
        ("kpi_total_clv", "Total Projected CLV", "Projected CLV"),
        ("kpi_top20_share", "Pct CLV from Top 20 Pct", "Top 20% share of CLV"),
        ("kpi_discount_attached", "Pct CLV Discount Attached", "% CLV discount-attached"),
    ]
    for i, (vid, meas, label) in enumerate(kpis):
        visuals.append(
            card_visual(
                vid,
                meas,
                {
                    "x": 24 + i * 308,
                    "y": 78,
                    "z": i + 1,
                    "height": 100,
                    "width": 296,
                    "tabOrder": i + 1,
                },
                label,
            )
        )

    # Slicers
    visuals.append(
        slicer_visual(
            "slicer_persona",
            "customer_persona",
            {"x": 24, "y": 192, "z": 5, "height": 44, "width": 624, "tabOrder": 5},
            "Persona",
        )
    )
    visuals.append(
        slicer_visual(
            "slicer_category",
            "category",
            {"x": 656, "y": 192, "z": 6, "height": 44, "width": 600, "tabOrder": 6},
            "Category",
        )
    )

    # Panel 1 — Pyramid (clusteredBarChart, horizontal bars)
    visuals.append(
        visual(
            "panel1_pyramid",
            "clusteredBarChart",
            {"x": 24, "y": 248, "z": 7, "height": 216, "width": 624, "tabOrder": 7},
            query_state={
                "Category": {
                    "projections": [col_projection("revenue_contribution_tier", active=True)]
                },
                "Y": {"projections": [meas_projection("Total Projected CLV")]},
            },
            objects={
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'1) Customer pyramid — top 20% hold ~60% of value'"
                                    }
                                }
                            },
                            "fontSize": {"expr": {"Literal": {"Value": "13D"}}},
                        }
                    }
                ]
            },
        )
    )

    # Panel 2 — Promo dependency × loyalty scatter, by persona
    visuals.append(
        visual(
            "panel2_scatter",
            "scatterChart",
            {"x": 656, "y": 248, "z": 8, "height": 216, "width": 600, "tabOrder": 8},
            query_state={
                "Category": {"projections": [col_projection("customer_persona", active=True)]},
                "X": {"projections": [meas_projection("Avg Promo Dependency")]},
                "Y": {"projections": [meas_projection("Avg Loyalty Score")]},
                "Size": {"projections": [meas_projection("Total Customers")]},
            },
            objects={
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'2) Promo dependency × retention (by persona)'"
                                    }
                                }
                            },
                            "fontSize": {"expr": {"Literal": {"Value": "13D"}}},
                        }
                    }
                ]
            },
        )
    )

    # Panel 3 — Geographic opportunity map (azureMap)
    visuals.append(
        visual(
            "panel3_map",
            "azureMap",
            {"x": 24, "y": 472, "z": 9, "height": 216, "width": 624, "tabOrder": 9},
            query_state={
                "Category": {"projections": [col_projection("location", active=True)]},
                "Size": {"projections": [meas_projection("Margin Adjusted CLV")]},
            },
            objects={
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'3) Geographic opportunity — margin-adjusted CLV by state'"
                                    }
                                }
                            },
                            "fontSize": {"expr": {"Literal": {"Value": "13D"}}},
                        }
                    }
                ]
            },
        )
    )

    # Panel 4 — Category funnel
    visuals.append(
        visual(
            "panel4_funnel",
            "funnel",
            {"x": 656, "y": 472, "z": 10, "height": 216, "width": 600, "tabOrder": 10},
            query_state={
                "Category": {"projections": [col_projection("category", active=True)]},
                "Y": {"projections": [meas_projection("Total Customers")]},
            },
            objects={
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'4) Category funnel — entry-point vs retention'"
                                    }
                                }
                            },
                            "fontSize": {"expr": {"Literal": {"Value": "13D"}}},
                        }
                    }
                ]
            },
        )
    )

    # Footer caveat
    visuals.append(
        textbox_visual(
            "footer_caveat",
            [
                {
                    "value": "Discount / subscription / gender are structurally entangled in the source — promo metrics are directional, not causal. See LIMITATIONS_AND_ETHICS.md.",
                    "textStyle": {
                        "fontSize": "9pt",
                        "fontStyle": "italic",
                        "color": "#8A99A8",
                        "fontFamily": "'Segoe UI'",
                    },
                }
            ],
            {"x": 24, "y": 698, "z": 11, "height": 16, "width": 1232, "tabOrder": 11},
        )
    )

    for v in visuals:
        writej(VISUALS / v["name"] / "visual.json", v)


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
    write(
        OUT / ".gitignore",
        "**/.pbi/localSettings.json\r\n**/.pbi/cache.abf\r\n",
    )


def main() -> None:
    print(f"Reading model from {SRC_BIM}")
    bim = json.loads(SRC_BIM.read_text(encoding="utf-8"))
    print(f"Cleaning {OUT}")
    clean()
    print("Writing semantic model (TMDL)…")
    write_semantic_model(bim)
    print("Writing PBIR report…")
    write_report()
    print("Writing root .pbip + .gitignore…")
    write_pbip_root()
    print(f"\nDone.  Open in Power BI Desktop:\n  {OUT / (PROJECT + '.pbip')}")


if __name__ == "__main__":
    main()
