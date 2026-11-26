# Loyalty Definition Framework — A vs B

Two loyalty definitions were engineered and evaluated against five commercial criteria. The winner is selected by weighted total score.

> **Validation target:** revenue-alignment and segment-separation are computed against `economic_value_proxy` (current-period margin-adjusted value, **loyalty-free**), not against `estimated_clv_proxy`. CLV contains a loyalty-derived tenure term, so using it as the target would be partly self-correlation. The orthogonal target gives a clean validation.

## Criteria weights

| Criterion | Weight | Why it matters |
|---|---:|---|
| Revenue alignment | 30% | Loyalty must track customer value to be useful for targeting. |
| Margin alignment | 25% | Distinguishes profitable loyalty from discount-driven habit. |
| Segment separation | 20% | A good metric discriminates high- from low-value customers. |
| Robustness | 15% | Conclusions must not flip when weights are nudged ±20%. |
| Explainability | 10% | Leadership must be able to understand and defend it. |

## Scores

| Definition | Revenue | Margin | Separation | Robustness | Explainability | **Total** |
|---|---:|---:|---:|---:|---:|---:|
| Definition A — Volume-led | 0.337 | 0.330 | 1.000 | 0.952 | 1.000 | **0.627** |
| Definition B — Margin-aware | 0.425 | 0.502 | 1.000 | 0.855 | 0.850 | **0.666** |

## Selected definition: **Definition B — Margin-aware** (`loyalty_score_v2`)

**Definition B (margin-aware) is adopted as the canonical loyalty metric.** It aligns more strongly with customer value (0.425 vs 0.337) and, critically, with margin (0.502 vs 0.330), because it explicitly rewards full-price, satisfied, repeat behaviour. Definition A's blind spot is fatal for this engagement: it labels discount-dependent buyers as loyal, which would send retention budget to exactly the customers eroding margin. The modest loss in explainability (B has two more weights) is an acceptable price for a metric that distinguishes *profitable* loyalty from *habitual* discount usage — the central question the brand asked.

