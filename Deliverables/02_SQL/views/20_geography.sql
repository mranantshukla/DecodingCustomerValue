-- ============================================================================
-- GEOGRAPHY VIEWS
-- "Where is demand healthy vs propped up by discounts, and where should we
-- invest?" Region-level economics for capital-allocation decisions.
-- ============================================================================

-- --- Master region scorecard -------------------------------------------------
DROP VIEW IF EXISTS v_region_scorecard;
CREATE VIEW v_region_scorecard AS
SELECT
    location,
    COUNT(*)                                         AS customers,
    ROUND(AVG(organic_demand_score), 3)              AS organic_demand,
    ROUND(AVG(promo_dependency_score), 3)            AS promo_dependency,
    ROUND(AVG(region_quality_index), 3)              AS region_quality,
    ROUND(AVG(loyalty_score), 3)                     AS avg_loyalty,
    ROUND(AVG(review_rating), 2)                      AS avg_satisfaction,
    ROUND(SUM(estimated_clv_proxy), 2)               AS total_clv,
    ROUND(AVG(estimated_clv_proxy), 2)               AS avg_clv,
    ROUND(AVG(promo_sensitivity_geo), 4)             AS promo_sensitivity
FROM customer_features
GROUP BY location
ORDER BY region_quality DESC;

-- --- Organic-demand regions: healthy markets to double down on ----------------
-- Top tercile of organic demand AND above-median region quality.
DROP VIEW IF EXISTS v_organic_demand_regions;
CREATE VIEW v_organic_demand_regions AS
WITH r AS (
    SELECT location,
           AVG(organic_demand_score) AS organic,
           AVG(region_quality_index) AS quality,
           SUM(estimated_clv_proxy)  AS total_clv,
           COUNT(*)                  AS customers
    FROM customer_features GROUP BY location
),
b AS (SELECT AVG(quality) AS med_quality FROM r)
SELECT r.location, ROUND(r.organic,3) AS organic_demand,
       ROUND(r.quality,3) AS region_quality, ROUND(r.total_clv,2) AS total_clv, r.customers
FROM r, b
WHERE r.organic >= 0.55 AND r.quality >= b.med_quality
ORDER BY r.organic DESC;

-- --- High-margin regions: high value with low discount leakage ----------------
DROP VIEW IF EXISTS v_high_margin_regions;
CREATE VIEW v_high_margin_regions AS
SELECT location,
       COUNT(*)                                AS customers,
       ROUND(AVG(estimated_clv_proxy),2)       AS avg_clv,
       ROUND(AVG(promo_dependency_score),3)    AS promo_dependency,
       ROUND(AVG(estimated_clv_proxy) * (1 - AVG(promo_dependency_score)), 2)
                                               AS margin_adjusted_clv
FROM customer_features
GROUP BY location
ORDER BY margin_adjusted_clv DESC;

-- --- Promo-heavy regions: discount-reliant markets (margin risk) --------------
DROP VIEW IF EXISTS v_promo_heavy_regions;
CREATE VIEW v_promo_heavy_regions AS
SELECT location,
       COUNT(*)                                AS customers,
       ROUND(AVG(promo_dependency_score),3)    AS promo_dependency,
       ROUND(AVG(organic_demand_score),3)      AS organic_demand,
       ROUND(AVG(promo_sensitivity_geo),4)     AS promo_sensitivity,
       ROUND(SUM(estimated_clv_proxy),2)       AS total_clv
FROM customer_features
GROUP BY location
HAVING AVG(promo_dependency_score) > 0.45
ORDER BY promo_dependency DESC;
