# COMPACT21_PREDICTIVE_V2 — independent audit plan

This plan is frozen with PREREGISTRATION.md on 2026-10-04 before inspecting new-variant outcomes. Audit code, data contracts and interpretation before granting comparative claims. No learner promotion, negative-feedback modification or new threshold follows from this audit.

## 1. Provenance and exposure

- Verify actual new run/commit, source blob, raw/diagnostic ZIP digests, retained panel semantic hashes, canonical ordered keys and runtime identity. Never invent a run ID or label old results as new execution.
- Require new-run source fingerprints and retained native individual and common-input prediction vectors for each model/year/vintage, with keys, mature targets and fitted-state fingerprints. Summaries alone cannot certify outcome identity.
- Verify input runs 37150436612 (diagnostic) and 37121749852 (raw), the recovered old controls from 37195399755 and their separation from failed/partial earlier jobs.
- State explicitly that all Original149 historical periods and old controls have already been observed. The two new recipes are preregistered development experiments, not independent confirmation on an untouched dataset.
- Preserve scientific parameter freeze and record execution-only amendments with the outcome-access timeline. Record every candidate, even if it fails, errors or has unavailable metrics.

## 2. Model recipe verification

- BASE: isolated canonical XGB parameters/rounds/seeds and averaged prediction behavior identical to old control.
- RIDGE: median imputation -> StandardScaler -> Ridge(alpha=30), continuous percentile label, identical missingness and intercept behavior.
- LGBM_LAMBDARANK: old recipe with explicit truncation 30, and verified parity with its old implicit default. Confirm actual booster parameters and pinned LightGBM4.6.0, not only caller arguments.
- LGBM_TOP5: only registered change from that control is truncation 8. Integer labels and gain 0..100 remain identical.
- ADDITIVE_RIDGE: median imputation -> StandardScaler -> independent univariate SplineTransformer(n_knots=4,degree=3,knots='quantile',include_bias=False,extrapolation='linear') -> StandardScaler -> Ridge(alpha=30), continuous percentile target. No interactions, hidden tuning, score clipping, validation-selected knots or test-fitted transforms.
- Record dimensions, training-only fitted state, all-missing and constant columns, raw/transformed matrices and per-seed prediction hashes. Test that a future/test-row change cannot alter fitted imputer/scaler/knots/coefficients.

## 3. Rowsets, time and numerical reproducibility

- Verify every annual cutoff, strict signal/exit maturity, target bounds, native training cohorts and ordered groups. Do not intersect training cohorts.
- Validate common Repeat2 inference and native aligned comparisons separately, all years/pairs, with no silent inner-join losses. Keep inference eligibility independent of future-label availability; maturity is an evaluation gate.
- Verify the fixed inference cutoff 2026-06-30 and outcome cutoff 2026-07-01. Report actual mature date counts and partial 2026 coverage.
- Verify pinned packages, effective common SIMD/OpenBLAS profile and one-thread constraints on every worker/preflight. A local bundled runtime used only to inspect artifacts must not be mislabeled as the fitted environment.
- Reproduce all old control outcomes before comparative claims; exact old prediction parity is preferred where predictions are retained. If only metric-level parity can be checked, explicitly label that evidential limit. A mismatch is a blocked control, not an unfavorable new candidate screen.
- Independently refit Repeat2 for every model/year and require exact arrays. Reject duplicate keys, nonfinite predictions, missing/duplicate years/pairs and mismatched target/evaluation support.

## 4. Metric verification

- Build and retain per-date/per-vintage records of predicted Top1, target percentile, Top1 top-decile hit, Top1 realized-Top5 hit, predicted/realized Top5 sets, precision@5, NDCG@5/@10, IC and raw-return regret availability.
- Verify descending-score order and deterministic ticker tie-break, exact cardinalities and target ties at boundaries. NDCG uses the existing linear percentile gain. Ensure a stability Spearman is not mislabeled as target IC.
- Independently recompute equal-date primary and secondary metrics, same-vintage values, equal-pair stability aggregates and legacy equal-year diagnostics. Confirm that 2026 receives weight proportional to its mature dates in the primary endpoint.
- Raw economic regret is valid only with a verified raw 21-session execution return. Never reconstruct economic gaps from rank percentiles, and never hide unavailability with zero values.
- Interpret exact winner hit, top-decile selection and realized regret separately. Stable ticker changes can be economically benign or costly; score margins alone establish neither case.

## 5. Bootstrap and selection guard

- Retain ordered paired candidate-minus-BASE date vectors for each vintage and their within-date mean. Apply identical sampled date indices to every candidate/vintage; do not resample ticker rows or vintage IDs independently.
- Recompute noncircular moving-block bootstrap L=3, B=20,000, default_rng(20261004), full blocks concatenated then truncated to N. Verify calendar adjacency if dates are missing and reject silent bridging of gaps.
- Independently reproduce point differences, two-sided percentile 95% CIs, one-sided95% lower bounds and one-sided Bonferroni familywise conservative 98.75% lower bounds for four challengers. The conservative L=3 lower bound governs superiority, not the most favorable interval.
- Report registered L=1/L=6 sensitivities, temporal nonstationarity and finite-sample limits. Do not present this bootstrap as correction for the entire prior research history or as evidence from independent markets.
- No p-value or confidence calculation from three pair spans, 30 annual-vintage cells or replicated same-market snapshots is valid merely because those counts look large.

## 6. Gate truth table

Independently recompute every preregistered conjunctive gate at unrounded precision: controls/evidence, primary positive conservative bound, every-vintage Top1 noninferiority, zero-tolerance Top5 precision noninferiority, at least25% common-input rankMAD reduction AND at least25% native-input Top1-disagreement reduction, with every-pair no worsening for both gated metrics. Common Top1 disagreement, native rankMAD and stability Spearman remain reported diagnostics; do not accidentally invent additional superiority gates in the implementation. For zero BASE denominators require zero candidate, not an arbitrary ratio. No IID or independent-vintage guarantee is implied.

Test rejection cases that matter: stable constant/flat predictions with weak selection; improvement only in one vintage; aggregate gains masking pair failure; bootstrap family correction omitted; partial2026 incorrectly weighted equally; NDCG passing while primary fails; CAGR used to rescue a failed predictive candidate; absent/invalid evidence treated as pass. Verify exact boundary behavior and report all failure reasons.

No performance gate is relaxed after outcome access. A candidate passing the historical development gates is not an adopted strategy; a candidate failing them remains in the report.

## 7. Complete replay and invariance, if executed

- Use raw inputs and same registered source/profile, not saved diagnostic panels. Keep all components except Compact21 identical to same-vintage BASE.
- Reconstruct actual Compact63 matrices/labels/groups/predictions, Tail predictions, MA3 schema/keys/dtypes/missing masks/value bits and annual component predictions. Verify actual semantic artifacts; byte serialization hashes are separate diagnostics.
- Preserve negative feedback, canonical blend/normalization, eligibility, allocation/risk and execution. Keep the historic unretained MA3 discrepancies unresolved rather than retrospectively relabeling them PASS.
- Recompute full daily decision comparisons, CAGR, maximum drawdown, turnover/scale and snapshot span. Report the exact replay period/date count. Connect large economic divergence to actual Top1/Top2/weight transitions and path effects.
- Do not select recipes or parameters by these economic outcomes. If no predictive candidate qualifies, state that clearly even if an unconditionally executed replay has favorable CAGR.

## 8. Report and next decision

Deliver source-backed results with per-year/per-vintage/per-pair tables, uncertainty and failure reasons; distinguish completed checks from unavailable or planned evidence. Record the next experiment and unresolved anomalies. Require a new data vintage for fresh revision sensitivity and mature unconsulted forward outcomes for future predictive confirmation. Preserve all new panels/predictions/manifests so later parity and propagation questions remain verifiable. Production adoption remains false.
