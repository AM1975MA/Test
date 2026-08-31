# STEP09A2 — Robust Escape Availability Target Audit
Date: 2026-09-01

## Why this is separate from STEP09A
STEP09A is closed and rejected unchanged. Its oracle class was defined by the single best ex-post ETF among 24, which mechanically made ROTATE dominate 88% of pre-2021 episodes. STEP09A2 does not retune that test. It changes the scientific target from "did one lucky winner exist?" to "did a broad, economically usable escape set exist?".

## Frozen sample, episode and features
Identical to STEP09A:
- exact causal OOF FUSION1 alerts, 2018-2022;
- full episode from t+1 to FUSION1 recovery to pre-trigger HWM, cap 126 sessions;
- date weighting, one trigger date total weight = 1;
- the exact frozen ESCAPE_GEOMETRY feature panel from STEP09A is reused without modification;
- 2023+ sealed.

## Robust three-state target
For every episode, calculate full-episode utility of each available non-BIL ETF in the frozen 24-member basket with the same 10 bp one-way costs.
Let `escape_fraction` be the fraction of those ETFs whose full-episode utility exceeds exact FUSION1 STAY utility.

Classes are fixed before model execution:
1. `ROTATE` if `escape_fraction >= 0.25` (at least one quarter of the basket provides an ex-post better escape route);
2. else `BIL` if BIL full-episode utility > STAY utility;
3. else `STAY`.

The 25% rule is a structural quartile definition, not selected from development performance. No alternative fractions will be searched in STEP09A2.

## Fixed model and validation
Identical to STEP09A primary:
- median imputation -> StandardScaler -> multinomial LogisticRegression(C=0.1, max_iter=3000);
- secondary shallow HGB only as nonlinear ceiling diagnostic;
- train/development: 2018-2020, LOO-year robustness;
- forward: 2021-2022 combined and by year;
- date weights.

## Information gate
Primary geometry LOGIT must satisfy all:
- forward 2021-2022 balanced accuracy >= 0.45;
- forward macro OVR AUC >= 0.60;
- ROTATE AUC >= 0.60;
- BIL AUC >= 0.60 when BIL is present;
- 2021 balanced accuracy >= 0.40;
- median valid pre-2021 LOO macro AUC >= 0.58;
- no predicted class >95% of forward date weight.

If this fails, market geometry from standard prices does not separate the robust three-state target sufficiently; proceed to genuinely orthogonal funding/flow/positioning information rather than threshold tuning.
