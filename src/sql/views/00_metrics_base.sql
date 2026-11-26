-- ============================================================================
-- METRICS BASE — shared, reusable aggregates
--
-- Many downstream views previously recomputed the same grand totals (total CLV,
-- total customers, average loyalty, P80 cutoff). Centralising them here:
--   * eliminates duplication,
--   * gives a single point of truth that exactly matches the Streamlit/Power BI
--     KPI definitions (see docs/SQL_METRICS.md),
--   * makes future changes O(1) instead of O(views).
--
-- This is materialised as a regular view (one row) — portable across SQLite and
-- PostgreSQL. On Postgres, consider promoting to a MATERIALIZED VIEW with a
-- scheduled REFRESH if the customer_features table grows large.
-- ============================================================================

DROP VIEW IF EXISTS v_metrics_base;
CREATE VIEW v_metrics_base AS
WITH ordered AS (
    SELECT estimated_clv_proxy,
           NTILE(5) OVER (ORDER BY estimated_clv_proxy DESC) AS value_quintile
    FROM customer_features
)
SELECT
    COUNT(*)                                          AS total_customers,
    SUM(estimated_clv_proxy)                          AS total_clv,
    AVG(estimated_clv_proxy)                          AS avg_clv,
    SUM(economic_value_proxy)                         AS total_economic_value,
    AVG(loyalty_score)                                AS avg_loyalty,
    AVG(promo_dependency_score)                       AS avg_promo_dependency,
    -- Top-20% cutoff: the smallest CLV inside quintile 1 (the highest by NTILE order).
    (SELECT MIN(estimated_clv_proxy) FROM ordered WHERE value_quintile = 1) AS p80_clv_cut,
    AVG(satisfaction_flag)                            AS pct_satisfied
FROM customer_features;
