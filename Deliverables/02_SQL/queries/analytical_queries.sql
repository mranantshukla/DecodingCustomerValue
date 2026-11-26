-- ============================================================================
-- ANALYTICAL QUERY LIBRARY
-- Standalone, copy-paste-ready queries that go BEYOND the persisted views to
-- demonstrate ad-hoc analysis. Each is documented with the business question it
-- answers. All run on SQLite 3.25+ and PostgreSQL.
--
-- Run any block against the database produced by `python -m src.pipeline`:
--   sqlite3 data/processed/customer_value.db < this_file.sql   (or paste blocks)
-- ============================================================================


-- Q1. THE 80/20 CHECK ---------------------------------------------------------
-- Q: What share of projected value comes from the top decile of customers?
-- Why: validates the "protect the top" thesis and sizes concentration risk.
WITH ranked AS (
    SELECT customer_id, estimated_clv_proxy,
           NTILE(10) OVER (ORDER BY estimated_clv_proxy DESC) AS decile
    FROM customer_features
)
SELECT decile,
       COUNT(*) AS customers,
       ROUND(SUM(estimated_clv_proxy), 0) AS clv,
       ROUND(100.0 * SUM(estimated_clv_proxy)
             / SUM(SUM(estimated_clv_proxy)) OVER (), 1) AS pct_of_clv
FROM ranked
GROUP BY decile
ORDER BY decile;


-- Q2. MARGIN-AT-RISK FROM DISCOUNT-DEPENDENT HIGH-VALUE CUSTOMERS -------------
-- Q: How much projected CLV sits with customers who are BOTH high-value AND
--    discount-dependent (the cohort the sunset plan must handle carefully)?
WITH thresholds AS (
    SELECT (SELECT estimated_clv_proxy FROM customer_features
            ORDER BY estimated_clv_proxy DESC
            LIMIT 1 OFFSET (SELECT CAST(0.2 * COUNT(*) AS INT) FROM customer_features)) AS hv_cut
)
SELECT
    COUNT(*)                                       AS at_risk_customers,
    ROUND(SUM(cf.estimated_clv_proxy), 0)          AS at_risk_clv,
    ROUND(AVG(cf.promo_dependency_score), 3)       AS avg_promo_dependency
FROM customer_features cf, thresholds t
WHERE cf.estimated_clv_proxy >= t.hv_cut
  AND cf.promo_reliance_tier = 'Discount-Dependent';


-- Q3. LOYALTY LIFT BY SUBSCRIPTION (confound-aware) ---------------------------
-- Q: Do subscribers show higher loyalty AND higher full-price behaviour?
-- Why: subscription is entangled with discounting in this data, so we report
--      loyalty and non-discount ratio side by side rather than in isolation.
SELECT subscription_status,
       COUNT(*)                                  AS customers,
       ROUND(AVG(loyalty_score), 3)              AS avg_loyalty,
       ROUND(AVG(non_discount_purchase_ratio),3) AS avg_full_price_ratio,
       ROUND(AVG(estimated_clv_proxy), 0)        AS avg_clv
FROM customer_features
GROUP BY subscription_status;


-- Q4. CATEGORY RETENTION RANK WITH WINDOW FUNCTIONS ---------------------------
-- Q: Rank categories by loyalty and show each one's gap to the leader.
SELECT category,
       ROUND(AVG(loyalty_score), 3) AS avg_loyalty,
       RANK()  OVER (ORDER BY AVG(loyalty_score) DESC) AS loyalty_rank,
       ROUND(MAX(AVG(loyalty_score)) OVER () - AVG(loyalty_score), 3) AS gap_to_leader
FROM customer_features
GROUP BY category
ORDER BY avg_loyalty DESC;


-- Q5. REGIONAL OPPORTUNITY QUADRANT -------------------------------------------
-- Q: Classify regions into invest / harvest / fix / watch quadrants by crossing
--    region quality with promo dependency (vs their medians).
WITH r AS (
    SELECT location,
           AVG(region_quality_index)  AS quality,
           AVG(promo_dependency_score) AS promo,
           SUM(estimated_clv_proxy)   AS clv,
           COUNT(*)                   AS customers
    FROM customer_features GROUP BY location
), m AS (
    SELECT AVG(quality) AS mq, AVG(promo) AS mp FROM r
)
SELECT r.location, ROUND(r.quality,3) AS quality, ROUND(r.promo,3) AS promo_dependency,
       ROUND(r.clv,0) AS total_clv, r.customers,
       CASE
         WHEN r.quality >= m.mq AND r.promo <  m.mp THEN 'INVEST (healthy)'
         WHEN r.quality >= m.mq AND r.promo >= m.mp THEN 'FIX (good but subsidised)'
         WHEN r.quality <  m.mq AND r.promo <  m.mp THEN 'WATCH (low engagement)'
         ELSE 'HARVEST/RATIONALISE (weak + subsidised)'
       END AS quadrant
FROM r, m
ORDER BY r.quality DESC;


-- Q6. RUNNING CUMULATIVE CLV (Lorenz-style curve input) -----------------------
-- Q: Ordered customers, cumulative share of value — feeds a concentration curve.
WITH ordered AS (
    SELECT customer_id, estimated_clv_proxy,
           ROW_NUMBER() OVER (ORDER BY estimated_clv_proxy DESC) AS rn,
           COUNT(*)     OVER ()                                  AS n,
           SUM(estimated_clv_proxy) OVER ()                      AS total
    FROM customer_features
)
SELECT ROUND(100.0 * rn / n, 1) AS pct_customers,
       ROUND(100.0 * SUM(estimated_clv_proxy) OVER (ORDER BY rn) / total, 1) AS cum_pct_clv
FROM ordered
WHERE rn % 195 = 0          -- ~20 sample points across 3,900 customers
ORDER BY rn;
