# COMPACT21_ORTHOGONAL_FEATURE_ABLATION_V1 — preregistration

## Objective

Identify a materially smaller set of Compact21 inputs that carries stable, non-redundant predictive information before any new production-ranker training is attempted.

This experiment is explicitly feature discovery only. It must not use CAGR, Sharpe, drawdown, strategy P&L, post-2017 realized targets, or the outcome of any new XGB/HGB fit to choose features.

## Frozen evidence source

Use only the three frozen TI_COMPACT.parquet panels from GitHub Actions run 37150436612 in repository AM1975MA/Test.

Canonical Compact21 source and the 125-feature declaration remain guarded by compact21_stability_v1/source_gate.py.

## Temporal boundary

Supervised feature discovery is restricted to rows satisfying the canonical Compact21 training eligibility before 2017-01-01, including strict exit_date_21 < 2017-01-01.

Rows from 2017-01-01 through 2026-06-30 may be used only for outcome-free feature stability auditing. Their target columns, strategy decisions and economic results must not enter feature scoring or set selection.

## Evidence classes

1. Cross-sectional Information Coefficient: monthly Spearman correlation between each feature and target_rank_21, independently on all three frozen snapshots.
2. Benjamini-Hochberg FDR across all 125 candidates using the worst repeat p-value.
3. Mutual information for deterministic nonlinear relevance.
4. Boruta-style shadow test with ExtraTrees: each real feature is compared with the 95th percentile of permuted shadow importance over three repeats and three fixed seeds.
5. Cross-snapshot stability: raw Spearman, cross-sectional rank MAD, normalized value difference, exact-value fraction and missingness mismatch across all three pairs.
6. Semantic de-duplication: names differing only by _pct or _dev are one economic family. The frozen 125 features map to 46 families.
7. mRMR-style greedy orthogonalization using absolute cross-sectional-rank correlation with already selected features.

## Frozen scoring

Predictive score: 40% IC percentile + 25% MI percentile + 25% Boruta-hit percentile + 10% repeat-direction percentile.

Robustness score: 45% cross-snapshot Spearman percentile + 40% inverse rank-MAD percentile + 15% inverse missingness-mismatch percentile.

Consensus: 65% predictive + 35% robustness.

Orthogonal utility: consensus_score * (1 - 0.70 * max_abs_rank_corr_to_already_selected).

No weight may be changed after outcomes are visible.

## Frozen outputs

Create nested feature ladders of 8, 12, 16, 24, 32 and 40 features plus the complete 46-family champion set.

Also report a descriptive strong-evidence subset requiring worst-repeat BH-FDR q <= 0.10, Boruta hit fraction >= 0.50 and median pre-2017 cross-snapshot raw Spearman >= 0.995.

## Next-stage rule

This experiment does not select the winning production set. After the feature-only result is frozen, a separate benchmark may train the canonical Compact21 learner on BASE125 and the predeclared ladders. Stability and predictive quality must be judged before economics. Feature-count selection from CAGR or strategy P&L is forbidden.
