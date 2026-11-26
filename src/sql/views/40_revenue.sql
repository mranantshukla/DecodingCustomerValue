-- ============================================================================
-- REVENUE VIEWS
-- "How much of our revenue is discount-dependent, and how concentrated is it?"
-- The margin-risk and revenue-concentration backbone for the exec narrative.
-- ============================================================================

-- --- Discounted vs non-discounted revenue split ------------------------------
DROP VIEW IF EXISTS v_revenue_discount_split;
CREATE VIEW v_revenue_discount_split AS
WITH base AS (
    SELECT CASE WHEN discount_applied = 'Yes' THEN 'Discounted' ELSE 'Full Price' END AS revenue_type,
           purchase_amount, estimated_clv_proxy
    FROM customer_features
), tot AS (SELECT SUM(purchase_amount) AS t_amt, SUM(estimated_clv_proxy) AS t_clv FROM base)
SELECT b.revenue_type,
       COUNT(*)                                          AS customers,
       ROUND(SUM(b.purchase_amount),2)                   AS observed_revenue,
       ROUND(100.0 * SUM(b.purchase_amount) / tot.t_amt, 1) AS pct_observed_revenue,
       ROUND(SUM(b.estimated_clv_proxy),2)               AS projected_clv,
       ROUND(100.0 * SUM(b.estimated_clv_proxy) / tot.t_clv, 1) AS pct_projected_clv
FROM base b, tot
GROUP BY b.revenue_type, tot.t_amt, tot.t_clv;

-- --- Revenue concentration: decile contribution (Pareto / 80-20 lens) ---------
DROP VIEW IF EXISTS v_revenue_concentration;
CREATE VIEW v_revenue_concentration AS
WITH ranked AS (
    SELECT customer_id, estimated_clv_proxy,
           NTILE(10) OVER (ORDER BY estimated_clv_proxy DESC) AS value_decile
    FROM customer_features
), tot AS (SELECT SUM(estimated_clv_proxy) AS total_clv FROM customer_features)
SELECT r.value_decile,
       COUNT(*)                                              AS customers,
       ROUND(SUM(r.estimated_clv_proxy),2)                   AS decile_clv,
       ROUND(100.0 * SUM(r.estimated_clv_proxy) / tot.total_clv, 1) AS pct_of_total_clv,
       ROUND(100.0 * SUM(SUM(r.estimated_clv_proxy)) OVER (ORDER BY r.value_decile)
             / tot.total_clv, 1)                             AS cumulative_pct_clv
FROM ranked r, tot
GROUP BY r.value_decile, tot.total_clv
ORDER BY r.value_decile;

-- --- Segment (revenue tier) contribution -------------------------------------
DROP VIEW IF EXISTS v_revenue_tier_contribution;
CREATE VIEW v_revenue_tier_contribution AS
WITH tot AS (SELECT SUM(estimated_clv_proxy) AS total_clv, COUNT(*) AS n FROM customer_features)
SELECT cf.revenue_contribution_tier                          AS tier,
       COUNT(*)                                              AS customers,
       ROUND(100.0 * COUNT(*) / tot.n, 1)                    AS pct_customers,
       ROUND(SUM(cf.estimated_clv_proxy),2)                  AS total_clv,
       ROUND(100.0 * SUM(cf.estimated_clv_proxy) / tot.total_clv, 1) AS pct_clv,
       ROUND(AVG(cf.promo_dependency_score),3)               AS avg_promo_dependency
FROM customer_features cf, tot
GROUP BY cf.revenue_contribution_tier, tot.n, tot.total_clv
ORDER BY total_clv DESC;
