# STEP08L — New Information BIL/STAY Gate
Date: 2026-08-31

## Purpose
Test whether genuinely additional information can solve the regime-instability of STEP08J/K without changing the action space or optimizing thresholds.

## Frozen action and engine
- Trigger/decision set: exactly the q95 events inherited from STEP08J/K.
- Actions: STAY in FUSION1 or BIL for the same frozen 10-session action window.
- Costs and FUSION1 mechanics unchanged.
- Decision rule: BIL iff predicted `utility(BIL)-utility(STAY) > 0`; otherwise STAY.
- No 2023+ data may be used.

## Frozen estimator
Exactly the STEP08K walk-forward estimator:
`SimpleImputer(median) + HistGradientBoostingRegressor(max_iter=180, learning_rate=.04, max_leaf_nodes=7, min_samples_leaf=35, l2_regularization=8, random_state=20260824)`.
Training uses date multiplicity weights and exponential recency weighting with half-life 365 calendar days. Fit for 2021 uses 2017-2020. Fit for 2022 adds fully matured 2021 rows. No hyperparameter search.

## Existing base features
The 18 STEP08J/K state+BIL features remain unchanged.

## New-information blocks
### VOL_FINCOND
Causal levels/changes derived from frozen historical raw series:
- VIX, VIX9D, VIX3M, VVIX, SKEW
- VIX9D/VIX and VIX/VIX3M term-structure ratios
- VIX 1/5/21-session changes
- VVIX/VIX ratio
- NFCI and 4-week change
- STLFSI4 and 4-week change

### STRUCTURAL_BREADTH
Derived from the frozen 150-ETF close matrix using information through the decision date only:
- fraction above MA21, MA63, MA126
- fraction with positive 21d and 63d return
- fraction with 5d return below -5%
- cross-sectional 21d return dispersion
- breadth 5d change for MA63 participation

### CREDIT_PROXY
Derived from frozen HYG and LQD closes:
- HYG/LQD relative return 5/21/63d
- HYG drawdown 21/63d
- HYG 21d volatility
- HYG minus LQD 21d volatility-adjusted return

## Policies
Primary, promotion-eligible development policy: `ALL_NEW_INFO` = base + all three blocks.
Attribution-only policies (not eligible for post-hoc promotion): `VOL_FINCOND_ONLY`, `BREADTH_ONLY`, `CREDIT_ONLY`.
No policy will be selected based on 2021-2022 results.

## Development gate
Same strong DD-first gate:
- delta CAGR >= -0.50 pp vs FUSION1
- delta mean MaxDD >= +0.50 pp
- delta p10 MaxDD >= +0.50 pp
- delta worst-decile MaxDD >= 0
- delta mean MaxDD >= 0 separately in 2021 and 2022
Only `ALL_NEW_INFO` can qualify for a future one-shot 2023+ holdout.

## Stop rule
If `ALL_NEW_INFO` fails, do not tune feature windows, thresholds, HGB parameters, or recency half-life on 2021-2022. Individual-block results may identify where information exists, but require a separately preregistered follow-up before any holdout.
