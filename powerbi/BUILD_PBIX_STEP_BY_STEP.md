# Build the `.pbix` from this repo — step-by-step

A `.pbix` is a proprietary Microsoft format only **Power BI Desktop** can author.
This guide documents three paths to a working `DecodingCustomerValue.pbix`,
fastest first:

- **Path 0 (one click, ~60 seconds):** open the pre-authored PBIP project at
  [`dashboard/DecodingCustomerValue.pbip`](dashboard/DecodingCustomerValue.pbip)
  in Power BI Desktop. The semantic model (46 columns, 19 DAX measures, all
  format strings) AND the four-panel Founder Dashboard load automatically.
  *File → Save As → `.pbix`* writes the binary.
- **Path A (fast, ~3 min):** import the pre-built semantic model
  (`model.bim`) via Tabular Editor — useful if you already have an empty
  `.pbix` you want to bolt the model onto. All 19 DAX measures pre-baked,
  then drop in the visuals manually.
- **Path B (no extra tools, ~10 min):** Get Data → CSV → manually paste the
  measures from `measures.dax`. Plain Power BI Desktop only.

The visual layout is identical in all paths — see
[`DASHBOARD_GUIDE.md`](DASHBOARD_GUIDE.md) for the four panels, and
[`../assets/founder_dashboard_mockup.png`](../assets/founder_dashboard_mockup.png)
as the visual reference.

---

## Prerequisites
- **Power BI Desktop** (free, Windows-only, 2.155+). Install from
  https://powerbi.microsoft.com/desktop or the Microsoft Store.
- Pipeline outputs generated: run `python -m src.pipeline` once in the repo
  root. This creates `data/processed/customer_features.csv` and the CSV view
  exports under `reports/sql_exports/`.
- **For Path 0 — REQUIRED:** in Power BI Desktop, *File → Options and
  settings → Options → GLOBAL → Preview features*, tick **both**:
    - ☑ Power BI Project (.pbip) save option
    - ☑ Store reports using enhanced metadata format (PBIR)

  Click OK, then **fully close and reopen Power BI Desktop** before opening
  the `.pbip`. If you skip this step the project still opens but the entire
  Report tier (all pages and visuals) is silently dropped because PBIR is
  still flagged as preview in the Microsoft Store edition — you'll see the
  semantic model in the Data pane but a blank canvas with no page tab at
  the bottom. Re-running `python scripts/build_pbip.py` restores the
  visuals; flip these switches first so Desktop loads them on open.

---

## Path 0 — One click (recommended, ~60 seconds)

Power BI Desktop 2.155 reads PBIP projects natively. The repo ships a
fully-authored project under `powerbi/dashboard/`:

```
powerbi/dashboard/
├── DecodingCustomerValue.pbip                  <- double-click this
├── DecodingCustomerValue.Report/                  PBIR — Founder page, 12 visuals
│   ├── definition.pbir
│   └── definition/
│       ├── report.json
│       └── pages/Founder/
│           ├── page.json
│           └── visuals/                            title + 4 KPIs + 2 slicers +
│               ├── title_main/visual.json          4 panels + footer caveat
│               ├── kpi_*/visual.json
│               ├── slicer_*/visual.json
│               ├── panel{1..4}_*/visual.json
│               └── footer_caveat/visual.json
└── DecodingCustomerValue.SemanticModel/            TMDL — 1 table, 46 cols,
    ├── definition.pbism                            19 measures, M source
    └── definition/
        ├── database.tmdl  · model.tmdl  · cultures/en-US.tmdl
        └── tables/customer_features.tmdl
```

Steps:

1. **Open the `.pbip`** by double-clicking `DecodingCustomerValue.pbip` (or
   from Power BI Desktop: *File → Open report → Browse* → select the `.pbip`).
2. Wait ~30 seconds while Desktop loads the semantic model and refreshes the
   CSV. The title bar will show `DecodingCustomerValue`.
3. Apply the theme: *View → Themes → Browse for themes* →
   `powerbi/theme.json`. The navy/accent palette applies. (The PBIP doesn't
   embed the theme by design — applying it manually keeps the file small and
   gives you the option to swap themes without re-authoring.)
4. *File → Save As* → `assets/DecodingCustomerValue.pbix`. Done.

### Re-generating the PBIP

If you change the model or want to rebuild the project from scratch:

```bash
python scripts/build_pbip.py
```

The script reads `powerbi/model.bim` and `data/processed/customer_features.csv`
and regenerates the entire `powerbi/dashboard/` folder. Safe to run any time.

---

---

## Path A — Fast (3 minutes, requires Tabular Editor)

Tabular Editor is the standard third-party tool for editing Power BI semantic
models. The free version 2 is sufficient. Install from
https://tabulareditor.com/.

### A.1 Open a new Power BI Desktop session
1. Launch **Power BI Desktop**.
2. *File → Get data → Text/CSV* → browse to
   `data\processed\customer_features.csv` → **Load** (not Transform).
   - Power BI auto-detects types. Verify `customer_id` is **Whole number**,
     and `purchase_amount`, `loyalty_score`, `estimated_clv_proxy`, etc. are
     **Decimal number**.

### A.2 Import the pre-built measures
1. *External tools → Tabular Editor* (Tabular Editor opens connected to the
   live PBI Desktop model).
2. In Tabular Editor: *File → Open → From File* → choose `powerbi\model.bim`.
3. From the imported model, **drag the entire `Measures` folder** under the
   `customer_features` table onto the same table in the local model (right pane).
   This copies all 19 measures with their format strings and display folders.
4. *File → Save* (saves into Power BI Desktop). Close Tabular Editor.

### A.3 Apply the theme
1. In Power BI Desktop: *View → Themes → Browse for themes* → select
   `powerbi\theme.json`. The navy/accent palette applies instantly.

### A.4 Build the four panels — see `DASHBOARD_GUIDE.md` §2
Follow the panel-by-panel build in `DASHBOARD_GUIDE.md`. Each panel maps to
one or two pre-built measures from the imported model.

### A.5 Save
*File → Save As* → `assets\DecodingCustomerValue.pbix`. Done.

---

## Path B — No extra tools (10 minutes, plain Power BI Desktop)

### B.1 Open a new Power BI Desktop session
Same as A.1 above.

### B.2 Apply the theme
Same as A.3 above.

### B.3 Add the 19 measures from `measures.dax`
Open `powerbi\measures.dax` in any text editor. For each measure block:

1. In Power BI Desktop: *Modeling → New measure* (or right-click the
   `customer_features` table → *New measure*).
2. Replace the default formula with the measure body. Example:

   ```dax
   Total Customers = DISTINCTCOUNT ( customer_features[customer_id] )
   ```

3. After typing, in the *Measure tools* ribbon set the **Format** appropriately:
   - Currency: `Total Projected CLV`, `Avg CLV per Customer`, `CLV Top 20 Pct`,
     `Discounted CLV`, `Full Price CLV`, `Estimated Margin Recovery`,
     `Margin At Risk CLV`, `Margin Adjusted CLV`
   - Percentage (1 decimal): `Pct Premium Customers`, `Pct Satisfied`,
     `Pct Discounted`, `Pct Subscribed`, `Pct CLV from Top 20 Pct`,
     `Pct CLV Discount Attached`
   - Decimal (3 places): all `Avg ...` measures, `Avg Region Quality`,
     `Avg Organic Demand`

Repeat for all 19 measures. Allow ~6 minutes.

### B.4 Build the four panels and save
Same as A.4 and A.5.

---

## The four panels — quick spec

Full spec lives in [`DASHBOARD_GUIDE.md §2`](DASHBOARD_GUIDE.md). Summary:

| Panel | Visual type | Data fields | Measures |
|---|---|---|---|
| **① Customer Pyramid** | Stacked horizontal bar | `revenue_contribution_tier` on Axis | `Total Projected CLV` |
| **② Promo Dep × Retention by persona** | Scatter (bubble) | X = `Avg Promo Dependency`; Y = `Avg Loyalty Score`; Bubble = `Total Customers`; Legend = `customer_persona` | (uses 3 measures) |
| **③ Geographic Opportunity Map** | Filled map | Location = `location`; Saturation = `Margin Adjusted CLV` | `Margin Adjusted CLV` |
| **④ Category Funnel** | Funnel visual | Group = `category`; Value = count of customers where `previous_purchases < 25` (entry-point) | (DAX measure shown below) |

For Panel ④, add a small helper measure if you want the funnel ordered by
share of low-history customers (Microsoft's Funnel visual orders descending
automatically):
```dax
Low History Customers =
CALCULATE ( [Total Customers], customer_features[previous_purchases] < 25 )
```

### Top KPI strip
Four card visuals across the top: `Total Customers`, `Total Projected CLV`,
`Pct CLV from Top 20 Pct`, `Pct CLV Discount Attached`.

### Page footer (text box)
Paste the data caveat from the dashboard guide:
> *Discount / subscription / gender are structurally entangled in the source —
> promo metrics are directional, not causal. See LIMITATIONS_AND_ETHICS.md.*

---

## Verifying the build matches the project's numbers

After loading, your KPI strip should match these (from
`reports/sql_exports/exec_kpis.csv`):

| KPI | Expected |
|---|---|
| `Total Customers` | 3,900 |
| `Total Projected CLV` | ~$12.6M |
| `Pct CLV from Top 20 Pct` | ~59.5% |
| `Pct CLV Discount Attached` | ~39.0% |
| `Pct Satisfied` | ~50% |
| `Pct Premium Customers` | ~20% |

If a card reads ≠ these to within ±0.5pp, check that the **summarize-by**
on the underlying column is correct (e.g. `estimated_clv_proxy` should
default to **Sum**, not Average).

---

## Why not a pre-built `.pbix` in the repo?

The `.pbix` binary format requires Power BI Desktop to encode (proprietary
VertiPaq columnar store + signed metadata). Producing one outside Power BI
Desktop without that toolchain is unreliable — files often fail to open or
load with errors.

The repo therefore ships everything *Power BI Desktop needs* to produce a
clean `.pbix` in one short session:

- `powerbi/model.bim` — TMSL semantic model with all 19 measures
- `powerbi/measures.dax` — same measures as plain DAX (fallback for Path B)
- `powerbi/theme.json` — the visual theme
- `powerbi/DASHBOARD_GUIDE.md` — panel-by-panel build spec
- `assets/founder_dashboard_mockup.png` — visual reference of the final layout
- `data/processed/customer_features.csv` — the data
- `reports/sql_exports/*.csv` — pre-aggregated CSVs for the panels

Once you've built the `.pbix`, save it to `assets/DecodingCustomerValue.pbix`
so it sits alongside the mockup PNG.

---

## Publishing (optional)

To publish to the Power BI Service:
1. *File → Publish → My workspace*.
2. In the service, set a data source for the CSV (Personal Gateway or upload
   the CSV to OneDrive/SharePoint and re-point the source).
3. Pin visuals to a dashboard if needed.

For a Postgres-backed live refresh, change the data source from the CSV to
the Postgres database the pipeline writes to (set `DCV_DB_BACKEND=postgres`).
Power BI Desktop has native Postgres connectivity.
