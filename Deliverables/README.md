# Deliverables — Decoding Customer Value: A SQL-Driven Retention Strategy

> **Consulting & Analytics Club — IIT Guwahati**
> Submission for the official Problem Statement PDF.

## Submitted by

| Team member | Programme | Institute | Email |
|---|---|---|---|
| **Anant Shukla** | B.Tech. Civil Engineering | IIT Roorkee | anant_s@ce.iitr.ac.in |
| **Khushi Rawat** | B.Tech. Civil Engineering | IIT Roorkee | khushi_r@ce.iitr.ac.in |

---

This folder is self-contained and maps 1:1 to the **Deliverables table on page 3
of the PDF**:

| PDF Deliverable | Folder | What's inside |
|---|---|---|
| **Python** — Cleaned dataset + engineered features (dependency score, value tier, satisfaction flag) | [`01_Python/`](01_Python/) | `customer_features.csv` (3,900 rows × 46 typed features), the raw dataset, the feature glossary, and the source code that produced them |
| **SQL** — Segmentation queries answering all 5 key questions | [`02_SQL/`](02_SQL/) | 19 SQL views (`views/`) + 6 ad-hoc analytical queries (`queries/`), CSV exports (`exports/`), and full documentation |
| **Power BI** — Four-panel founder dashboard as described in scope | [`03_PowerBI/`](03_PowerBI/) | PBIP project (opens in Power BI Desktop, save as `.pbix`), theme, DAX measures, layout spec, and screenshots of the rendered dashboard |
| **Playbook** — Promo sunset plan + ideal customer profile | [`04_Playbook/`](04_Playbook/) | The two required documents at the root; two bonus recommendations (`growth`, `risk`) in `extras/` |
| **Summary** — Concise executive summary (max 1 page) of findings and recommendations | [`05_Summary/`](05_Summary/) | `executive_summary.md` (≤1 page); bonus 3-page consolidated `CUSTOMER_INTELLIGENCE_REPORT.md` and `loyalty_framework.md` in `extras/` |

---

## How to consume this folder

1. **Read first:** [`05_Summary/executive_summary.md`](05_Summary/executive_summary.md) — one page, gives the verdict and the headlines.
2. **For the Power BI dashboard:** [`03_PowerBI/PBIP_Project/DecodingCustomerValue_V2_Legacy.pbip`](03_PowerBI/PBIP_Project/) — open in Power BI Desktop, refresh, save as `.pbix`. The 4 panels and 4 KPI cards render automatically from the embedded `report.json`.
3. **For the SQL layer:** every CSV in [`02_SQL/exports/`](02_SQL/exports/) is the output of the SQL view of the same name in [`02_SQL/views/`](02_SQL/views/). The 5 PDF questions map 1:1 to views — see [`02_SQL/SQL_DOCUMENTATION.md`](02_SQL/SQL_DOCUMENTATION.md).
4. **For the recommendations:** [`04_Playbook/01_promotional_sunset_plan.md`](04_Playbook/01_promotional_sunset_plan.md) names the SEGMENT, TRIGGER, TIMELINE, METRIC per wave (as the PDF mandates — "Reduce discounts is not an acceptable answer"). [`04_Playbook/02_ideal_customer_profile.md`](04_Playbook/02_ideal_customer_profile.md) gives the ICP precise enough for a marketing team to act on today.

---

## How the dashboard satisfies the four PDF panel mandates

The PDF section 3 mandates these four panels for the Founder Dashboard. Each is present:

| PDF mandate | How it's built |
|---|---|
| **Customer pyramid** — value distribution across the customer base | `revenue_tier_contribution` bar chart (Bronze · Silver · Gold · Platinum) — Power BI Panel 1 |
| **Promo dependency vs. retention rate, plotted by segment** | Scatter bubble chart: X = avg promo dependency, Y = avg loyalty, bubbles = customer personas — Power BI Panel 2 |
| **Geographic opportunity map — high spend AND low promo dependency** | Filled map keyed off `margin_adjusted_clv` = `estimated_clv × (1 − promo_dependency)` — encodes both signals in one metric. Power BI Panel 3 |
| **Category funnel — low purchase history vs high purchase history** | Funnel of entry-point categories by `new_ish_customers` count (customers with < median previous_purchases) — Power BI Panel 4 |

---

## How the methodology satisfies the Central Analytical Challenge

The PDF's "Central Analytical Challenge" requires:

- **Loyalty must be defined, not declared. At least two competing definitions, tested, with one defended.**
  → Two definitions (A: behaviour-only, B: behaviour + margin-aware) are scored on 5 criteria
  in [`05_Summary/extras/loyalty_framework.md`](05_Summary/extras/loyalty_framework.md). **Definition B wins** with 0.666 vs 0.627 on the orthogonal `economic_value_proxy` validation target. The score is not self-correlated because the validation target excludes loyalty from its construction.

- **Every segment claim must be traceable.**
  → Each of the 6 personas (`Premium Loyalist`, `Loyal Full-Price`, `Margin-at-Risk Premium`, `Promo Hunter`, `At-Risk Premium`, `Casual Buyer`) is a stated combination of `loyalty_tier × promo_reliance_tier × revenue_contribution_tier`. See [`02_SQL/views/10_segmentation.sql`](02_SQL/views/10_segmentation.sql).

- **Expected Outcome question:** "Is the business successfully building a loyal customer base, or is it reliant on continuous promotional activity?"
  → Answered explicitly on the first line of [`05_Summary/executive_summary.md`](05_Summary/executive_summary.md): **partially reliant — 43% discounted, 39% of CLV discount-attached, but most is habit not stimulus. Loyalty is being built, but the brand is also subsidising demand it doesn't need to.**

