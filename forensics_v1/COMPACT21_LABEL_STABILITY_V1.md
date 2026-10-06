# ETF_TRADER_COMPACT21_LABEL_STABILITY_V1 — preregistration

## Purpose
Test whether minimal deterministic coarsening of the Compact21 training relevance label suppresses the large XGBRanker sensitivity already attributed to tiny historical label perturbations.

## Motivation frozen before test
- Compact21 is the dominant Titanium amplifier.
- Inference-feature perturbations alone produce ~0 Top1 disagreement.
- Training-feature-only and training-label-only perturbations both materially change Compact21.
- Current integer label is round(target_rank_pct * 100).
- Cross-snapshot integer-label disagreement is only ~0.05–0.07%, yet it causes large fitted-ranker divergence.
- Q4 feature quantization reduces full CAGR span by ~54.4% but does not improve Top1 convergence.

## Frozen interventions
1. BASE: current labels, current features.
2. L50: use round(target_rank_pct * 50) as the XGBoost pairwise relevance label; features unchanged.
3. Q4_L50: same L50 label plus 4-decimal rounding of all 125 F2D Compact21 features at train and inference.

L50 is a single mechanistic choice, not a sweep. Its rank-bin width is 0.02, deliberately larger than one Original149 rank step (~1/149 = 0.0067) while preserving 50 relevance levels.

## Frozen evaluation
- Frozen Yahoo repeat1 vs repeat3.
- Annual model years: 2017, 2020, 2023, 2026, matching prior Compact21 forensic.
- Same canonical Compact21 params, seeds and maturity-safe rowsets.

## Primary endpoints
- Compact21 rank mean absolute difference.
- mean daily Spearman.
- Top1 disagreement fraction.

## Secondary endpoints
- raw prediction mean absolute difference.
- feature exact fraction.
- training label disagreement fraction after coarsening.

## Decision rule
Do not select a variant from CAGR. Only if L50 or Q4_L50 materially improves cross-snapshot Compact21 stability may it advance to a separately preregistered full-pipeline replay.
