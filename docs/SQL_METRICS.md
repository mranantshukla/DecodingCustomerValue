# SQL Semantic Metrics Layer

A small, deliberate semantic layer: the canonical definitions for the metrics
every view, dashboard, and report uses. The goal is **one definition per
metric** — so a number quoted in Streamlit, Power BI, the executive summary, and
an ad-hoc SQL query is provably the same number.

The single source of truth is **`v_metrics_base`** (in
`src/sql/views/00_metrics_base.sql`), a one-row view computing every grand total
referenced by other views.

## Canonical metrics

| Metric | SQL definition | Lives in | Used by |
|---|---|---|---|
| `total_customers` | `COUNT(*) FROM customer_features` | `v_metrics_base` | every roll-up |
| `total_clv` | `SUM(estimated_clv_proxy)` | `v_metrics_base` | concentration, persona shares, revenue split |
| `avg_clv` | `AVG(estimated_clv_proxy)` | `v_metrics_base` | KPI strip |
| `total_economic_value` | `SUM(economic_value_proxy)` | `v_metrics_base` | margin-recovery framing |
| `avg_loyalty` | `AVG(loyalty_score)` | `v_metrics_base` | promo×retention matrix mid-line |
| `avg_promo_dependency` | `AVG(promo_dependency_score)` | `v_metrics_base` | regional benchmarks |
| `p80_clv_cut` | smallest CLV in top quintile (`NTILE(5)`) | `v_metrics_base` | premium cutoff |
| `pct_satisfied` | `AVG(satisfaction_flag)` | `v_metrics_base` | KPI strip |

## How views consume the layer

```sql
-- BEFORE (duplicated grand total in every view)
WITH tot AS (SELECT COUNT(*) AS n, SUM(estimated_clv_proxy) AS clv FROM customer_features)
SELECT ..., 100.0 * ... / tot.clv FROM customer_features cf, tot ...

-- AFTER (one definition, reused everywhere)
SELECT ..., 100.0 * ... / m.total_clv
FROM customer_features cf
CROSS JOIN v_metrics_base m
GROUP BY ..., m.total_clv;
```

A `CROSS JOIN` against a one-row view is **free** in any engine — both SQLite
and PostgreSQL collapse it to a constant — and it keeps the SQL declarative
rather than imperative.

## Why this matters (and why we stopped here)

- **Numbers cannot disagree.** Previously, `total_clv` was recomputed in five
  places; a future change (e.g. excluding test customers) had to be made in all
  five. Now it is one line.
- **It is not a warehouse.** We deliberately did not introduce dbt, semantic
  layer DSLs, or a metric server — that would be over-engineering for a
  3,900-row dataset. The pattern (one base view + `CROSS JOIN`) is sufficient
  and would scale linearly if the team did decide to adopt dbt later.

## Indexing rationale (recap from schema)

| Index | Why |
|---|---|
| `idx_cf_location` | Region scorecard, opportunity quadrants, geo simulator |
| `idx_cf_category` | Category scorecard, retention-driving categories |
| `idx_cf_persona` | Persona scorecard, dashboard cross-filtering |
| `idx_cf_rev_tier` | Customer pyramid, value-tier contribution |
| `idx_cf_promotier` | Promo Impact Simulator, sunset-plan cohort selection |

These are the columns the analytical views `GROUP BY` or `WHERE` against most
often; the unique `customer_id` already has the implicit PK index.
