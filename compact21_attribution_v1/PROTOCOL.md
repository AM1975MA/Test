# RETURN_RANK_NDCG: stage-by-stage portfolio attribution audit

Frozen 2026-10-17; research-only, **zero fits, zero changes to canonical models or simulator**. User wants to investigate why RETURN_RANK_NDCG had worse standalone Compact21 selected-ETF realized returns (+1.96% vs BASE +2.62% per 21 sessions) but improved historical full V2 CAGR (35.84% vs 31.76%).

## Immutable inputs

- Original BASE 125-feature annual OOS Compact21 predictions: GitHub run 37229180477 artifact `predictive-BASE`, exact file hashes verified.
- RETURN_RANK_NDCG predictions: run 39031200131 artifact `compact21-return-predictive`, source hash-verified.
- Complete certified untouched 149-ETF V2 BASE and RETURN_RANK_NDCG replays, including independently verified raw-to-cache parity, 3 correlated Yahoo revisions, each 2366 sessions, same run 39031200131 artifact `compact21-return-economic`.
- Those economic paths and their previously observed metrics are known, previously inspected **development data**, not out-of-sample in the statistical-model-selection sense. No promotional claim from this audit.

## Descriptive stage-by-stage diagnostics, fixed before computation

For each Yahoo revision, month, and ETF, use ORIGINAL frozen signals only. Four stage definitions:
1. **COMPACT21**: frozen OOS XGB scores (BASE versus NDCG).
2. **TITANIUM**: persisted canonical `TIT_R` post `0.7*rank(COMPACT21)+0.3*rank(TAIL)+MACRO` and cross-sectional re-ranking (no refit).
3. **PRE-ALLOCATION ENSEMBLE**: reconstruct unchanged Stage19 score formula from persisted `ENSEMBLE_TAIL_OOS`: `tail = .6*ET_TAIL+.4*XGB_TAIL`; `sm=.4*tail(t)+.3*tail(t-1)+.3*tail(t-2)`, with initial-row replication; `score=.475*TIT_R + .525*clip(sm,0,1)^1.10`. Verify **exact mechanical decomposition** `delta(final_score)==.475*delta(TIT_R)` to 1e-12 since all other ensemble sources are unchanged.
4. **REALIZED V2 ALLOCATION**: original certified daily `d1,d2,weight1,margin,alt_idx,turnover,equity` arrays, **not reconstructed guesses**.

Stage reporting: number of vintage-month decisions, rate of Top1 leader changes, average Top5 Jaccard similarity, per-month signed realized next-21-session returns of each stage Top1 on 113 mature dates (evaluate only; outcomes never used for decisions), and shift in winner percentage. Across three revisions also report source-disagreement at each stage, preserving dates within vintage.

Allocation reporting by revision and aggregated across correlated revisions: fraction of 2366 sessions with different `d1`, `d2`, either ordered pair; mean absolute difference `weight1` and fraction >.01; margin changes, turnover changes, V6 alternative index changes, CAGR/MaxDD/Sharpe and per-year change. Audit each equity path via independent `metrics` and compare to original replay-result JSON to 1e-12. Compute **additive accounting** of difference in log equity by day-group with (i) same Top1/Top2, (ii) same Top1 but different Top2, (iii) different Top1; report this as *path-dependent contemporaneous accounting only* and **do not** call it causal contribution because prior holdings/risk states can differ even on days of matching leaders. Provide chronological per-year log-equity difference and warn different paths are not independent.

Diagnostic interpretation explicitly distinguishes:
- Exact mechanical pathway of Stage19 final-score perturbation.
- Observed ranking/holdings/weight/return changes (correlated downstream response).
- Any **causal** allocation vs selection decomposition remains unidentifiable from two observational replay paths; follow-up would require newly preregistered hybrid-state counterfactuals with path-dependent simulator.

Fixed checks: SHA identities, equal native keys/labels, exact per-month 149-ETF source coverage, unchanged ET/XGB/TAIL columns bit-for-bit, exact all-date final-score delta relationship, no nonfinite values, equal session dates, raw-linkage and BASE parity PASS for all 3 revisions, replay metric independent 1e-12 parity. Preserve detailed parquet/CSV + JSON and any negative finding. No future labels in generation of scores; no production changes. No new hyperparameter scan on repeatedly reused history.
