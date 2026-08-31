# STEP08A — development result

**Verdict: REJECT_BEFORE_2023_HOLDOUT.**

2023+ holdout opened: **NO**. FUSION1 parity gap: `0.000e+00`.

## 2021–2022 structural frontier

| Variant | ΔCAGR vs FUSION1 | Δmean MaxDD | Δp10 | Δworst-decile | risky wt | defensive wt | gate |
|---|---:|---:|---:|---:|---:|---:|:---:|
| BIL_FILL | +0.007 pp | +0.004 pp | +0.000 pp | -0.000 pp | 98.02% | 1.98% | FAIL |
| LOWCORR_TOP3 | -0.178 pp | -0.042 pp | -0.064 pp | -0.079 pp | 98.02% | 1.98% | FAIL |
| TRIAD_TREND | +0.006 pp | -0.043 pp | +0.000 pp | +0.028 pp | 98.02% | 1.98% | FAIL |
| LOWCORR_TOP3_SHIFT15 | -0.305 pp | -0.075 pp | -0.337 pp | -0.169 pp | 97.59% | 2.41% | FAIL |

## Interpretation
The test changes portfolio composition rather than attempting another crash classifier. Residual FUSION1 cash is invested in frozen defensive assets; the strongest fixed variant also transfers 15 pp of risky sleeve into the same defensive sleeve during stress.

No lookback, asset universe, score coefficient, top-k, or transfer size is retuned after these results.