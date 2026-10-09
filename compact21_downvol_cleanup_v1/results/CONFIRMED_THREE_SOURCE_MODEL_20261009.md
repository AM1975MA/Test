# Confirmed independent three-source DOWNVOL-cleaned XGB comparison — 2026-10-09

## Reproducibility and stage sequence
1. Single Repeat1 source root-cause and cleanup validation [37936052825](https://github.com/AM1975MA/Test/actions/runs/37936052825) — PASS, original OHLC-derived legacy feature parity, 6 unit tests, exact original other columns.
2. Prepare individually three frozen Original149 acquisitions [37936573578](https://github.com/AM1975MA/Test/actions/runs/37936573578) — 3/3 PASS, source parity/labels/30-feature eligibility preserved, 9 cleaned feature columns in every vintage.
3. Frozen ten-year model training [37936989442](https://github.com/AM1975MA/Test/actions/runs/37936989442) — validation PASS; annual 2017–2026 10/10 PASS, three native vintages with exact independent 360-round XGB refits; first summary attempt failed on unequal *physical row order* of original and candidate vectors (94.7% dates in inconsistent order), not on scientific cohort.
4. Summary-only recovery [37938079106](https://github.com/AM1975MA/Test/actions/runs/37938079106) — SUCCESS after sorting both original and cleaned score frames by (vintage,signal_date,ticker) before exact non-score equality. New 8 source/ordering tests PASS, 39 original predictive regression tests PASS, source gate PASS. All original annual artifacts reused unchanged. Artifact: [clean-downvol-three-source-summary-recovery, ID 11619126898](https://github.com/AM1975MA/Test/actions/runs/37938079106/artifacts/11619126898), containing full machine-readable SUMMARY.json and human-readable SUMMARY.md.

## Verified overall results: cleaned XGB versus unchanged original XGB

| Endpoint | Original BASE | Cleaned data | Interpretation |
|---|---:|---:|---|
| Common-input mean Rank-MAD | 0.053609 | 0.046611 | ~13.05% better, below minimum 25% improvement |
| Native Top1 disagreement | 50.00% | 50.58% | 0.58 pp WORSE |
| Realized mature selected Top1 percentile | 0.583437 | 0.558928 | 0.024509 absolute reduction (~4.2% relative) |
| Realized Precision@5 | 0.126254 | 0.127434 | slight gain |
| Realized NDCG@5 | 0.551994 | 0.552966 | slight gain |

### All acquisition pairs (114 monthly signal dates per pair)

| Pair | Original common Rank-MAD | Cleaned common Rank-MAD | Original native Top1 flip | Cleaned native Top1 flip |
|---|---:|---:|---:|---:|
| 1–2 | 0.053423 | 0.045640 | 54.39% | 55.26% |
| 1–3 | 0.053423 | 0.047791 | 42.98% | 48.25% |
| 2–3 | 0.053982 | 0.046401 | 52.63% | 48.25% |

## Frozen pass/fail gates
- `STABILITY_PILOT_PASS = false`: rank-MAD does not fall 25% and native Top1 gets worse overall/on pairs 1–2 and 1–3.
- `NEAR_REPEATABILITY_PASS = false`: none of the 3 pairs achieve <=5% Top1; no 90% MAD reduction.
- `QUALITY_CONSERVATION_PASS = false`: overall mean selected Top1 percentile still >=95% BASE and Precision@5 >=95% BASE, but vintage 1 failed individual >=95% floor and 3-month bootstrap one-sided lower-bound noninferiority gate failed. Small average score change or NDCG improvement does not compensate for failure.
- `STABLE_WITH_CONSERVED_QUALITY = false`, `FULL_IMPROVEMENT = false`.
- `full_portfolio_economic_replay_authorized = false`, by the frozen prerun protocol; **CAGR of cleaned variant NOT measured**. No portfolio adoption and no change to Etf_trader.

## Scientific interpretation and follow-up
The extreme null rates were due to a **real feature-definition pathology** in original `downvol21/63/126`: negative-only rolling series with minimum negative counts 10/31/63. Each independent frozen acquisition's repaired historical features are now fully populated for the 114-month evaluated window. Repair with zero-target semideviation (all returns, full window) is semantically sound, causal and deterministic; that alone does not establish how well XGBoost learns, especially at close Top1 ranks and under small vintage input revisions.

The observed experiment proves that **removing the missing-value discontinuity is insufficient** to stabilize the original XGB choice. Lower global rank disagreement can coexist with worse top-of-book choices and realized Top1 quality. No further unregistered weight/quantization/model sweep is warranted on burned Original149 development evidence. Appropriate next scoped investigation is to inspect input data instability in the remaining 116 features (OHLC adjustment, cross-sectional ranks, robust deviations, labels), and design one explicitly preregistered targeted upstream correction; then check both stability and predictive quality before any CAGR simulation. An independent future/universe holdout remains essential.

Status: **SOURCE QUALITY REPAIR PASS; MODEL STABILITY/QUALITY GATE FAIL; NO CAGR CLAIM**.
