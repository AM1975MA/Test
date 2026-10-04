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

Workflow review identified and corrected contract upload, artifact-name compatibility and passing the persisted benchmark advancement matrix. Dependency pins and separate unit discovery are recorded by the author. The targets and quantizer are train-only by construction. Actual-worker synthetic integration tests preserve canonical Compact21 BASE and all compared Compact63 prediction bytes, check intervention shapes/targets, and confirm that appended future rows with extreme feature/outcome mutations leave SCALE_ECON1BP fitted inputs and both horizons' predictions exact. These four integration tests passed; 13 target tests and nine quantizer tests also passed. A reduced two-round smoke execution of the actual benchmark runner completed for all seven variants. Reduced rounds are used only in synthetic testing; the frozen experiment remains 360 rounds. This is not a new full raw future-mutation/truncation replay: no claim of a new dynamic full-pipeline causality PASS is made here.

## Frozen benchmark outcome — independently verified

GitHub run `37167010405` completed all seven frozen 2017–2026 benchmark variants successfully. Persisted BENCHMARK.json blob SHA is `f0d85116b1b8691913a967e820a35de483966b50`. The independent audit recomputed annual/pair aggregates and the advancement gate from individual cells, found no discrepancy with the summary, and verified common input hashes/year folds across variants. All maturity and exact repeated-fit determinism checks pass.

| Variant | Rank MAD improvement | Common Top1 disagreement | Native Top1 disagreement | NDCG@5 | Advance |
| --- | ---: | ---: | ---: | ---: | --- |
| BASE | 0% | 49.4444% | 49.4444% | 0.546566 | Control |
| Q4 | 7.5944% | 52.7778% | 52.7778% | 0.554519 | No |
| ORDINAL | 8.7188% | 51.1111% | 51.1111% | 0.547736 | No |
| ECON1BP | 8.8977% | 48.8889% | 48.8889% | 0.549085 | No |
| Q4_ECON1BP | 2.7985% | 51.3889% | 51.3889% | 0.550257 | No |
| SCALE | 10.2782% | 49.1667% | 49.7222% | 0.547624 | No |
| SCALE_ECON1BP | 10.5094% | 50.8333% | 50.8333% | 0.545585 | No |

All six challengers fail the preregistered minimum 25% rank-MAD improvement. Several also worsen Top1 disagreement. The quality floor passes for every variant; it does not override the stability failure. SCALE's common-input Top1 gain is small and its native-input Top1 disagreement worsens. No challenger advances. The full replay matrix correctly contains only three unconditional controls (BASE, Q4 and Q4_LEGACY), each on three raw snapshots.

Pair-specific inspection matters. On pair 1–3, BASE Top1 disagreement is 42.5%, versus ECON1BP 52.5%, ORDINAL 57.5% and SCALE 47.5%, despite some more favorable aggregate means across all pairs. These are monthly query disagreements, distinct from later daily strategy leader disagreements.

Mean training pair-relation disagreement falls from approximately 1.41553e-5 for canonical labels to 9.82932e-6 for ORDINAL and 9.95131e-6 for ECON1BP. Dense integer-ID disagreement is much larger because occupied label levels can renumber; it should not be interpreted as equivalent changes to pairwise learning relations. Reduced relation disagreement does not translate into adequate fitted-ranker convergence in this test.

The scale quantizer's step for every feature is identical across all three snapshots in every annual fold. Thus the observed failure of these SCALE recipes is not attributable to IQR crossing a dyadic step boundary in the tested data. Residual feature/value bin-boundary changes, pair-relation changes and their fitted-tree interactions remain; this benchmark does not separately attribute their shares.

This rejects the specific fixed recipes, not all quantization, all alternative targets or the untested hypothesis of a measured-noise-aware transform. SCALE is a scale-resolution proxy and never estimated a vendor noise floor. Original149 remains burned development evidence.

## Full raw replay outcome — independently verified

All nine raw replay jobs and the full summary completed successfully in GitHub run `37167010405`. The persisted FULL_REPLAY.json blob SHA is `04040d51398fe711a76350baa5e20047d2126e5a`. The independent audit downloaded and inspected every raw replay ZIP, recomputed CAGR spans/means and daily leader disagreements directly from their metrics/CSVs, and found no discrepancy with the final summary. Each replay covers the same 2,366 dates; there is no duplicate-date or silent inner-join loss. Compact21/Compact63 strict fit-exit maturity and the retained MA3 ensemble maturity audits all pass.

| Replay | Repeat | CAGR | MaxDD | Sharpe | Annual turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| BASE | 1 | 29.7534% | -34.8621% | 1.04611 | 12.94384 |
| BASE | 2 | 30.8437% | -25.6896% | 1.08699 | 12.96048 |
| BASE | 3 | 34.6771% | -36.0975% | 1.18293 | 13.23132 |
| Q4 and Q4_LEGACY | 1 | 28.8182% | -31.0687% | 1.04241 | 13.16436 |
| Q4 and Q4_LEGACY | 2 | 27.9886% | -34.9213% | 1.00753 | 13.12205 |
| Q4 and Q4_LEGACY | 3 | 30.2336% | -36.0048% | 1.09054 | 13.92485 |

Q4 and Q4_LEGACY have exactly identical metrics, all daily leaders and Titanium output hashes for every repeat. Thus incidentally rounding the inactive Compact63 horizon in the old recipe has no effect on this observed baseline replay. Their economic values reproduce the old Q4 result.

The new BASE CAGR span is 4.923631 pp and mean CAGR 31.7581%; Q4/Q4_LEGACY span is 2.244969 pp and mean CAGR 29.0134%. The span reduction is 54.4042%, but mean CAGR falls 2.74464 pp to approximately 91.3577% of BASE, below the frozen 95% floor. Mean pairwise daily Top1 disagreement rises from 31.3750% to 34.0941%, an increase of 2.71908 pp. The economic robustness gate therefore fails on both decision convergence and mean CAGR even before the unresolved evidence issue below.

### MA3 evidence issue remains unresolved

The MA3 pickle byte hash differs from its same-repeat BASE in three outcomes: Q4 repeat 2, Q4 repeat 3 and Q4_LEGACY repeat 2. Accordingly `ma3_features_preserved` is false and ALL_EVIDENCE_PASS remains false for both Q4 variants. All other reported evidence checks pass, including same raw files/canonical source, source-only regeneration flags, preserved Compact63 predictions for isolated Q4, unchanged negative feedback and strict maturity.

The retained ZIPs contain the result, daily leaders, input contract and ensemble fit audit; they do **not** retain RAW_FEATURE_PANEL.pkl or a value-level MA3 fingerprint. Therefore this audit cannot distinguish a semantic feature difference from a serialization, floating-point representation or runtime artifact. Inspection of the builder found no timestamp/path metadata written into the DataFrame; cluster construction sorts set-derived ticker lists and uses a fixed seed. Those source observations and identical economic outcomes do not prove semantic equality of the missing panels. No gate is relaxed, no equality claim is substituted for the failed hash check, and no new regeneration is used ex-post to rescue this result.

### Final disposition

No challenger passed the benchmark advancement gate, and Q4's unconditional full replay control failed the fixed economic/decision gate. All preregistered outcomes, including failures and the unresolved MA3 evidence flags, remain recorded. This line supplies engineering evidence and does not justify strategy promotion or production adoption. A future measured-noise experiment or alternative learner requires a distinct preregistration and new validation; no threshold or recipe is changed here.
