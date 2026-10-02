# Evidence V3 — LTR tail-symmetry diagnostic

Status: **DIAGNOSTIC ONLY; PREREGISTERED BEFORE EXECUTION**

## Purpose

Explain how the frozen Dev72 LTR can retrieve the future 21-day winner far above chance while producing poor Top1/Top5 economics. This diagnostic does not test or select a trading rule and has no advancement gate.

## Frozen inputs

- `evidence_v3/results/ltr_baseline_transfer_dev72/PREDICTIONS.csv`
- frozen predictions SHA256 `fafe49e44bd24a250ecb023338ef97696f79767404b281ff1d04af1f890c14b5`
- exactly 114 evaluation dates with 72 candidates each, as certified by the Phase-B summary.

No model refit, new feature, network data, alternative target, threshold or portfolio rule is permitted.

## Questions fixed before execution

For each monthly cross-section, order candidates by frozen OOS `LTR_SCORE` descending and identify the realized 21-day global winner and loser.

Report:
1. Top1/Top5/Top10 capture counts for the global winner.
2. Top1/Top5/Top10 capture counts for the global loser.
3. Exact random expectations and enrichment factors for both positive and negative extremes.
4. Number of months in which Top5 and Top10 contain both the global winner and the global loser.
5. Spearman correlation of `LTR_SCORE` with `fwd_ret_21` and separately with `abs(fwd_ret_21)` for each month, plus means/medians and positive-rate diagnostics.
6. Mean absolute 21-day return in score Top1, Top5 and Top10 versus the full cross-section.
7. Mean and median realized return by **fixed score-rank bucket**: ranks 1-6, 7-12, 13-18, ..., 67-72 (12 equal six-name buckets).
8. Positive-return rate and extreme-loss rate (`fwd_ret_21 <= -10%`) for each fixed rank bucket.
9. For score Top10, report average count of names in the realized top-10 return set and realized bottom-10 return set.

## Interpretation constraints

- The diagnostic may identify whether LTR behaves more like a directional ranker or an extreme/tail detector.
- It may not select an optimal K, score threshold, rank bucket, category, volatility rule, long/short rule or direction filter on Dev72.
- Any new architecture motivated by this result must be specified before testing on a **new disjoint development universe**. Dev72 remains burned and diagnostic-only.
- Subperiods may be reported descriptively but cannot be used to define a regime rule.