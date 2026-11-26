-- ============================================================================
-- PRODUCT / CATEGORY VIEWS
-- "Which categories build retention vs merely transact?" Product mix through a
-- loyalty and value lens, not just a revenue lens.
-- ============================================================================

-- --- Category scorecard ------------------------------------------------------
DROP VIEW IF EXISTS v_category_scorecard;
CREATE VIEW v_category_scorecard AS
SELECT
    category,
    COUNT(*)                                 AS purchases,
    ROUND(AVG(purchase_amount),2)            AS avg_basket,
    ROUND(AVG(loyalty_score),3)              AS avg_loyalty,
    ROUND(AVG(review_rating),2)              AS avg_rating,
    ROUND(AVG(promo_dependency_score),3)     AS avg_promo_dependency,
    ROUND(AVG(discount_elasticity_proxy),4)  AS discount_elasticity,
    ROUND(SUM(estimated_clv_proxy),2)        AS total_clv
FROM customer_features
GROUP BY category
ORDER BY total_clv DESC;

-- --- Retention-driving categories: high loyalty AND high satisfaction ---------
DROP VIEW IF EXISTS v_retention_driving_categories;
CREATE VIEW v_retention_driving_categories AS
WITH c AS (
    SELECT category,
           AVG(loyalty_score)  AS loy,
           AVG(review_rating)  AS sat,
           AVG(repeat_purchase_intensity) AS rpi,
           COUNT(*) AS n
    FROM customer_features GROUP BY category
)
SELECT category, ROUND(loy,3) AS avg_loyalty, ROUND(sat,2) AS avg_rating,
       ROUND(rpi,3) AS repeat_intensity, n AS purchases,
       RANK() OVER (ORDER BY loy DESC) AS loyalty_rank
FROM c
ORDER BY avg_loyalty DESC;

-- --- Entry-point categories: where low-history customers start ----------------
-- High share of customers with below-median previous_purchases => acquisition doors.
DROP VIEW IF EXISTS v_entry_point_categories;
CREATE VIEW v_entry_point_categories AS
WITH m AS (SELECT AVG(previous_purchases) AS med FROM customer_features)
SELECT cf.category,
       COUNT(*)                                                         AS customers,
       SUM(CASE WHEN cf.previous_purchases < m.med THEN 1 ELSE 0 END)   AS new_ish_customers,
       ROUND(100.0 * SUM(CASE WHEN cf.previous_purchases < m.med THEN 1 ELSE 0 END) / COUNT(*), 1)
                                                                        AS pct_low_history,
       ROUND(AVG(cf.purchase_amount),2)                                 AS avg_basket
FROM customer_features cf, m
GROUP BY cf.category
ORDER BY pct_low_history DESC;

-- --- High-loyalty products (item level) --------------------------------------
DROP VIEW IF EXISTS v_high_loyalty_products;
CREATE VIEW v_high_loyalty_products AS
SELECT item_purchased, category,
       COUNT(*)                       AS purchases,
       ROUND(AVG(loyalty_score),3)    AS avg_loyalty,
       ROUND(AVG(review_rating),2)    AS avg_rating,
       ROUND(AVG(estimated_clv_proxy),2) AS avg_clv
FROM customer_features
GROUP BY item_purchased, category
HAVING COUNT(*) >= 20
ORDER BY avg_loyalty DESC;
