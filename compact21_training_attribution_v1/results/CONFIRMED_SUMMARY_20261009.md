# COMPACT21 training-source attribution — independently recovered result (2026-10-09)

## Evidence and provenance
- Original experiment: GitHub Actions [37916159772](https://github.com/AM1975MA/Test/actions/runs/37916159772), ten of ten 2017–2026 annual fits SUCCESS, original validation SUCCESS. Original summary failed only due missing transitive matplotlib dependency.
- The first recovery [37930864105](https://github.com/AM1975MA/Test/actions/runs/37930864105) restored the pinned dependency set and revealed that the old aggregator compared raw hardware identity instead of the already-required normalized CPU dispatch contract. Across all ten original annual artifacts the exact source, raw inputs, preregistration, normalized dispatch profile and baseline reference match. CPU model differs across GitHub hosted job machines; normalized AVX2/Haswell target and thread count are identical.
- The second summary-only recovery [37931212920](https://github.com/AM1975MA/Test/actions/runs/37931212920) completed SUCCESS, with no annual retraining and the original annual artifacts unchanged. Immutable summary artifact ID: **11616107888**, named `attribution-summary-recovery`; includes `SUMMARY.json` and `SUMMARY.md`.
- Summary integrity PASS, 114 complete monthly evaluation dates, 16,986 common test rows per vintage, exactly three acquisition pairs and no omitted annual folds. Preregistered training-factor experiment remains strictly diagnostic and non-deployable.

## Original frozen controls and counterfactual factorial

| Training features / labels | Rank-MAD | Change in Rank-MAD vs BASE | Native-trained model Top1 disagreement on identical Repeat2 inference | Delta Top1 vs BASE (pp) | Decision |
|---|---:|---:|---:|---:|---|
| Both original vintage (BASE) | 0.053609 | reference | 50.00% | reference | control |
| Own feature matrix + common Repeat2 labels | 0.050215 | -6.33% | 56.43% | +6.43 | fails decision stability |
| Common Repeat2 feature matrix + own labels | 0.041422 | -22.73% | 57.02% | +7.02 | fails decision stability |
| Both common Repeat2 (identity control) | 0 | -100% | 0% | -50.00 | not deployable; tautological |

**These are counterfactual source-attribution tests, not usable production strategies.** A lower Rank-MAD can coexist with a much higher Top1 disagreement. The -100% identity-control result is tautological and cannot be reported as a usable stability enhancement. Label-associated and feature-associated changes interact nonlinearly with the fitted ranker, and this fixed factorial does not isolate unique additive causal contributions.

### Full pairwise evidence
| Variant | Pair 1–2 MAD / Top1 | Pair 1–3 MAD / Top1 | Pair 2–3 MAD / Top1 |
|---|---|---|---|
| BASE | 0.053423 / 54.39% | 0.053423 / 42.98% | 0.053982 / 52.63% |
| Own X + Repeat2 Y | 0.050360 / 48.25% | 0.049152 / 54.39% | 0.051131 / 66.67% |
| Repeat2 X + Own Y | 0.041945 / 57.89% | 0.041732 / 52.63% | 0.040589 / 60.53% |

## Additional exploratory predictive diagnostics (NOT acceptance gates)
Using the 113 mature monthly dates, per-vintage annual realized-quality summaries aggregated by date counts (12 for 2017–2025, five for 2026) give the following descriptive results:
- Original BASE: Top1 mean realized percentile ≈0.58344, NDCG@5 ≈0.55225.
- Own features/common labels: Top1 ≈0.56512, NDCG@5 ≈0.54707.
- Common features/own labels: Top1 ≈0.56609, NDCG@5 ≈0.54873.
These are cross-vintage dependent observational diagnostics, not fresh OOS evidence, and were not included in the summary's promotion gates. Do not interpret them as investment returns.

## Forensics
In the 2026 fit, changed canonical rounded integer training-label counts are only 24/33833 (pair 1–2), 16/33833 (pair 1–3), 20/33833 (pair 2–3), whereas a very large fraction of finite feature cells are numerically unequal across source acquisitions. The numeric inequality count is not an effect-size estimate (changes may be extremely small). Training panels are expanding; do not treat repeated annual training rows as independent observations.

## Decision
**NO ADOPTION.** Both nontrivial counterfactual treatments improve aggregate rank closeness but worsen actual Top1 consensus; no full-strategy CAGR was run in this experiment and no CAGR preservation is demonstrated. The 114-month history is already development data with multiple prior trials; an untouched future holdout is still mandatory.

Suggested next preregistered diagnostic: investigate which monthly Top1 flips are driven by near-tie score margins versus broad rank reversals and evaluate their realized economic regret on mature dates without training on that regret. Measure candidate quality and model decision convergence jointly, then (only if passed) unchanged full-strategy economic replay and independent holdout. Leave ETF_trader and negative feedback unchanged.
