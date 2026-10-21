# V3 L04/02 — Strict prequential supervised meta-ranker on frozen Ranker/Tail scores

**Date:** 21 October 2026. **Completed, NOT PROMOTED.** No CAGR or production changes.

- Success [Actions run 39660554536](https://github.com/AM1975MA/Test/actions/runs/39660554536), artifact **12372618737**.
- Inputs: frozen original 149 ETF OHLCV snapshot 39482809691; already annual-OOS ranker and Tail classifier score percentiles from 39652989033 and 39655513813, assembled in published run 39659903643.
- Predeclared logistic meta ranker `C=.2` with only four score-derived inputs: pairwise percentile, Tail percentile, product, absolute disagreement; target = 21D future ETF upper-decile by same-month rank.
- Annual expanding refits from 2022; **training first-stage observations themselves had been scored in OOS historical years 2018–2021** and their 21D labels matured before January 1 cutoff. Evaluation 53 later OOS months 2022–May2026, same ETF/months across all controls, 500 canonical overlapping baskets.
- No macro, risk, allocation, CAGR, changes to L00/L01/L02 or selection on test labels.

| Metric | Ranker | Tail static | Blend50 static | Blend25/75 | Supervised Meta |
|---|---:|---:|---:|---:|---:|
| Basket Top-3 | 39.162% | 44.268% | **45.102%** | 44.679% | 44.257% |
| Basket Top-1 | 16.970% | 17.675% | **18.038%** | 17.940% | 17.962% |
| nDCG@3 | **0.540941** | 0.523551 | 0.536393 | 0.527458 | 0.523404 |
| Selected basket regret | **0.109655** | 0.117513 | 0.112841 | 0.115996 | 0.117003 |
| Elite21 average precision | 0.272677 | 0.292392 | 0.289412 | 0.290454 | **0.293750** |

Meta minus Tail Top-3: **−0.0113 percentage points**, 95% paired six-month block bootstrap **[−0.4415,+0.4302] pp**, 6000 draws. Elite AP +0.001358 with CI [-0.001391,+0.004611]. Meta minus Blend50 nDCG@3 -0.012989 with CI [-0.027414,-0.000086].

## Decision

Reject promotion of `L04_META_LOGIT` under current evidence. It has no proven incremental winner capture and loses nDCG against the simple equal blend. Simple blends themselves were not a stable Top-3 improvement against Tail across the entire 101-month explored window. Keep both original expert scores **separate and version-frozen**, Tail for upper-winner recall and ranker for general/regret ranking.

The 53 months are sequentially out-of-year for meta fitting but **not an independent virgin holdout**: this calendar has already been examined in earlier model research. Future complex meta-ranker experiments require new data vintage or explicit nested selection discipline.

**L05 handoff:** Evaluate the selection/allocation rule with score source held fixed (Tail winner specialist), not a new weighted blend and not a CAGR maximization.
