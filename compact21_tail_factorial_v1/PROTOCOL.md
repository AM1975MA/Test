# Compact21 / Titanium Tail / MA3 Hybrid Tail — frozen 2×2×2 ablation

This is an **explanatory, not exploratory parameter search**, preregistered 2026-10-17 before seeing its eight-arm outputs. Branch: `research/compact21-tail-factorial-20261017`, production untouched.

## Immutable original inputs

- 125-feature original XGB BASE annual OOS forecasts from successful run 37229180477.
- Return-gap graded `rank:ndcg` XGBoost RETURN_RANK_NDCG annual OOS forecasts from successful run 39031200131.
- Original149 source input revisions and canonical V2 saved baseline_control and candidate replays from successful run 39031200131; raw market snapshots run 37121749852. Input SHA and original replay raw/source parity are verified, all original 2017–2026 score rows matched; 3 Yahoo vintages are correlated.
- Models, training windows, 125 features, ET/XGB Hybrid Tail and original Titanium Tail scores all **frozen**. No new model fitting, no future returns used in signals, no changes to portfolio production code.

## Fixed factorial: 8 combinations

Two Compact21 learners, BASE or RETURN_RANK_NDCG; either Titanium's auxiliary `tail` contribution with macro-tail bonus ON or OFF; and either MA3 42-feature ExtraTrees/XGB Hybrid Tail ON or OFF. Exactly eight combinations, across all three dependent Yahoo vintages (24 full simulator runs).

For Titanium Tail ON use unchanged historical archived `TIT_R` for the corresponding Compact21 candidate; original Titanium combines 70% Compact21 percentile, 30% Ridge Tail percentile, plus the conditional 0.15 macro+Tail bonus and a final percentile rank. For Titanium Tail OFF use **only within-date Compact21 score percentile rank** (no macro Tail bonus); do not set the Tail score to zero. This is a clean renormalization.

For MA3 Hybrid Tail ON use exact original Stage19 score: `0.475*TIT_R + 0.525*(.4*H_t+.3*H_{t-1}+.3*H_{t-2})**1.1` where `H=.6*ET_TAIL+.4*XGB_TAIL`. Keep ET/XGB model-agreement risk-off channel as in original. For MA3 Hybrid Tail OFF use **only `TIT_R` score** (no zeros or model-dependent dilution), and silence the separate ET/XGB agreement signal used in risk-off weight overrides. All other risk, MA3 allocation logic, V6 alternative generation, costs and execution are unchanged. Record the fact that toggling Hybrid Tail also disables its agreement decision—this is a package-level ablation, not the isolated causal effect of scoring alone.

Original canonical `holdout70/v2_canonical_same_source_compare.py::replay_full_universe` is invoked unchanged. A research-only local interception replaces the two named Stage19 scoring/agreement functions only for MA3-off arms, restoring functions immediately after each replay. The original ON/ON BASE and ON/ON RETURN_RANK arms MUST reproduce archived daily source paths, selections and CAGR/DD/Sharpe to numeric equality (tolerance 1e-12); if not abort without publishing a valid summary.

## Primary endpoints and attribution design

- Preallocation rank Top1 from the actual score to be sent to portfolio allocator, matched 114 monthly dates, 149 tickers, 113 mature economic evaluation months; mean next-21-session realized ETF return, exact winner hit rate, top-five hit rate, top-five overlap and cross-source monthly Top1 disagreement.
- Full V2 2366-session historical investment CAGR, MaxDD, Sharpe, daily Top1/Top2/weight, annual equity returns, turnover, cross-source CAGR span and daily final Top1 disagreement. Source equity curves reconstructed independently from archive paths.
- **Factorial contrasts**: at fixed Tail gates report Return-Rank minus BASE for preallocation chosen future return and CAGR. Report marginal mean effect of switching Titanium Tail and MA3 Tail and their interactions, plus direct comparison with all-ON canonical configuration; note CAGR contrasts are nonlinear, nonadditive and sample-dependent.
- Separate *fixed 50/50* monthly top-two comparator calculated from **next-open trade prices** with monthly rebalance and **10bp one-way turnover cost**, no leverage, no MA3 risk or alternate ETF. This is a diagnostic alternate **execution policy**, not the canonical V2 strategy. It helps see whether improvements persist without dynamic risk or opportunity weighting. No 21-day outcome enters selection.
- In every economic comparator, same parameters and execution assumptions for BASE and Return-Rank within the matched arm.
- All comparisons are retrospective on repeatedly inspected history. No prospective statistical significance, no tuning weights/targets/TopK, no promotion based on tests.

## Audit gates
Strict identity on original full cohort keys and model components; all-on score and equity parity, full 149 eligible symbols, 114 monthly signals, 2366 daily sessions, no NaN scores and original native BASE/Return-Rank labels identical. Year 2017–2026 support must not drift. Fail closed for discrepancies. Store all 24 arms and aggregated table, monthly-level diagnostics, yearly summary and exact source SHA256s.

Interpretation: ablation compares frozen model **packages** inside a specified decision architecture; it does not prove which training architecture is universally best or disentangle selection, risk, and exposure causally. For deployment require prospective independent data.
