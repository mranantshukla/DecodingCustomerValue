"""Customer segmentation: rule-based personas + an unsupervised behavioural overlay.

Two complementary lenses, each chosen deliberately:

1. **Rule-based personas** (``customer_persona``). Mutually-exclusive business
   segments defined by transparent rules on the engineered features. These are
   what go into the deck — a CMO can act on "Promo-Dependent High-Value" without
   knowing what a cluster is. Priority order resolves overlaps.

2. **KMeans behavioural cluster** (``behaviour_cluster``). An unsupervised overlay
   on a small set of standardised behavioural features. We use it ONLY to discover
   structure we might have missed and to validate the rule-based personas — not as
   the primary segmentation, because clusters are not directly actionable and
   shift run-to-run. This is the restrained use of ML the brief asks for.
"""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from config.settings import get_settings
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# Features fed to KMeans — all on a comparable [0,1]-ish footing after scaling.
CLUSTER_FEATURES = [
    "loyalty_score",
    "promo_dependency_score",
    "estimated_clv_proxy",
    "repeat_purchase_intensity",
    "satisfaction_norm",
]


def assign_personas(df: pd.DataFrame) -> pd.DataFrame:
    """Assign one mutually-exclusive business persona per customer.

    Priority order (first match wins) is chosen so the most decision-relevant
    label dominates: we would rather know a customer is a discount-reliant
    high-value account than that they are merely "premium".
    """
    df = df.copy()
    s = get_settings().thresholds

    loyal = df["loyalty_score"] >= df["loyalty_score"].quantile(0.70)
    premium = df["premium_customer_flag"]
    promo_dep = df["promo_dependency_score"] >= s.promo_dependent_threshold
    satisfied = df["satisfaction_flag"]
    low_freq = df["freq_rank_norm"] <= 0.34
    high_value = df["estimated_clv_proxy"] >= df["estimated_clv_proxy"].quantile(
        s.high_value_percentile
    )

    persona = pd.Series("Standard", index=df.index, dtype="object")
    # Lowest priority first; later assignments overwrite.
    persona[low_freq & high_value] = "High-Value Low-Frequency"
    persona[premium & ~satisfied] = "At-Risk Premium"
    persona[promo_dep & high_value] = "Promo-Dependent High-Value"
    persona[promo_dep & ~high_value] = "Promo Hunter"
    persona[premium & satisfied] = "Premium Loyalist"
    persona[loyal & ~promo_dep & satisfied] = "Loyal Full-Price"
    df["customer_persona"] = persona
    return df


def assign_behaviour_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Add a KMeans behavioural cluster label (validation overlay, not primary)."""
    df = df.copy()
    settings = get_settings()
    feats = [c for c in CLUSTER_FEATURES if c in df.columns]
    scaled = StandardScaler().fit_transform(df[feats].fillna(df[feats].median()))
    km = KMeans(n_clusters=settings.n_segments, random_state=settings.random_seed, n_init=10)
    labels = km.fit_predict(scaled)

    # Order clusters by mean CLV so labels are stable and interpretable
    # (cluster 0 = lowest value ... n-1 = highest), regardless of KMeans init.
    order = (
        pd.Series(df["estimated_clv_proxy"].values)
        .groupby(labels)
        .mean()
        .sort_values()
        .index.tolist()
    )
    remap = {old: new for new, old in enumerate(order)}
    df["behaviour_cluster"] = [f"C{remap[label]}" for label in labels]
    log.info("KMeans assigned %d behavioural clusters", settings.n_segments)
    return df


def segment_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Full segmentation: personas + behavioural clusters."""
    return df.pipe(assign_personas).pipe(assign_behaviour_clusters)


def persona_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Executive roll-up by persona: size, value share, loyalty, promo reliance."""
    total_clv = df["estimated_clv_proxy"].sum()
    g = df.groupby("customer_persona").agg(
        customers=("customer_id", "count"),
        avg_loyalty=("loyalty_score", "mean"),
        avg_clv=("estimated_clv_proxy", "mean"),
        total_clv=("estimated_clv_proxy", "sum"),
        avg_promo_dependency=("promo_dependency_score", "mean"),
        pct_satisfied=("satisfaction_flag", "mean"),
    )
    g["clv_share"] = g["total_clv"] / total_clv
    g["customer_share"] = g["customers"] / len(df)
    return g.sort_values("total_clv", ascending=False).round(4).reset_index()
