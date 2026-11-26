-- ============================================================================
-- Decoding Customer Value — analytical schema
--
-- The pipeline materialises one analytics-ready table, `customer_features`
-- (one row per customer, raw dimensions + engineered features + segments).
-- This file is the canonical DDL: it documents the contract and creates the
-- indexes the analytical views rely on. It is written to run on BOTH SQLite
-- (default, zero-setup) and PostgreSQL (production target).
--
-- Note on types: the pipeline loads the table via pandas, so `CREATE TABLE IF
-- NOT EXISTS` is typically a no-op at runtime and serves as the human-readable
-- contract; the `CREATE INDEX IF NOT EXISTS` statements are what execute.
-- BOOLEAN is stored as 0/1 by SQLite and as true booleans by Postgres — the
-- views treat the flags numerically so they behave identically on both.
-- ============================================================================

CREATE TABLE IF NOT EXISTS customer_features (
    customer_id                 INTEGER PRIMARY KEY,
    -- raw dimensions
    age                         INTEGER,
    gender                      TEXT,
    item_purchased              TEXT,
    category                    TEXT,
    purchase_amount             REAL,
    location                    TEXT,
    size                        TEXT,
    color                       TEXT,
    season                      TEXT,
    review_rating               REAL,
    subscription_status         TEXT,
    shipping_type               TEXT,
    discount_applied            TEXT,
    previous_purchases          INTEGER,
    payment_method              TEXT,
    frequency_of_purchases      TEXT,
    -- engineered: loyalty
    loyalty_score               REAL,   -- canonical (winning definition)
    loyalty_score_v1            REAL,
    loyalty_score_v2            REAL,
    loyalty_tier                TEXT,
    loyalty_confidence_index    REAL,
    repeat_purchase_intensity   REAL,
    brand_affinity_score        REAL,
    -- engineered: promotion
    promo_dependency_score      REAL,
    non_discount_purchase_ratio REAL,
    discount_elasticity_proxy   REAL,
    promo_reliance_tier         TEXT,
    -- engineered: value (decomposed so loyalty's role is auditable)
    annual_value                REAL,    -- spend * cadence (loyalty-free)
    margin_factor               REAL,    -- 1 - margin_haircut * discount_flag
    economic_value_proxy        REAL,    -- annual_value * margin_factor  (loyalty-FREE)
    expected_tenure_years       REAL,    -- 1 + 4 * loyalty_v2  (loyalty enters HERE)
    estimated_clv_proxy         REAL,    -- economic_value_proxy * expected_tenure_years
    revenue_contribution_tier   TEXT,
    high_value_probability      REAL,
    premium_customer_flag       BOOLEAN,
    -- engineered: behavioural
    satisfaction_flag           BOOLEAN,
    category_breadth_est        REAL,
    shipping_urgency_index      REAL,
    payment_repeat_index        REAL,    -- empirical (was payment_stability_score)
    seasonal_consistency_score  REAL,
    -- engineered: geography
    organic_demand_score        REAL,
    region_quality_index        REAL,
    promo_sensitivity_geo       REAL,
    -- segmentation
    customer_persona            TEXT,
    behaviour_cluster           TEXT
);

-- Indexes for the grouping/filtering columns the views hit most.
CREATE INDEX IF NOT EXISTS idx_cf_location  ON customer_features (location);
CREATE INDEX IF NOT EXISTS idx_cf_category  ON customer_features (category);
CREATE INDEX IF NOT EXISTS idx_cf_persona   ON customer_features (customer_persona);
CREATE INDEX IF NOT EXISTS idx_cf_rev_tier  ON customer_features (revenue_contribution_tier);
CREATE INDEX IF NOT EXISTS idx_cf_promotier ON customer_features (promo_reliance_tier);
