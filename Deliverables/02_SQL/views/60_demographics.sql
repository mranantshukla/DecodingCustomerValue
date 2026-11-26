-- ============================================================================
-- DEMOGRAPHICS VIEWS
-- Closes the "demographics" half of PDF Key Question 3 — "Which geographies
-- AND DEMOGRAPHICS are commercially underlevered?". The geography half already
-- has v_region_scorecard et al.; this file adds an age-band × gender lens
-- so under-served demographic pockets become visible.
--
-- Honest note: gender is structurally confounded with discount/subscription in
-- the source data (every discounted customer is male). Promo-related metrics
-- in this view are therefore reported alongside customer count so the confound
-- stays visible; we deliberately do NOT compute promo-by-gender as a primary
-- targeting signal. See docs/LIMITATIONS_AND_ETHICS.md.
-- ============================================================================

DROP VIEW IF EXISTS v_demographic_opportunity;
CREATE VIEW v_demographic_opportunity AS
WITH banded AS (
    SELECT
        customer_id,
        gender,
        CASE
            WHEN age < 25 THEN '18-24'
            WHEN age < 35 THEN '25-34'
            WHEN age < 45 THEN '35-44'
            WHEN age < 55 THEN '45-54'
            WHEN age < 65 THEN '55-64'
            ELSE '65+'
        END AS age_band,
        estimated_clv_proxy,
        loyalty_score,
        promo_dependency_score,
        satisfaction_flag,
        premium_customer_flag
    FROM customer_features
)
SELECT
    age_band,
    gender,
    COUNT(*)                                          AS customers,
    ROUND(AVG(estimated_clv_proxy), 2)                AS avg_clv,
    ROUND(SUM(estimated_clv_proxy), 2)                AS total_clv,
    ROUND(AVG(loyalty_score), 3)                      AS avg_loyalty,
    ROUND(AVG(promo_dependency_score), 3)             AS avg_promo_dependency,
    ROUND(100.0 * AVG(satisfaction_flag), 1)          AS pct_satisfied,
    ROUND(100.0 * AVG(premium_customer_flag), 1)      AS pct_premium
FROM banded
GROUP BY age_band, gender
ORDER BY total_clv DESC;
