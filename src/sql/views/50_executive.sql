-- ============================================================================
-- EXECUTIVE VIEWS
-- The single-glance numbers for the leadership dashboard. Each row/column maps
-- directly to a KPI card or headline chart.
-- ============================================================================

-- --- One-row KPI strip -------------------------------------------------------
DROP VIEW IF EXISTS v_executive_kpis;
CREATE VIEW v_executive_kpis AS
SELECT
    COUNT(*)                                                      AS total_customers,
    ROUND(SUM(estimated_clv_proxy),2)                             AS total_projected_clv,
    ROUND(AVG(estimated_clv_proxy),2)                             AS avg_clv,
    ROUND(AVG(loyalty_score),3)                                   AS avg_loyalty,
    ROUND(AVG(promo_dependency_score),3)                          AS avg_promo_dependency,
    ROUND(100.0 * AVG(CASE WHEN discount_applied = 'Yes' THEN 1.0 ELSE 0.0 END),1)
                                                                  AS pct_discounted,
    ROUND(100.0 * AVG(satisfaction_flag),1)                       AS pct_satisfied,
    ROUND(100.0 * AVG(CASE WHEN premium_customer_flag = 1 THEN 1.0 ELSE 0.0 END),1)
                                                                  AS pct_premium,
    ROUND(100.0 * AVG(CASE WHEN subscription_status = 'Yes' THEN 1.0 ELSE 0.0 END),1)
                                                                  AS pct_subscribed
FROM customer_features;

-- --- Loyalty distribution (for the loyalty histogram / pyramid) ---------------
-- Uses v_metrics_base (00_metrics_base.sql) for the grand totals, so there is
-- exactly one definition of `total_customers` / `total_clv` across the project.
DROP VIEW IF EXISTS v_loyalty_distribution;
CREATE VIEW v_loyalty_distribution AS
SELECT cf.loyalty_tier,
       COUNT(*)                                          AS customers,
       ROUND(100.0 * COUNT(*) / m.total_customers, 1)    AS pct_customers,
       ROUND(AVG(cf.estimated_clv_proxy),2)              AS avg_clv,
       ROUND(100.0 * SUM(cf.estimated_clv_proxy) / m.total_clv, 1) AS pct_of_clv
FROM customer_features cf
CROSS JOIN v_metrics_base m
GROUP BY cf.loyalty_tier, m.total_customers, m.total_clv
ORDER BY cf.loyalty_tier;

-- --- Promo dependency vs retention matrix (2x2 quadrants) ---------------------
-- The strategic centrepiece: cross loyalty (retention proxy) with promo reliance.
-- Uses v_metrics_base for the loyalty mid-line so this matches every other view.
DROP VIEW IF EXISTS v_promo_retention_matrix;
CREATE VIEW v_promo_retention_matrix AS
WITH q AS (
    SELECT cf.customer_id, cf.estimated_clv_proxy,
           CASE WHEN cf.loyalty_score >= m.avg_loyalty
                THEN 'High Loyalty' ELSE 'Low Loyalty' END AS loyalty_band,
           CASE WHEN cf.promo_dependency_score >= 0.5
                THEN 'High Promo' ELSE 'Low Promo' END      AS promo_band
    FROM customer_features cf
    CROSS JOIN v_metrics_base m
)
SELECT loyalty_band, promo_band,
       COUNT(*)                              AS customers,
       ROUND(AVG(estimated_clv_proxy),2)     AS avg_clv,
       ROUND(SUM(estimated_clv_proxy),2)     AS total_clv
FROM q
GROUP BY loyalty_band, promo_band
ORDER BY loyalty_band, promo_band;

-- --- Promo × retention BY SEGMENT (Founder Page Panel 2) ---------------------
-- The PDF asks for "Promo dependency vs. retention rate, plotted BY SEGMENT".
-- This view exposes the persona dimension that v_promo_retention_matrix
-- aggregates over, so each persona becomes a bubble on the Founder Page scatter.
DROP VIEW IF EXISTS v_promo_retention_by_persona;
CREATE VIEW v_promo_retention_by_persona AS
SELECT
    customer_persona,
    COUNT(*)                                          AS customers,
    ROUND(AVG(loyalty_score), 3)                      AS avg_loyalty,
    ROUND(AVG(promo_dependency_score), 3)             AS avg_promo_dependency,
    ROUND(AVG(estimated_clv_proxy), 2)                AS avg_clv,
    ROUND(SUM(estimated_clv_proxy), 2)                AS total_clv,
    -- Quadrant label vs the dataset average loyalty + 0.5 promo cutoff.
    CASE
        WHEN AVG(loyalty_score) >= (SELECT avg_loyalty FROM v_metrics_base)
             AND AVG(promo_dependency_score) <  0.5 THEN 'Healthy core (High Loy / Low Promo)'
        WHEN AVG(loyalty_score) >= (SELECT avg_loyalty FROM v_metrics_base)
             AND AVG(promo_dependency_score) >= 0.5 THEN 'Margin at risk (High Loy / High Promo)'
        WHEN AVG(loyalty_score) <  (SELECT avg_loyalty FROM v_metrics_base)
             AND AVG(promo_dependency_score) >= 0.5 THEN 'Promo hunters (Low Loy / High Promo)'
        ELSE                                                'Dormant (Low Loy / Low Promo)'
    END                                               AS quadrant
FROM customer_features
GROUP BY customer_persona
ORDER BY total_clv DESC;

-- --- Category performance compact (for exec category bar) ---------------------
DROP VIEW IF EXISTS v_executive_category;
CREATE VIEW v_executive_category AS
SELECT category,
       COUNT(*)                              AS customers,
       ROUND(SUM(estimated_clv_proxy),2)     AS total_clv,
       ROUND(AVG(loyalty_score),3)           AS avg_loyalty,
       ROUND(AVG(promo_dependency_score),3)  AS avg_promo_dependency
FROM customer_features
GROUP BY category
ORDER BY total_clv DESC;
