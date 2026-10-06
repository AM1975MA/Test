# COMPACT21_BLOCKBAG_V1

Registered on 2026-10-06 before any candidate fit or access to its prediction outcomes. This protocol follows observed learner-swap, factorial and semideviation development results. It is a new, single-recipe development experiment on a previously researched history, not a pristine holdout or a retrospective claim of familywise significance. Record the registration file SHA256, source commit, actual run identity and manifests before execution.

## User objective and priority

First reduce the sensitivity of Compact21 to independent downloads of the same historical market data acquired close together. Preserve at least similar ticker-selection predictive quality relative to the original BASE/XGB; improvement is preferable. Stability here means agreement between the three frozen repeated-download snapshots on the same signal dates and universe. It does not mean constancy across genuinely different market dates, regimes or returns.

The three retained repeats are the original repeatability snapshots from raw run 37121749852; diagnostic TI panels come from run 37150436612. The user's motivating observation is downloads separated by seconds. The retained source workflow `.github/workflows/gap-analysis-yfinance-repeatability-v1.yml` executes Acquisition 1, 2 and 3 sequentially in one job with identical Original149/start/end contracts and no inserted delay between acquisition steps; `gap_analysis/protocols/YFINANCE_REPEATABILITY_V1.md` explicitly registers three sequential acquisitions in one CI job. Exact acquisition intervals have not yet been independently established from the local retained raw files, which contain no acquisition-timestamp manifest; a complete 149-ticker batch itself takes time, so do not claim an independently measured seconds interval without recovering direct evidence. That provenance limitation does not change the paired-snapshot test.

Near agreement of model predictions is necessary but does not prove near agreement of complete strategy decisions, weights or performance. Only a later unchanged full replay can establish that. Do not select or repair a predictor using CAGR. Negative feedback, Compact63, Tail, MA3, strategy blends and all downstream rules remain unchanged. There is no automatic adoption.

## One frozen candidate

BLOCKBAG retains the original 125 unquantized features, original native eligibility/cohorts, rounded relevance labels, canonical XGB ranker parameters, 360 rounds, seeds 101/202/303 and annual fitting schedule. It averages four fixed ensembles fitted with different temporal-query weights. No new feature transformation, label smoothing, early stopping, parameter search or alternative bag count/block length is introduced.

For each fit year 2017 through 2026:

1. Apply the existing eligibility and strict maturity gates first: valid original target, at least 30 valid original features, signal_date and actual exit_date_21 strictly before January 1 of the fit year. Sort canonical training rows by signal_date,ticker. Keep all original row keys and query groups.
2. Obtain the ordered monthly training-query dates. Require identical ordered query keys and group row counts across the three vintages; otherwise stop rather than silently changing the sampling population. Verify calendar adjacency for the block construction; do not bridge missing months. The frozen snapshots are expected to satisfy this requirement.
3. With N queries and block length L=3, for bag replicate b in 0,1,2,3 construct a fresh NumPy default_rng(SeedSequence([20261005, fit_year, b])). Draw ceil(N/3) integer starts uniformly, with replacement, from 0 through N-3 inclusive. Concatenate the complete three-consecutive-query index blocks in draw order and truncate the concatenation to its first N indices. Use bincount with minlength=N to obtain one float64 nonnegative weight per query. Their sum must be N. Zero weights are permitted and retained.
4. Use exactly the same bag weights for all three vintages and for all three canonical seeds. Construct the original QuantileDMatrix from the full training cohort and original labels **without weights**, then set original query groups, then attach the float64 query-group weights using set_weight. The original unweighted quantile sketch/cuts remain shared with BASE; weights alter the query loss contribution after matrix construction. This is loss-query weighting, not a weighted-quantile bootstrap. Construct the test QuantileDMatrix with that training matrix as its reference. Preserve all rows, all groups and their original order; do not expand/duplicate rows or delete zero-weight groups.
5. Fit all three original seeds separately for each bag; average their raw float32 score vectors in canonical seed order using the original NumPy mean behavior (float32 accumulation/result). Then average the four bag score vectors in replicate order, with uniform weight and explicitly float64 accumulation, and cast the result to canonical float32. No score standardization, percentile averaging, stacking or vintage averaging is added. This is 12 seed models per annual/vintage fit rather than BASE's three, an explicit additional-compute intervention.

Retaining original rows does not retain effective training support: zero query weights exclude that query's objective contribution, and positive weights reweight other queries. Weighted ranking is not assumed numerically or scientifically equivalent to duplicating sampled queries. The treatment changes query weighting and ensemble composition jointly; do not describe it as a pure parameter-free noise correction.

## Inputs, numeric profile and controls

Use the same three original TI panels and original Repeat2 common-inference matrix. Preserve native inference keys and features for each vintage, signal cutoff 2026-06-30, quality outcomes mature by 2026-07-01, annual maturity, targets, all pairs 1-2/1-3/2-3, and all date weights from COMPACT21_PREDICTIVE_V2. Reuse its deterministic ticker tie-break and average-tie percentile ranks. Future targets never determine inference eligibility.

Use the old pinned Ubuntu/Python3.13 numeric profile, including numpy2.3.5, pandas2.2.3, xgboost3.1.3, sklearn1.8.0, scipy1.17.0, pyarrow23.0.1, lightgbm4.6.0, numba0.65.1; AVX2/Haswell, all numeric/XGB threads one and the frozen AVX512 disable list. Compare actual normalized dispatched numeric profiles against retained V2 contracts, with raw profiles retained. Do not silently fit candidate models in a different local Python runtime.

Before fitting any candidate in a year job, reproduce all three old BASE vintage fits and require prediction-byte equality for both native and Repeat2 common frames against retained V2 references. Then fit the canonical XGB path with float64 all-one query weights for all three vintages and require byte-identical predictions against the unweighted BASE vectors. Additionally aggregate four identical copies of each all-one control vector using the registered float64 inter-bag mean followed by float32 cast, and require exact bytes against original BASE. This checks the aggregation operation separately from the weighted training path before candidate fitting. An all-one or aggregator mismatch blocks candidate execution; neither a close score nor a matching Top1 is an adequate control. Preserve the same ordering and averaging convention in the weighted and original paths.

Independently refit the entire BLOCKBAG candidate for every year and vintage, using the same registered weights, and require exact native and common prediction bytes. This refit is not a re-use of fitted objects or score files. Record each bag's weights and SHA256, ordered query and row-key hashes, original feature and label hashes, individual seed fitted-state fingerprints where supported, individual bag score vectors, final vectors, runtimes and input/profile/source fingerprints. Write input and registration contracts before fitting. Require complete 10-year by 3-vintage evidence, no missing pairs, finite scores, exact original keys/targets, strict maturity and preserved native coverage. Any integrity/control failure invalidates comparative conclusions even if aggregate metrics appear favorable.

## Stability measurements: first gate

Compute stability on every eligible inference date, including dates whose future outcomes are not yet mature, with equal weight per date. For common-input metrics compare separately trained vintage models on exactly the original Repeat2 inference features/keys; for native-input metrics align the two original native frames, preserve coverage evidence and require no unexpected key loss. Within each pair retain date-level rank MAD, Spearman, deterministic Top1 disagreement and Top5 Jaccard/overlap. Aggregate dates before giving the three pairs equal weight. Report all individual pairs and year-level diagnostics.

Apply two distinct engineering classifications; never call the weaker one a resolution of the user's problem:

- **STABILITY_PILOT_PASS:** common-input rank MAD is at least 25% below fresh BASE, native-input Top1 disagreement is at least 25% below fresh BASE, and every individual pair is no worse than BASE on both metrics. All integrity/control requirements must pass. This is a useful improvement threshold reused from the earlier development protocol, not sufficient near repeatability.
- **MODEL_NEAR_REPEATABILITY_PASS:** native-input Top1 disagreement is at most 5% for each of the three pairs, and common-input rank MAD for each pair is at most 10% of its corresponding fresh BASE value (at least 90% reduction). All integrity/control requirements must pass. These are fixed operational engineering thresholds registered before BLOCKBAG outcomes; they permit residual disagreement and are not an assertion of exact identity or completed full-strategy reproducibility.

When a corresponding BASE denominator is zero, require candidate zero; do not treat an undefined reduction as a pass. Use unrounded values for every boundary. Report common Top1 disagreement, native rank MAD, Top5 agreement and rank distribution tails even though they are not additional registered gates. A low mean MAD may coexist with changes at the ranking head; the native Top1 threshold directly guards that head.

## Predictive preservation and improvement: second gate

Primary quality is the V2 equal-date, equal-vintage mean realized target_rank_21 of the predicted Top1. Preserve each vintage's individual primary metric. Secondary metrics are true-Top5 and top-decile Top1 hits, Precision@5, NDCG@5/@10, Spearman IC, verified realized-return regret and year-level paired effects. Use identical original mature outcome rows, original labels and deterministic ticker tie-breaks. Do not replace a failed Top1 endpoint with a favorable NDCG or CAGR.

For **QUALITY_SIMILAR_PASS**, require all of:

1. Overall candidate Top1 primary is at least 95% of fresh BASE's overall primary.
2. Each vintage's candidate primary is at least 95% of its own fresh BASE primary.
3. Overall candidate Precision@5 is at least 95% of fresh BASE Precision@5.
4. The paired 3-month-block bootstrap one-sided 95% lower bound for candidate-minus-BASE primary is strictly greater than -0.05 times BASE's overall primary.
5. All integrity and control requirements pass.

The 95%-of-BASE preservation concept was present in COMPACT21_LEARNER_SWAP_V1 before these outcomes. This experiment makes the relative margin explicit and adds paired uncertainty and vintage guards; it does not assert that the old protocol already contained these exact new tests. This is an engineering definition of similar quality, not proof of equality. Report the actual allowed absolute margin and observed difference. Precision@5 by vintage remains mandatory reporting; its registered preservation gate is overall.

Separately evaluate **QUALITY_IMPROVED_PASS** using the old V2 stricter development rules: positive overall primary difference, conservative paired bootstrap lower bound at percentile 1.25% strictly above zero, each vintage primary at least its BASE, and overall Precision@5 at least BASE. Require STABILITY_PILOT_PASS and all controls jointly for an improved-and-stabler development classification. Retaining the old conservative percentile does not establish familywise error control over this adaptive history of experiments. No model may be promoted or called superior merely for passing QUALITY_SIMILAR_PASS.

The strongest requested provisional outcome is MODEL_NEAR_REPEATABILITY_PASS together with QUALITY_SIMILAR_PASS; append whether stricter improvement also passed. STABILITY_PILOT_PASS with preserved quality warrants further research but does not resolve the original severe repeat-download instability. Report failed gates explicitly; no compensating weighted score can rescue a failure.

## Paired uncertainty

For each common mature date, compute candidate-minus-BASE Top1 realized percentile separately within vintage and average the three differences. The three vintages are dependent observations of one history, not three independent market trials. Keep the complete paired date vector.

Use the unchanged V2 noncircular moving calendar-block procedure: 3 consecutive months, 20,000 bootstrap resamples, NumPy default_rng(seed=20261004), concatenate sampled complete blocks then truncate to the original date count. The same date sample applies to every vintage jointly. Preserve the existing V2 handling of any missing calendar months; do not silently treat gaps as adjacent. Report mean difference, two-sided 95% percentile interval, one-sided lower 95% bound at percentile 5%, and conservative lower bound at percentile 1.25%. Lengths 1 and 6 are fixed sensitivity reports using the same seed and cannot replace a failed primary length-3 gate. The fitting sampler seed 20261005 is distinct from this outcome bootstrap seed.

These intervals summarize conditional historical uncertainty and dependence assumptions. They do not establish performance in an untouched period, independence of vintages, or significance across all previous adaptive searches.

## Execution, checkpoint and next decision

Execute this one candidate and report all results, including failures. Do not change four bags, three-month blocks, seeds, parameters, endpoints, margins, cutoffs or weighting after consulting candidate outcomes. Scientific changes require a new prospective protocol. Execution-only corrections must be documented with timing, affected artifacts and consistent rerun scope.

Save a checkpoint with source/run/registration identities, control and refit parity, stability and quality by pair/vintage/year, uncertainty, runtime increase, all failed or unavailable endpoints, anomalies and one next recommended experiment. Adoption remains false. Any later complete replay must preserve the original pair/cutoff and demonstrate unchanged Compact63/Tail/MA3 evidence and feedback before a deployment recommendation. A new acquisition batch and an unconsulted forward period with mature labels remain necessary external confirmation; an additional vintage alone tests revision robustness, not fresh temporal predictive validity.
