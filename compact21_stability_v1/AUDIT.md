# COMPACT21_STABILITY_V1 — independent evidence audit

## Prior evidence and its limits

`forensics_v1/results/FEATURE_QUANTIZATION_FULL_Q4_V1.json` supports a **54.4042% reduction of the max-minus-min CAGR span across three frozen Yahoo snapshots**, from 4.923631 to 2.244969 percentage points. This is neither a variance reduction estimate nor evidence that decisions converged. Mean CAGR fell from 31.7581% to 29.0134%; mean pairwise daily Top1 disagreement rose from 31.3750% to 34.0941%. Either-Top1/Top2 disagreement improved slightly, from 61.6512% to 60.6227%.

The old full-Q4 runner rounded all 125 feature columns before `models.fit_predict`, incidentally affecting both Compact21 and Compact63. `models.variants` uses Compact21 and Tail for the historical baseline; Compact63 is inactive in that baseline. New implementations should isolate the Compact21 intervention explicitly.

`COMPACT21_LABEL_STABILITY_V1.json` already records failed simple target coarsening: L50 improves rank MAD by 13.9561% but increases Top1 disagreement from 43.75% to 54.1667%; Q4_L50 improves rank MAD by 22.0753% but increases Top1 disagreement to 60.4167%. Repeating those recipes is a control, not a new solution.

The completed `ranker_stability_v1/results/PHASE_B.json` is authoritative over its stale STATUS narrative. Ridge and LambdaRank satisfy that benchmark's gate. XENDCG does not: NDCG@5 ratio to XGB is 0.915158, below 0.95. Ridge is an existing stable comparison, not evidence that quantization is solved or that its full strategy is validated.

## Actual mechanism

`kernel.add_labels` computes 21-session forward Open returns and then their cross-sectional percentile rank. `models._fit_compact_rankers_isolated` converts those ranks to `round(rank * 100)` integer labels. Small return differences can reorder near-tied observations or create/break exact ties **before** that conversion. Removing the integer rounding removes one artificial partition but cannot remove underlying ordinal-rank sensitivity.

The prior Compact21 attribution supports two material training pathways. On frozen years 2017, 2020, 2023 and 2026, training-feature-only perturbations have mean rank MAD 0.053290 and Top1 disagreement 62.5%; training-label-only perturbations have MAD 0.044974 and Top1 disagreement 58.3333%. Total training perturbations have MAD 0.059643 and Top1 disagreement 43.75%. Inference-only perturbations have MAD 0.000105 and Top1 disagreement 0%. These are interactions, not additive shares of blame; label rounding is not established as the sole root cause.

## Data and causal controls

- Original149 is development evidence with repeated inspection, not an untouched holdout. Survivorship/universe caveats remain.
- The frozen raw acquisition contract is three sequential downloads in CI run `37121749852`, yfinance 0.2.66, pandas 2.2.3, start 2004-01-01, end exclusive 2026-08-01, adjusted OHLC using same-row Adj Close / raw Close and raw Volume.
- Frozen Titanium internal artifacts come from CI run `37150436612`; their `TI_COMPACT.parquet` is the benchmark input.
- Annual Compact21 fitting must retain signal date < January 1 and exit_date_21 < January 1, nonmissing target and at least 30 valid feature values. Row/group ordering is signal_date, ticker.
- Ranker benchmarks use monthly signal queries (usually 12 per full year and 6 in 2026). Their `mean_daily_spearman` name does not imply daily independent samples. Full strategy Top1 disagreement is measured on daily leaders and is a different endpoint.
- Any learned feature scale, imputation, quantization step, return deadband or noise estimate must use only matured pre-cutoff training rows. Future-row mutation/truncation must leave fitted state and historical predictions invariant.
- Pooling historical repeat snapshots is allowed as a frozen perturbation diagnostic, but it is not a deployable single-vintage transform. Report it as a separate diagnostic scope if used.
- Freeze file hashes, source commit, dependency versions, seeds, single-thread worker settings and the experiment definition before outcomes are visible. No feature-step/target-bin/algorithm choice from CAGR.

## Suggested acceptance gate

Use original XGB plus Q4 as controls and a fixed small factorial of feature stabilization versus target stabilization. Include an existing deterministic Ridge reference. Compare all three repeat pairs; use identical Repeat2 inference features for the primary training-sensitivity endpoint and each snapshot's own inference features as a secondary total-sensitivity endpoint.

A mechanistic candidate should advance only with rank MAD reduced by at least 25%, improved stability Spearman, Top1 disagreement no worse, NDCG@5 at least 95% of baseline on the same evaluation rows, deterministic same-data fits, and passing maturity/future-invariance controls. Specify aggregation and all-year checks before running. Full-pipeline CAGR and risk are subsequent diagnostics; they do not substitute for the decision-convergence gate. Independent data or a forward test is still needed before production promotion.

Hard quantization always introduces boundaries. A training-only noise-aware grid may improve stability, but neither equality on one pair nor a smaller economic span establishes that the perturbation problem has been eliminated.

## Implementation review

Initial read-only review of `targets.py`, `quantization.py` and `run_benchmark.py` found the intended annual fit boundary respected: the runner supplies native eligible pre-cutoff training rows to separately fitted per-snapshot grids, applies those same grids at inference, and constructs targets with explicit maturity validation. Common Repeat2 inference and own-snapshot inference are separated. Pairwise label-relation disagreement correctly accompanies integer-label disagreement; dense label numbering alone is not a meaningful measure of pairwise changes.

The target implementation removes rank-percentile multiplication/rounding in its ordinal control and introduces a fixed 1 bp simple-return resolution in its economic target. It preserves economic ties and does not claim universal bin-boundary invariance. The scale quantizer uses known domain widths or annual training IQR divided by 4096 and rounds the step upward to a dyadic value. This is **scale-aware resolution**, not a measured vendor noise floor. It acknowledges that grids themselves can differ across snapshots at IQR step boundaries.

Review fixes verified in the benchmark: the `legacy` mode name is consistent, predictions must be finite, empty common/quality rowsets fail, JSON NaN is rejected, years are checked, and pair-specific aggregate results remain inspectable. Predictive quality is compared against the new BASE on identical quality rowsets; the explicit 2026-07-01 outcome cutoff differs from the previous Phase B benchmark.

The full hook mirrors canonical scheduling and preserves Compact63 inputs, labels, seeds and prediction reduction for every variant except the explicit historical Q4_LEGACY control. Input and prediction hashes are retained. The full MA3 ensemble now uses n_jobs=1 to avoid the parallel ExtraTrees nondeterminism established by the prior forensic. This execution-only change applies to all new controls and challengers; exact historic economic parity should be assessed with that caveat.

`summarize_full.py` retains every outcome and verifies expected benchmark advancement membership, exactly three repeats, identical leader dates/sessions, raw/source identity against each repeat's BASE, source-only regeneration flags/hashes, strict fit-exit maturity audits, unchanged negative feedback, canonical MA3 feature hashes, and Compact63 prediction preservation except Q4_LEGACY. Its fixed economic diagnostic gate requires span <=75% of new BASE, Top1 disagreement no worse and mean CAGR >=95% of new BASE, plus source/maturity evidence. Historical Q4 is a diagnostic comparison only. Eight preserved standard-library unit tests for aggregate success, source rejection, maturity rejection, coverage loss, missing results, nonfinite JSON, expected-matrix completeness and silent inner joins passed.

Workflow review identified and corrected contract upload, artifact-name compatibility and passing the persisted benchmark advancement matrix. Dependency pins and separate unit discovery are recorded by the author. The targets and quantizer are train-only by construction, and synthetic tests exercise their future-row independence. This is not a new full raw future-mutation/truncation replay: no claim of a new dynamic full-pipeline causality PASS is made here.

Real frozen-panel/model execution and actual outcome review remain pending. This audit does not certify production suitability or any unobserved stability outcome.
