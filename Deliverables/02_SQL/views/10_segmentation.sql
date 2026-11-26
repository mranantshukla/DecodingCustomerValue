-- ============================================================================
-- SEGMENTATION VIEWS
-- The customer taxonomy leadership acts on. Each view answers a single
-- "who are the ___ customers and what are they worth?" question.
-- Portable across SQLite 3.25+ and PostgreSQL (CTEs + window functions only).
-- ============================================================================

-- --- Persona scorecard: size, value share, and economics of each persona -----
DROP VIEW IF EXISTS v_persona_scorecard;
CREATE VIEW v_persona_scorecard AS
WITH totals AS (
    SELECT SUM(estimated_clv_proxy) AS total_clv,
           COUNT(*)                 AS total_customers
    FROM customer_features
)
SELECT
    cf.customer_persona,
    COUNT(*)                                              AS customers,
    ROUND(100.0 * COUNT(*) / t.total_customers, 1)        AS pct_of_customers,
    ROUND(AVG(cf.loyalty_score), 3)                       AS avg_loyalty,
    ROUND(AVG(cf.promo_dependency_score), 3)              AS avg_promo_dependency,
    ROUND(AVG(cf.estimated_clv_proxy), 2)                 AS avg_clv,
    ROUND(SUM(cf.estimated_clv_proxy), 2)                 AS total_clv,
    ROUND(100.0 * SUM(cf.estimated_clv_proxy) / t.total_clv, 1) AS pct_of_clv,
    ROUND(AVG(cf.satisfaction_flag), 3)
                                                          AS pct_satisfied
FROM customer_features cf
CROSS JOIN totals t
GROUP BY cf.customer_persona, t.total_customers, t.total_clv
ORDER BY total_clv DESC;

-- --- Loyal customers: high loyalty, low promo reliance ------------------------
DROP VIEW IF EXISTS v_loyal_customers;
CREATE VIEW v_loyal_customers AS
SELECT customer_id, location, category, loyalty_score, loyalty_tier,
       estimated_clv_proxy, promo_dependency_score, review_rating
FROM customer_features
WHERE loyalty_tier IN ('L4-Committed', 'L5-Champion')
  AND promo_dependency_score < 0.5
ORDER BY loyalty_score DESC;

-- --- Promo hunters: high promo dependency, below-median value -----------------
DROP VIEW IF EXISTS v_promo_hunters;
CREATE VIEW v_promo_hunters AS
WITH med AS (SELECT AVG(estimated_clv_proxy) AS m FROM customer_features)
SELECT cf.customer_id, cf.location, cf.category, cf.promo_dependency_score,
       cf.promo_reliance_tier, cf.estimated_clv_proxy, cf.loyalty_score
FROM customer_features cf, med
WHERE cf.promo_reliance_tier = 'Discount-Dependent'
  AND cf.estimated_clv_proxy < med.m
ORDER BY cf.promo_dependency_score DESC;

-- --- Premium customers: top-tier value AND satisfied --------------------------
DROP VIEW IF EXISTS v_premium_customers;
CREATE VIEW v_premium_customers AS
SELECT customer_id, location, category, estimated_clv_proxy,
       revenue_contribution_tier, loyalty_score, review_rating, customer_persona
FROM customer_features
WHERE premium_customer_flag = 1
ORDER BY estimated_clv_proxy DESC;

-- --- High-risk customers: high value but NOT satisfied (retention danger) -----
DROP VIEW IF EXISTS v_high_risk_customers;
CREATE VIEW v_high_risk_customers AS
SELECT customer_id, location, category, estimated_clv_proxy, loyalty_score,
       review_rating, satisfaction_flag, promo_dependency_score
FROM customer_features
WHERE premium_customer_flag = 1
  AND satisfaction_flag = 0
ORDER BY estimated_clv_proxy DESC;

-- --- High-value low-frequency: big baskets, rare visits (frequency upside) ----
DROP VIEW IF EXISTS v_high_value_low_frequency;
CREATE VIEW v_high_value_low_frequency AS
WITH v AS (SELECT estimated_clv_proxy AS c, NTILE(5) OVER (ORDER BY estimated_clv_proxy) AS vq
           FROM customer_features)
SELECT cf.customer_id, cf.location, cf.category, cf.frequency_of_purchases,
       cf.purchase_amount, cf.estimated_clv_proxy, cf.loyalty_score
FROM customer_features cf
WHERE cf.frequency_of_purchases IN ('Annually', 'Quarterly', 'Every 3 Months')
  AND cf.estimated_clv_proxy >= (SELECT AVG(estimated_clv_proxy) FROM customer_features)
ORDER BY cf.estimated_clv_proxy DESC;
