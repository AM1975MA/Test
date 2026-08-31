# STEP08E — basket-local Titanium protective rotation

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022

| policy | delta CAGR pp | delta mean MaxDD pp | delta p10 pp | delta worst-decile pp |
|---|---:|---:|---:|---:|
| ORACLE_LOCAL_FORCE | +8.374290 | +2.892492 | +4.528161 | +3.566782 |
| ORACLE_LOCAL_STAY_ALLOWED | +9.156281 | +3.046643 | +4.940783 | +3.938691 |
| TIT_R_BASKET_LOCAL_V2 | +0.476254 | +0.415965 | +0.179810 | -0.525883 |

## Annual deltas — causal policy

| year | delta CAGR pp | delta mean MaxDD pp | delta p10 pp | delta worst-decile pp |
|---|---:|---:|---:|---:|
| 2021 | -0.706933 | -0.334021 | -0.619764 | -1.668140 |
| 2022 | +1.665011 | +0.795400 | +1.150795 | +1.134038 |

## Mechanism
- 1,124 frozen q95 decisions.
- BIL fallback: 0.00%.
- Native V2 100% top-1 concentration rate conditional on non-BIL: 4.63%.
- Causal event choice beats exact FUSION1 continuation utility: 53.83%.
- Basket-local oracle equals full-150 oracle: 11.30%.
- Basket-local oracle beats FUSION1 event utility: 86.65%.
- Authentic TIT_R score age mean / median / max: 14.2 / 13 / 32 calendar days.

No post-hoc tuning was performed. The development gate fails because mean MaxDD and p10 improvement are below +0.50 pp, worst-decile worsens, and 2021 mean MaxDD is negative. 2023+ was not opened.
