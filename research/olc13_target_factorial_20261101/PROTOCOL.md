# OLC13 — controlled target factorial

2026-11-01. User approved trying the four target variants described in TARGET_SEMANTICS_AUDIT_20261101.md. Registered before any new target fits or outcomes. Research only in AM1975MA/Test; no main or Etf_trader modification and no live promotion.

Parent: OLC12 commit 8709a652eaa5100e1348c738f34abc05b3709901. Source archives: OLC11_Selezione_Checkpoint_20261101.zip and OLC12_Integrazione_Checkpoint_20261101.zip. Preserve immutable input checksums and inherited environment.

## Question and fixed variants
Target Y=sum_h w_h*r_h**alpha, h=(21,42,63), same original cumulative cross-sectional percentile labels.
- ORIGINAL_P15: w=(.45,.35,.20), alpha=1.5; matched OLC11 control.
- EXP42_P15: w_h=2**(-h/42)/sum_j 2**(-j/42), alpha=1.5.
- ORIGINAL_P10: original weights, alpha=1.0.
- EXP42_P10: exponential weights with half-life42 sessions, alpha=1.0.
No half-life sweep, additional alpha, market-specific selection or rescue variant. This phase does not implement incremental targets; it measures incremental outcomes as common diagnostics.

## Training isolation
Use OLC11 prepared annual inputs2019–2026, USA149 and EU165, identical ordered Hybrid42 matrices, prediction keys, median imputation and whole-group maturity-safe training rows. Never remove live candidates because their future outcome is missing. All variants use exit63 group availability. Labels joined one-to-one to stored train keys; original target must reproduce y. The source universe names are maximum universes, not an assertion that every historical date contains every ticker.

Model families: original ExtraTreesRegressor and XGBRegressor with the exact OLC11 hyperparameters, seeds101/211/307, n_jobs1 per fit. No classifier or ranking-objective changes in this factorial. Reuse authenticated OLC11 original predictions; first refit both original regressors in2022 in both markets, seed101 (4 parity fits). Three new targets x2 learners x8 years x3 seeds x2 markets=288 new fits. Save models, imputers, predictions, parameter/input/code hashes, versions and completion checkpoints. Average raw predictions across the three seeds before cross-sectional percentile fusion; keep seed diagnostics.

## Common endpoints, not target-specific victories
Primary native comparison: MEAN3, CURRENT .6*rank(ET)+.4*rank(XGB), signal dates2021–2024 with each outcome fully mature before2025-01-01. Keep OLC11 evaluation-date rules and strict full candidate-group completeness. Secondary periods2025,2026_PARTIAL and ALL_ACTIVE to2026-07-01, all explicitly retrospective and incomplete where appropriate.

Evaluate every variant against unchanged outcomes: original target NDCG@2/IC and original top/bottom-quintile events; Top2 forward return/excess/regret at21/42/63; incremental returns21–42 and42–63 derived as (1+R_long)/(1+R_short)-1; negative/bottom-quintile selections; tie-aware Top2 selection; choice agreement and per-seed stability. Include a common full63-maturity sample across horizons for clean horizon comparisons. Label geometry/correlation and self-target MSE are diagnostic only, not evidence of economic superiority. No calibration comparisons for different events.

Stage diagnostics CURRENT, SMOOTH and FUSION preserve OLC11 .6/.4 learner weights, .4/.3/.3 memory, power1.1 and .475 Return + .525 Hybrid. Return125 with corrected RSI remains exactly frozen. Authenticate control composition against OLC12 MATCHED_REG.

## Economic replay (unchanged integration)
After input/parity and label tests pass, replay all four targets through the unchanged OLC12 portable engine with fixed allocation/risk/stop/V6 rules. USA and EU; IMMEDIATE/DELAY3/PHASE5; costs .001/.003:48 paths. Additional predeclared IMMEDIATE lagged-systemic-input sensitivity at both costs:16 paths. Require exact equality of the12 original main paths against OLC12 MATCHED_REG. Independent equity/accounting reconstruction and end-point statistics. Common2021–2024 main window; full available and annual breakdown secondary. Historical engine same-open execution and data/FX/total-return assumptions remain limitations, not newly certified live realism. New target does not authorize changing allocation or exits.

## Inference and decision
Paired monthly comparisons; moving/circular block bootstrap with block length6 months,4000 draws, fixed seed20261101, descriptive95% intervals. No automatic veto if an interval spans zero. Distinguish magnitude, direction, seed/period/market stability, and the limited effective sample. USA/EU are correlated checks, not independent replications. Repeatedly inspected history and multiple comparisons preclude untouched-holdout claims. No promotion from one market or from optimizing a candidate's own new target. Report negative outcomes and unchanged choices. Preserve provenance and deliver code/results/checkpoints, not just a claimed winner.
