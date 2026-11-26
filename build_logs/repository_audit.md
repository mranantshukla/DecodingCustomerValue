# Repository Audit — Power BI Dashboard v2 Build

**Generated:** by `scripts/build_dashboard_v2.py` (build session, 2026-06-10)
**Output:** `powerbi/dashboard_v2/DecodingCustomerValue_V2.pbip`

---

## Discovered inputs

### Primary data file
| File | Rows | Columns |
|---|---:|---:|
| `data/processed/customer_features.csv` | 3,900 | 56 |

### SQL-derived exports (18 tables)
All sourced from `reports/sql_exports/` — each is a pre-aggregated SQL view exported as CSV by `python -m src.pipeline`.

| Filename | Rows | Cols | Purpose |
|---|---:|---:|---|
| `exec_kpis.csv` | 1 | 9 | Single-row executive KPI snapshot |
| `loyalty_distribution.csv` | 5 | 5 | Loyalty tier × customer share |
| `promo_retention_matrix.csv` | 4 | 5 | 2×2 (loyalty × promo) banding |
| `demographic_opportunity.csv` | 12 | 9 | Age band × gender opportunity matrix |
| `executive_category.csv` | 4 | 5 | Category-level executive view |
| `promo_retention_by_persona.csv` | 6 | 7 | Persona-grouped promo × retention |
| `organic_demand_regions.csv` | 21 | 5 | High-organic-demand state list |
| `persona_scorecard.csv` | 6 | 9 | Persona-level KPI scorecard |
| `region_scorecard.csv` | 50 | 10 | Full state-level scorecard |
| `category_scorecard.csv` | 4 | 8 | Category-level KPI scorecard |
| `high_margin_regions.csv` | 50 | 5 | Margin-adjusted CLV per state |
| `promo_heavy_regions.csv` | 17 | 6 | High-promo-dependency states |
| `retention_driving_categories.csv` | 4 | 6 | Categories ranked by retention |
| `entry_point_categories.csv` | 4 | 5 | Entry-point category funnel |
| `high_loyalty_products.csv` | 25 | 6 | SKU-level high-loyalty products |
| `revenue_discount_split.csv` | 2 | 6 | Discounted vs full-price revenue |
| `revenue_concentration.csv` | 10 | 5 | Decile-level Pareto data |
| `revenue_tier_contribution.csv` | 4 | 6 | Revenue tier (VIP/High/Mid/Low) |

### Other discovered files
- `powerbi/measures.dax` — 19 DAX measures (reused verbatim)
- `powerbi/theme.json` — original theme (embedded as `CagiitgTheme.json` in v2)
- `powerbi/model.bim` — TMSL semantic model (v1, retained for reference)
- `powerbi/dashboard/DecodingCustomerValue.pbip` — v1 PBIP (retained)

---

## Build assumptions

1. **Power BI Desktop is installed locally** — confirmed at
   `C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_2.155.756.0_x64__8wekyb3d8bbwe\bin\PBIDesktop.exe`.
2. **PBIR (Power BI Project Enhanced Report Format) is the target output** — the user opens the `.pbip` in PBI Desktop and saves as `.pbix`. The pre-2024 PBIR-Legacy single-file `report.json` is *not* used.
3. **CSV paths are absolute Windows paths** in the M expressions (`E:\Cagiitg\...`). Refresh on a different machine requires updating these or making the project portable via an M parameter.
4. **No relationships are defined between tables** — every CSV is independent; visuals bind to one table each. Persona/Category slicers act only on `customer_features` because that's the grain table where measures live.

---

## Missing / questionable

- *None identified.* The earlier audit flagged `assets/powerbi_executive.png` as a stale README link; that was cleaned up in the prior turn.

---

## Anti-patterns explicitly guarded against (per user request)

1. **Row Number / Index columns auto-injected** — guarded by writing the M expression by hand with the exact pipeline `Csv.Document → Table.PromoteHeaders → Table.TransformColumnTypes` (no `Table.AddIndexColumn`, no auto-detect-types step).
2. **Values not loaded properly** — every column has an explicit DAX type in the TMDL; `Table.TransformColumnTypes` is called WITHOUT a third argument (the previous Culture-string bug came from passing `MissingField.Ignore` as the third arg, which Power Query tried to coerce into a culture string).
3. **Folder name ≠ inner `name` property** — both are generated from a single variable per visual / page / bookmark in the script, eliminating any drift.
4. **UTF-8 BOM** — files are written with `Path.write_bytes(content.encode("utf-8"))` (no BOM) with CRLF line endings, matching what Power BI Desktop emits on Save As.

---

## Outputs produced

```
powerbi/dashboard_v2/
├── DecodingCustomerValue_V2.pbip                 ← open this in PBI Desktop
├── .gitignore
├── DecodingCustomerValue_V2.SemanticModel/
│   ├── .platform                                 (Fabric Git metadata)
│   ├── definition.pbism                          (semantic-model marker)
│   └── definition/
│       ├── database.tmdl                         (compatibility-level 1567)
│       ├── model.tmdl                            (culture, annotations)
│       ├── cultures/en-US.tmdl
│       └── tables/                               (19 tables)
│           ├── customer_features.tmdl            (3,900 rows, 46 cols + 19 measures)
│           ├── exec_kpis.tmdl
│           ├── … 17 more SQL-export tables …
└── DecodingCustomerValue_V2.Report/
    ├── .platform
    ├── definition.pbir                            (PBIR version 4.0)
    ├── StaticResources/RegisteredResources/
    │   └── CagiitgTheme.json                     (embedded theme)
    └── definition/
        ├── report.json                            (theme + resourcePackages)
        ├── version.json
        ├── pages/
        │   ├── pages.json                         (5-page order)
        │   ├── Founder/                           (4 panels + KPIs + slicers + bookmarks)
        │   ├── SegmentationExplorer/
        │   ├── MarginPromoRisk/
        │   ├── DemographicOpportunity/
        │   └── IdealCustomerProfile/
        └── bookmarks/
            ├── bookmarks.json
            ├── HealthyCore.bookmark.json
            ├── MarginAtRisk.bookmark.json
            └── AtRiskPremium.bookmark.json
```
