# STEP08C — Protective Rotation / Destination Selection

**Final verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## C0 oracle ceiling
The economic opportunity is very large when the correct destination is known ex post.

| Policy | ΔCAGR vs FUSION1 | Δmean MaxDD | Δp10 | Δworst-decile |
|---|---:|---:|---:|---:|
| BIL_ONLY | -3.657 pp | -0.774 pp | -0.836 pp | -1.854 pp |
| ORACLE_FORCE_ROTATE | +18.266 pp | +3.610 pp | +6.613 pp | +5.492 pp |
| ORACLE_STAY_ALLOWED | +18.670 pp | +3.653 pp | +6.732 pp | +5.601 pp |

Both oracle rotation variants pass the preregistered C0 continuation gate, so destination opportunity is not the limiting factor. The full-150 oracle is explicitly an upper bound, not a deployable strategy.

## C1 frozen causal selector
`SimpleImputer -> StandardScaler -> Ridge(alpha=10)` was trained only on fully matured pre-2021 labels. The validation trigger is the frozen STEP07A q95 high-risk bucket. No selector parameter was tuned on 2021-2022.

- ΔCAGR vs FUSION1: **-2.862 pp**
- Δmean MaxDD: **-1.549 pp**
- Δp10 MaxDD: **-2.423 pp**
- Δworst-decile: **-3.463 pp**
- BIL fallback rate: **35.2%**
- Exact oracle-destination hit rate: **4.45%**
- Event-level causal choice beats BIL utility: **29.4%**
- Event-level causal choice beats exact FUSION1 continuation utility: **37.7%**

2021 is the decisive failure: ΔCAGR -6.076 pp and Δmean MaxDD -2.373 pp. 2022 is much less hostile, but mean MaxDD still does not improve.

## Interpretation
STEP08C separates two questions cleanly. **Where to rotate has a very high oracle ceiling**, but the low-dimensional causal price/state model cannot identify the destination reliably enough. Conversely, simply treating BIL as the automatic destination when q95 fires is not safe: BIL_ONLY itself worsens the 2021-2022 frontier because FUSION1 is already defensive and many high-risk states rebound quickly.

The correct conclusion is therefore not that protective rotation is impossible. It is that the destination selector must inherit a stronger source of cross-sectional alpha than the raw price/risk features used here. Per the stop rule, STEP08C is closed without tuning q95, horizon, Ridge alpha, threshold or feature weights.
