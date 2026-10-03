# ETF_TRADER_RANKER_STABILITY_V1 — status

Branch: research/ranker-stability-v1

## Frozen forensic conclusion inherited
- Runtime/code is deterministic on byte-identical raw.
- Execution ablation collapses the native 4.9236 pp CAGR span to ~0.000022 pp when Repeat2 decisions are frozen across all three raw snapshots.
- Tail and macro are not the dominant amplification.
- Titanium component ablation localizes the dominant instability to Compact21.
- Compact21 inference-only feature perturbation is negligible; the amplification is created mainly by refitting the ranker on nearly identical training sets.
- Q4 feature quantization reduces full-pipeline CAGR span by ~54.4% but worsens Top1 disagreement and lowers mean CAGR; it is not adopted as the primary fix.
- Single-thread dynamic lookahead closure passes; no operational lookahead remains indicated by the audited replay.

## Phase A
Preregistered models:
- XGB_CANONICAL
- LGBM_XENDCG
- LGBM_LAMBDARANK
- CAT_YETI
- RIDGE_POINTWISE

Confirmed results already complete:
- XGB_CANONICAL: rank_mean_abs 0.0596426; stability Spearman 0.957036; Top1 disagreement 0.4375; NDCG@5 0.510679; ~34.85 s/fit.
- LGBM_XENDCG: rank_mean_abs 0.0242050; stability Spearman 0.993313; Top1 disagreement 0.229167; NDCG@5 0.522381; ~15.02 s/fit.
- LGBM_LAMBDARANK: rank_mean_abs 0.0419688; stability Spearman 0.979484; Top1 disagreement 0.270833; NDCG@5 0.493552; ~23.69 s/fit.
- RIDGE_POINTWISE: rank_mean_abs 0.0009196; stability Spearman 0.999950; Top1 disagreement 0.0; NDCG@5 0.532907; ~0.283 s/fit.
- CAT_YETI: still computing at this marker.

Under the preregistered Phase-A gate, XENDCG and RIDGE already qualify; LambdaRank also appears eligible on the frozen four-year sample because NDCG@5 remains above 95% of XGB and stability improves materially.

## Phase B
All-year 2017-2026 benchmark launched for XGB, XENDCG, LambdaRank, Ridge.
RIDGE all-year is already complete:
- rank_mean_abs 0.0009001
- stability Spearman 0.9999536
- Top1 disagreement 0.0
- Top5 Jaccard 0.988889
- NDCG@5 0.556077
- target Spearman 0.097424
- mean fit/predict 0.237 s
- maturity PASS
- determinism PASS

## Laya fallback
Laya is reserved for a later experimental line only if conventional numeric LTR fails. It is a typed option/score decision engine over text/JSON, not a native grouped numeric LTR estimator. Published material also reports degradation for long option lists; therefore ranking 149 ETFs directly as 149 options is not the preferred first-line architecture.
