# Growth Strategy
### Margin-accretive growth across acquisition, retention, and product

The brand's growth problem is not volume — it is **quality of growth**. Value is
highly concentrated (top 20% of customers hold ~60% of projected CLV) and a large
share of activity is discount-attached. The strategy below grows the *right*
customers while structurally reducing promotional dependency.

---

## 1. Acquisition — buy more of the ICP, fewer Promo Hunters

| Move | Detail | KPI |
|---|---|---|
| **ICP look-alikes** | Seed audiences from the 639-strong ICP cohort (see ICP doc). | CAC of ICP-matched cohort; their 12-mo CLV |
| **Suppress discount hooks in prospecting** | Discount-led creative over-recruits Promo Hunters (avg CLV ~$814). | % new customers landing in Promo Hunter persona |
| **Geo-weighting** | Over-index ICP-strong states (NY, GA, TN, AL, MD); test demographic-adjacent markets. | New-customer CLV by state |
| **Channel-fit** | Lead with hero items (boots, coats, jewelry) + speed-of-delivery value prop. | Creative-level ROAS on full-price baskets |

## 2. Retention — protect the core, repair the at-risk

| Priority | Cohort | Play |
|---|---|---|
| **P0 — Protect** | Top-20% value + Premium Loyalists | Ring-fence from discount messaging; concierge service, early access, loyalty status. |
| **P1 — Repair** | **At-Risk Premium (n ≈ 233): high value, NOT satisfied** | Proactive CX intervention (these are high-CLV customers actively unhappy — the single highest-ROI save). Root-cause via category/region drill-down. |
| **P2 — Convert** | High-Value Low-Frequency | Frequency-building: replenishment prompts, curated drops, bundles — grow visits, not basket discounts. |
| **P3 — Migrate** | High-value Discount-Dependent (~230, ~$2.1M CLV) | Move to behaviour-based loyalty rewards before any discount withdrawal (Wave 4 of the sunset plan). |

## 3. Margin optimisation
- Execute the **Promotional Sunset Plan** wave-by-wave; recycle recovered margin
  into ICP acquisition and the P1 "repair" programme.
- Use **regional promo elasticity** (`promo_sensitivity_geo`) to pull discounts
  first where they least affect volume.
- Shift the value proposition from **price** to **speed + service**, which the ICP
  already pays for (shipping skews to 2-Day/Express/Next-Day).

## 4. Product / merchandising
- **Double down on retention-driving categories** (rank categories by
  `v_retention_driving_categories`): merchandise and bundle around the ones with
  the highest loyalty, not just the highest revenue.
- **Use entry-point categories** (`v_entry_point_categories`) as acquisition
  doors, then cross-sell into retention-driving categories within 60 days.
- **Promote hero items** (boots, coats, skirts, jewelry) as anchor SKUs in
  full-price campaigns.

## 5. 12-month north-star targets

| Metric | Baseline | 12-mo target | Mechanism |
|---|---:|---:|---|
| % CLV discount-attached | ~39% | ≤ 30% | Sunset plan waves 1–3 |
| Promo Hunter share of *new* customers | (track) | ↓ ≥ 30% | Acquisition creative shift |
| At-Risk Premium count | 233 | ↓ ≥ 40% | P1 repair programme |
| Top-20% CLV retention | — | ≥ 100% | P0 protection |
| Blended gross margin % | — | ↑ | Margin recycling |

> Every target maps to a metric the pipeline already produces — progress is
> measurable monthly from the same dashboard, not a one-off study.
