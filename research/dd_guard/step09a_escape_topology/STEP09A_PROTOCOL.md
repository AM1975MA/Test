# STEP09A — Escape Topology Audit
Date: 2026-09-01

## Objective
Test whether causal cross-sectional market geometry at frozen FUSION1 stress alerts separates three economically distinct full-episode actions: STAY, ROTATE, BIL.
This is an information audit only. No 2023+ data are opened and no candidate is promoted from STEP09A.

## Frozen trigger and sample
- Use exact causal OOF FUSION1 alerts from the frozen STEP06J engine, 2018-2022.
- Pre-2021 (2018-2020) is model-development/training and temporal robustness only.
- 2021-2022 is forward development. 2023+ is sealed.
- Effective evidence unit is calendar episode/date. Every trigger date receives total weight 1, divided across baskets on that date.

## Full-episode target
For each FUSION1 alert at close t:
- action begins at t+1, the same causal boundary as the FUSION1 overlay;
- episode endpoint is the first session on which exact FUSION1 equity recovers the pre-trigger high-water mark, capped at 126 sessions;
- STAY = exact FUSION1 continuation;
- BIL = 100% BIL over the same episode, 10 bp one-way at entry and exit;
- ROTATE = ex-post best non-BIL ETF among the basket's frozen 24 members over the same episode, same costs;
- utility = terminal return + 0.5 * local minimum drawdown, but terminal return, trough, duration and area-under-water are all preserved for diagnostics.
- primary class is argmax(STAY utility, BIL utility, best-ROTATE utility). No post-hoc margin threshold.

## Primary causal information: ESCAPE_GEOMETRY
Computed only from closes available at or before trigger t.
Basket-local and broad-150 features are limited to:
1. mean pairwise correlation, 21d and 63d;
2. first correlation-eigenvalue share, 21d and 63d;
3. correlation/eigenvalue compression (21d minus 63d);
4. downside correlation on recent negative-market sessions;
5. cross-sectional cumulative-return dispersion 1/3/5/10/21d;
6. fraction of basket members outperforming the current frozen HGB basket path over 1/3/5/10/21d;
7. fraction positive over 5/21/63d;
8. fraction above MA63/126/252;
9. fraction within 5% of trailing 63d high;
10. broad-150 analogues of correlation/eigenvalue concentration, dispersion and trend breadth.
No future information and no fitted feature weights enter construction.

## Secondary confirmation block
`ESCAPE_GEOMETRY_PLUS_CREDIT` may add the already frozen true HY OAS / IG OAS / HY-IG variables from STEP08M. It is attribution only. It cannot override a failed geometry-primary verdict.

## Fixed models
Primary: multinomial LogisticRegression, C=0.1, StandardScaler, median imputation, max_iter=3000.
Secondary nonlinear ceiling diagnostic: shallow HistGradientBoostingClassifier, learning_rate=0.05, max_leaf_nodes=7, max_iter=150, l2_regularization=1.0.
No hyperparameter search.

## Validation
- temporal robustness inside pre-2021: leave-one-year-out for 2018, 2019, 2020 when all required classes are present;
- forward fit on all 2018-2020 and evaluate 2021-2022 combined and by year;
- sample weights are date weights (one market date = weight 1).
Metrics: weighted balanced accuracy, weighted macro F1, one-vs-rest weighted AUC by class and macro mean AUC, confusion/action-rate diagnostics.

## Primary information gate
Geometry is considered sufficiently informative to justify STEP09B only if the frozen primary logistic model satisfies all:
- combined 2021-2022 weighted balanced accuracy >= 0.45;
- combined weighted macro mean OVR AUC >= 0.60;
- ROTATE OVR AUC >= 0.60;
- 2021 weighted balanced accuracy >= 0.40;
- median valid pre-2021 LOO-year macro OVR AUC >= 0.58;
- no sign/identity collapse in which one predicted class exceeds 95% of forward weighted decisions.
2022 class-specific gates are diagnostic only because the FUSION1 alert count is very small.

If primary geometry fails, do not tune geometry thresholds or models. The next admissible information source is genuinely orthogonal flow/positioning/funding plumbing.
