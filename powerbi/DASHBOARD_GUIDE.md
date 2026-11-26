# Power BI Dashboard — Founder Dashboard + Analyst Companion Pages

This is the executive-facing layer of the project. The Streamlit app (in
`src/dashboard/`) is the interactive analyst tool; **Power BI is the board-room
deliverable**.

> **⚡ Going straight to `.pbix`?** The fastest path is to open the
> pre-authored PBIP project at
> [`dashboard/DecodingCustomerValue.pbip`](dashboard/DecodingCustomerValue.pbip)
> in Power BI Desktop — the semantic model AND the four-panel Founder
> Dashboard load automatically, then *File → Save As → `.pbix`* writes the
> binary. The full click-path is in
> [`BUILD_PBIX_STEP_BY_STEP.md`](BUILD_PBIX_STEP_BY_STEP.md) (Path 0). If you
> prefer to author from a blank report, the same doc covers Path A
> (Tabular Editor + `model.bim`) and Path B (manual measure entry from
> `measures.dax`).

> **Data source:** `data/processed/customer_features.csv` (one row per customer).
> Also import the view exports in `reports/sql_exports/` as supporting tables —
> in particular `promo_retention_by_persona.csv` and `demographic_opportunity.csv`
> for the founder page panels. Generate them with `python -m src.pipeline`.

---

## 0. The deliverable, exactly as the brief specifies it

The official brief mandates **a clean, four-panel dashboard designed for a non-
technical founding team**. That dashboard is the **Founder Page** below — one
page, four panels, in a 2×2 layout. Nothing else competes for the founder's
attention.

The pages after the Founder Page are **Analyst Companion Pages**: deeper drill-
through views beyond the brief's scope, useful for an analyst preparing for a
board meeting but never required for the founder herself.

---

## 1. Design principles

| Principle | Decision |
|---|---|
| **Founder page = ONE page, four panels** | No more, no fewer. 2×2 layout, no scrolling. |
| **KPIs in a thin top strip** | 4 cards above the four panels. Not a panel of their own. |
| **Action in the title** | "Top 20% hold ~60% of value" — not "CLV by decile". |
| **Restraint over decoration** | One accent colour (`#2E86AB`), red reserved for risk only. No 3-D, no pies. |
| **Caveats visible** | A persistent footnote flags the discount/subscription/gender confound so no one over-reads promo splits. |

**Theme:** Navy `#16324F` (text/primary), Accent `#2E86AB`, Gold `#E0A458`
(promo/attention), Risk `#C1483B`, Good `#3A8B5C`, Grey `#8A99A8`. Font: Segoe UI.
Save as a custom theme JSON (`powerbi/theme.json`) and apply via View > Themes.

---

## 2. The Founder Dashboard (one page, four panels)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║ DECODING CUSTOMER VALUE — FOUNDER DASHBOARD          [Persona ▾] [Category ▾] ║
╟───────────────────────────────────────────────────────────────────────────╢
║  Customers  │  Projected CLV  │  Top-20% share of CLV  │  % CLV discount-attached  ║
║   3,900     │     $12.6M      │         ~60%           │           ~39%            ║
╠══════════════════════════════════════╦══════════════════════════════════════╣
║                                      ║                                      ║
║  ① CUSTOMER PYRAMID                  ║  ② PROMO DEPENDENCY × RETENTION       ║
║  100% stacked bar, by value tier     ║  Scatter, BY SEGMENT (persona)       ║
║  (Bronze/Silver/Gold/Platinum)       ║  bubble = customers; colour = avg CLV ║
║                                      ║                                      ║
╠══════════════════════════════════════╬══════════════════════════════════════╣
║                                      ║                                      ║
║  ③ GEOGRAPHIC OPPORTUNITY MAP        ║  ④ CATEGORY FUNNEL                    ║
║  Choropleth (US states), coloured    ║  TRUE funnel: categories ordered       ║
║  by margin-adjusted CLV; high spend  ║  by % low-history customers — top of  ║
║  + low promo dependency overlaid     ║  funnel = entry-point categories;     ║
║                                      ║  bottom = retention categories.       ║
╚══════════════════════════════════════╩══════════════════════════════════════╝
Footnote: "Discount/subscription/gender are structurally entangled in the source —
promo metrics are directional, not causal. See LIMITATIONS_AND_ETHICS for detail."
```

### Panel-by-panel build

#### Panel ① — Customer Pyramid
- **Visual:** Stacked horizontal bar, 100% normalised, one stack per value tier.
- **Field:** `revenue_contribution_tier` on Axis, `Total Projected CLV` as Value,
  measure `Pct CLV from Top 20 Pct` as Tooltip.
- **Data source:** `reports/sql_exports/revenue_tier_contribution.csv`
  (or live from `customer_features` via the DAX measures in `measures.dax`).
- **Title takeaway:** "Top 20% of customers hold ~60% of projected CLV".
- **Why this visual:** the pyramid is the single fastest way to communicate
  value concentration — the foundation of the entire retention thesis.

#### Panel ② — Promo Dependency × Retention (by segment)
- **Visual:** Scatter / bubble. **X = avg promo dependency, Y = avg loyalty,
  bubble size = customers, colour = avg CLV** — one bubble per **persona**.
- **Field:** `customer_persona` as Legend; the four metrics from
  `v_promo_retention_by_persona`.
- **Data source:** `reports/sql_exports/promo_retention_by_persona.csv`.
- **Quadrants:** add a vertical line at promo = 0.5 and a horizontal line at the
  mean loyalty (from `v_metrics_base.avg_loyalty`) so the four quadrants are
  visually obvious: top-left = healthy core, top-right = margin at risk,
  bottom-right = promo hunters, bottom-left = dormant.
- **Title takeaway:** "Loyal Full-Price is the healthy core; Promo-Dependent
  High-Value is the margin-at-risk cohort".

#### Panel ③ — Geographic Opportunity Map
- **Visual:** Filled map of US states (Power BI built-in Map visual), with state
  name on Location and `Margin Adjusted CLV` (DAX measure) on Saturation.
- **Overlay:** a small scatter to the right (region quality × promo dependency)
  highlighting the INVEST / FIX / WATCH / HARVEST quadrants — the same view
  produced by `Geography Insights` in Streamlit.
- **Data source:** `reports/sql_exports/region_scorecard.csv`.
- **Title takeaway:** "Healthy markets (high quality, low promo dependency)
  are where freed-up promo budget should land".

#### Panel ④ — Category Funnel (TRUE funnel, not a bar)
- **Visual:** Power BI **Funnel** visual (not a bar chart). Categories ordered
  TOP→BOTTOM by `pct_low_history` (high % at top = entry-point; low % at
  bottom = retention).
- **Field:** `category` on Group; `pct_low_history` as Value (descending).
- **Data source:** `reports/sql_exports/entry_point_categories.csv`.
- **Title takeaway:** "Categories at the top of the funnel are where new
  customers enter; categories at the bottom are where they stay".

---

## 3. KPI strip (top of Founder Page)

Four cards above the 2×2:

| Card | DAX measure |
|---|---|
| Customers | `[Total Customers]` |
| Projected CLV | `[Total Projected CLV]` |
| Top-20% share of CLV | `[Pct CLV from Top 20 Pct]` |
| % CLV discount-attached | `[Pct CLV Discount Attached]` |

The four cards correspond 1:1 to the brief's "is the brand building loyalty or
relying on promos?" question — three measure *what's working* (value pool and
its concentration), the fourth measures *what's at risk*.

---

## 4. Cross-page slicers and interactions
- **Sync slicers** for Persona and Category at the top of the page.
- **Cross-highlight** on: clicking a persona bubble in Panel ② filters the
  pyramid (①) and the map (③).
- **Bookmarks** (one button row at the bottom): "Healthy core",
  "Margin-at-risk", "At-risk premium" — each a one-click executive state.

---

## 5. Analyst Companion Pages (beyond PDF scope — optional)

These pages are NOT part of the four-panel founder dashboard. They live in the
same `.pbix` for an analyst preparing for a board meeting, but the founder
never needs them.

### Companion A — Customer Segmentation Explorer
Persona scorecard table + drill-through to a single-customer detail page. Built
from `reports/sql_exports/persona_scorecard.csv` and `customer_features.csv`.

### Companion B — Margin & Promo Risk
Waterfall (`Full Price CLV` → `Discounted CLV` → `Estimated Margin Recovery`)
+ a matrix of promo reliance tier × revenue tier with conditional formatting.
Built from the DAX measures `Discounted CLV`, `Full Price CLV`,
`Estimated Margin Recovery` in `measures.dax`.

### Companion C — Demographic Opportunity (NEW)
Heatmap of age band × gender against `avg_clv` and `loyalty_score`. Surfaces
the under-served demographic pockets that complement the geographic map. Built
from `reports/sql_exports/demographic_opportunity.csv`.

### Companion D — Ideal Customer Profile (ICP)
Card + small multiples filtered to `customer_persona IN ('Premium Loyalist',
'Loyal Full-Price')`: age band, top categories, top regions, payment mix,
shipping mix. The acquisition team's targeting brief on one page. See
[`reports/recommendations/02_ideal_customer_profile.md`](../reports/recommendations/02_ideal_customer_profile.md).

---

## 6. Refresh / deployment
- Local: re-run `python -m src.pipeline`, then **Refresh** in Power BI Desktop
  (the CSV paths are stable).
- Service: publish to Power BI Service; point the dataset at the Postgres
  database (set `DCV_DB_BACKEND=postgres`) via an on-prem gateway, or schedule
  refresh of the CSV files from blob storage.

## 7. Rendered preview (closest substitute for a `.pbix`)
A Matplotlib mockup of the exact four-panel founder page is generated by
`scripts/render_founder_dashboard_mockup.py` and saved to
`assets/founder_dashboard_mockup.png`. This is the closest substitute for a
real Power BI screenshot we can produce in this repo; the `.pbix` itself
should be built using this guide and saved to the same `assets/` folder.

## 8. Screenshot placeholders (add when built)
- `assets/founder_dashboard_mockup.png` — auto-generated Matplotlib mockup
- `assets/powerbi_founder.png` — the real Power BI Founder Page (Page 1)
- `assets/powerbi_companion_geo.png` — Companion C (Demographic Opportunity)
