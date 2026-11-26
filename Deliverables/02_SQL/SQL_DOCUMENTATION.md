# SQL Analytics Layer — Documentation

The SQL layer turns the engineered customer table into board-ready analytics. It
is intentionally **view-driven**: the pipeline loads one table
(`customer_features`) and every insight is a reusable, documented view on top.

> **Portability:** all SQL runs on **SQLite 3.25+** (default, zero setup) and
> **PostgreSQL** (production). Only standard CTEs and window functions are used.
> Boolean flags are stored as integers `0/1` for cross-engine parity.

## 1. How it's built

```bash
python -m src.pipeline            # builds the DB + exports all views to CSV
# or just the SQL step against an existing feature table, via the runner API
```

The runner (`src/sql/runner.py`):
1. `prepare_analytics_frame()` — selects the analytics columns, casts flags to int.
2. Loads `customer_features` (replace).
3. Applies `src/sql/schema/*.sql` then `src/sql/views/*.sql` in lexical order.
4. Exports each view in `VIEW_EXPORTS` to `reports/sql_exports/<name>.csv`.

## 2. File map

| File | Contents |
|---|---|
| `src/sql/schema/01_schema.sql` | `customer_features` DDL (contract) + indexes |
| `src/sql/views/10_segmentation.sql` | Persona scorecard + 5 customer-segment views |
| `src/sql/views/20_geography.sql` | Region scorecard, organic/high-margin/promo-heavy regions |
| `src/sql/views/30_product.sql` | Category scorecard, retention-driving & entry-point categories, high-loyalty products |
| `src/sql/views/40_revenue.sql` | Discount split, revenue concentration (deciles), tier contribution |
| `src/sql/views/50_executive.sql` | KPI strip, loyalty distribution, promo×retention matrix + by-persona, exec category |
| `src/sql/views/60_demographics.sql` | `v_demographic_opportunity` — age band × gender lens (PDF Q3 demographics half) |
| `src/sql/queries/analytical_queries.sql` | 6 ad-hoc analyses (Pareto, margin-at-risk, quadrants, Lorenz) |

## 3. View reference

### Segmentation (`10_segmentation.sql`)
| View | Question answered |
|---|---|
| `v_persona_scorecard` | Size, value share, loyalty & promo reliance of each persona |
| `v_loyal_customers` | High-loyalty, low-promo customers (the core to protect) |
| `v_promo_hunters` | High promo dependency, below-average value |
| `v_premium_customers` | Top-tier value AND satisfied |
| `v_high_risk_customers` | High value but NOT satisfied (retention danger) |
| `v_high_value_low_frequency` | Big baskets, rare visits (frequency upside) |

### Geography (`20_geography.sql`)
| View | Question answered |
|---|---|
| `v_region_scorecard` | Full per-state economics (quality, organic demand, CLV) |
| `v_organic_demand_regions` | Healthy markets to double down on |
| `v_high_margin_regions` | High value with low discount leakage |
| `v_promo_heavy_regions` | Discount-reliant markets (margin risk) |

### Product (`30_product.sql`)
| View | Question answered |
|---|---|
| `v_category_scorecard` | Category economics through a loyalty lens |
| `v_retention_driving_categories` | Which categories build loyalty (ranked) |
| `v_entry_point_categories` | Acquisition doors (high share of low-history buyers) |
| `v_high_loyalty_products` | Item-level loyalty leaders (≥20 purchases) |

### Revenue (`40_revenue.sql`)
| View | Question answered |
|---|---|
| `v_revenue_discount_split` | Discounted vs full-price revenue & CLV |
| `v_revenue_concentration` | Decile contribution + cumulative % (Pareto) |
| `v_revenue_tier_contribution` | Platinum/Gold/Silver/Bronze contribution |

### Executive (`50_executive.sql`)
| View | Question answered |
|---|---|
| `v_executive_kpis` | One-row KPI strip for the cockpit |
| `v_loyalty_distribution` | Loyalty-tier sizes and value share |
| `v_promo_retention_matrix` | The strategic 2×2 (loyalty × promo) — aggregated |
| `v_promo_retention_by_persona` | Same 2×2 lens **broken out by persona** — drives Founder Page Panel 2 |
| `v_executive_category` | Compact category bar for the exec page |

### Demographics (`60_demographics.sql`)
| View | Question answered |
|---|---|
| `v_demographic_opportunity` | Age band × gender — `avg_clv`, `loyalty_score`, `promo_dependency`, `pct_premium`. Closes the "demographics" half of PDF Q3. |

## 4. Techniques used (and why)
- **CTEs** for readability and to compute totals once (e.g. `WITH totals AS …`).
- **Window functions** — `NTILE` (deciles/quintiles), `RANK` (category leaders),
  running `SUM() OVER (ORDER BY …)` (cumulative Pareto / Lorenz curve).
- **`CROSS JOIN` to a 1-row totals CTE** to compute shares without correlated
  subqueries (fast and portable).
- **Integer flags** so boolean logic behaves identically on SQLite and Postgres.

## 5. PostgreSQL notes
- Set `DCV_DB_BACKEND=postgres` (or `DCV_DB_URL=postgresql+psycopg2://…`) and
  install `psycopg2-binary`. The same view files apply unchanged.
- For heavy datasets, convert the hottest views to **materialized views**
  (`CREATE MATERIALIZED VIEW … ; REFRESH MATERIALIZED VIEW …`). SQLite has no
  materialized views, which is why the portable default uses regular views.
