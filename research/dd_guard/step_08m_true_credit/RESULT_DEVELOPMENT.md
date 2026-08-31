# STEP08M — True Credit Spread Confirmation + Structural Breadth

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Gate

| check                         | pass   |
|:------------------------------|:-------|
| mean_maxdd_ge_0p50            | False  |
| p10_ge_0p50                   | False  |
| worst_decile_ge_0             | False  |
| cagr_ge_minus_0p50            | False  |
| annual_maxdd_nonnegative_both | False  |

## Development scorecard

| policy                       | cagr | dd | sh | calmar | p10 | p5 | worstdec | worst | delta_cagr_pp | delta_maxdd_pp | delta_p10_pp | delta_p5_pp | delta_worst_decile_pp | delta_worst_pp | delta_sharpe | delta_calmar |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| TRUE_CREDIT_BREADTH | 17.452491 | -27.104220 | 0.667539 | 0.794678 | -36.869986 | -40.678231 | -42.385456 | -57.507111 | -2.963494 | -0.952164 | -1.056165 | -1.410276 | -1.707536 | -4.400835 | -0.081259 | -0.143885 |
| TRUE_CREDIT_ONLY_ATTRIBUTION | 17.331154 | -26.946846 | 0.665350 | 0.787376 | -36.605138 | -40.654500 | -42.101895 | -57.507111 | -3.084831 | -0.794790 | -0.791318 | -1.386545 | -1.423974 | -4.400835 | -0.083449 | -0.151187 |

## Annual deltas

Primary TRUE_CREDIT_BREADTH:
- 2021: ΔCAGR -4.443599 pp; Δmean MaxDD -1.536941 pp; BIL rate 68.8172%; n=558.
- 2022: ΔCAGR -1.474092 pp; Δmean MaxDD -0.275765 pp; BIL rate 33.0389%; n=566.

## Mechanism

Primary TRUE_CREDIT_BREADTH:
- BIL rate: 50.8007%
- oracle BIL rate: 38.2562%
- oracle hit: 34.6085%
- selected-BIL win rate: 23.2925%
- mean realized utility advantage among selected BIL: -3.8308%
- features: 45

Credit-only attribution:
- BIL rate: 64.6797%
- oracle BIL rate: 38.2562%
- oracle hit: 32.8292%
- selected-BIL win rate: 27.6479%
- mean realized utility advantage among selected BIL: -2.7194%
- features: 36

Primary policy was frozen before replay. Credit-only is attribution-only and cannot be selected post-hoc. No 2023+ OAS, labels, transforms, fit rows or replay observations were used. No post-result tuning.
