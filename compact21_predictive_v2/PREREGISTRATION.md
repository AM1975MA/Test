# COMPACT21_PREDICTIVE_V2

Frozen 2026-10-04 before inspecting any outcome of the two new variants in this line. The fixed controls have already been observed in COMPACT21_LEARNER_SWAP_V1. This is a prospective protocol for a new development comparison, not an untouched historical holdout.

## Objective and scope

Test whether Compact21 can improve the realized quality of its selected ticker while reducing sensitivity to the three frozen historical data vintages. Predictive selection quality comes before complete-strategy CAGR. A stable but less useful predictor does not qualify. No model is automatically adopted, no hyperparameter is selected from CAGR, and negative feedback remains unchanged.

Preserve the canonical 125 unquantized features, native eligibility, annual fitting schedule, target/outcome horizon of 21 trading sessions, seeds, source snapshots, all three snapshot pairs, inference rowsets and cutoffs. Keep Compact63, Tail, macro, MA3, component percentile normalization, blends, allocation, execution and risk rules unchanged in any complete-strategy replay. No feature quantization, arbitrary synthetic perturbations, new ensemble weights, feedback change or parameter search is introduced.

## Provenance and inputs

- Old diagnostic panels: TI_COMPACT.parquet from GitHub run 37150436612, repeats 1/2/3.
- Frozen raw snapshots for complete replays: GitHub run 37121749852, repeats 1/2/3.
- Recovered old-control outcome run: 37195399755. Its source commit is efe2ae9fd30c2be8413b4a074d0f25db5410988f; the recovered checkout was 74ef7c0a99ee14bae3b6134c74dbc3ca8cf0261c.
- The canonical comparison source blob recorded in the prior protocol is ebd578e0d92e986adb5c2fbf265a346f87b7218e.
- No new run ID, new commit SHA or new outcome is known at registration. Record those actual values at execution; do not reuse old metadata as the identity of a new run.

Manifest hashes and source/runtime identities must be written before model fitting. Retain a source fingerprint, fitted-state fingerprints, native individual prediction vectors for each model/year/vintage, common-input prediction vectors, canonical keys and mature targets. Summary metrics alone are insufficient new-run evidence. Benchmark panels are diagnostic inputs and never substitutes for raw inputs to a complete replay. Do not combine partial outcome artifacts from different runs.

## Fixed five-model matrix

| Variant | Fixed model and transform | Training target |
| --- | --- | --- |
| BASE | Canonical isolated XGB worker; unchanged COMPACT_PARAMS, 360 rounds and seeds 101/202/303 | round(target_rank_21 * 100) |
| RIDGE | Median SimpleImputer, StandardScaler, Ridge(alpha=30) | Continuous target_rank_21 |
| LGBM_LAMBDARANK | Old frozen LightGBM recipe, now explicitly lambdarank_truncation_level=30 | Canonical rounded integer relevance |
| LGBM_TOP5 | Same frozen LightGBM recipe with only lambdarank_truncation_level=8 | Canonical rounded integer relevance |
| ADDITIVE_RIDGE | Median SimpleImputer -> StandardScaler -> SplineTransformer(n_knots=4, degree=3, knots='quantile', include_bias=False, extrapolation='linear') -> StandardScaler -> Ridge(alpha=30) | Continuous target_rank_21 |

The additive pipeline contains separate univariate spline bases with no interaction expansion. Both scalers, imputer, spline knots and Ridge coefficients are fitted on mature annual training rows only. Preserve Ridge intercept behavior and canonical missing-value handling. Record retained feature dimensions and all fitted transform state, including all-missing/constant columns; do not silently invent a new missingness recipe. No clipping or calibration of continuous predictions is added before the canonical component percentile normalization.

Both LightGBM variants use objective=lambdarank, n_estimators=360, learning_rate=.035, max_depth=4, num_leaves=15, min_child_samples=40, subsample=.85, subsample_freq=1, colsample_bytree=.8, reg_lambda=8, reg_alpha=.1, label_gain=0..100, n_jobs=1, deterministic=true, force_col_wise=true. Fit seeds 101/202/303 separately and average predictions as in the old control. No early stopping or internal parameter search. Truncation 8 is a single registered top-focused intervention; its merit must be measured, not assumed from its name.

Ridge/additive comparisons change learner and target representation relative to BASE. The LightGBM pair isolates the registered truncation change within its recipe. No pure learner-only causal attribution is claimed for the whole matrix.

## Temporal protocol and numerical controls

Annual expanding fits cover 2017-2026. Each vintage retains its own training cohort, sorted by signal_date,ticker, with nonmissing target and canonical at least 30 valid features. Both signal_date and exit_date_21 must be strictly before Jan1 of its fit year. Do not intersect training cohorts. Fit transformations only after the maturity gate.

Inference signals end 2026-06-30. Quality evaluation uses outcomes mature by 2026-07-01 and the same native rowset for every model within each vintage. Future labels must not select inference eligibility. Primary common-input stability uses the frozen Repeat2 inference frame for each independently fitted vintage; native-input stability aligns diagnostic keys and reports coverage. Evaluate pairs 1-2, 1-3, 2-3 and all annual cells.

Use the same pinned prior numerical environment and common AVX2/Haswell profile: Python3.13, numpy2.3.5, pandas2.2.3, scikit-learn1.8.0, xgboost3.1.3, lightgbm4.6.0, scipy1.17.0, pyarrow23.0.1, numba0.65.1; all worker and MA3/ExtraTrees numerical threads one; PYTHONHASHSEED=0; OPENBLAS_CORETYPE=Haswell; NPY_DISABLE_CPU_FEATURES=AVX512F,AVX512CD,AVX512_KNL,AVX512_KNM,AVX512_SKX,AVX512_CLX,AVX512_CNL,AVX512_ICL,AVX512_SPR. Record actual host and runtime profiles, not only environment variables.

Before claims about new-model quality, reproduce old BASE, RIDGE and LGBM_LAMBDARANK controls under this profile. Require exact same-input predictions and semantic rowsets/targets against retained old predictions where available; otherwise require exact reported old per-year/per-vintage quality and stability metrics and mark prediction-level reproduction unavailable. Verify that explicitly setting truncation 30 reproduces the old LightGBM default. A mismatch blocks comparative claims until explained and repaired consistently across all models. Do not loosen a gate or change a candidate after seeing its new quality.

Repeat2 must be independently refitted each year with exactly equal prediction arrays. Nonfinite outputs, duplicate/missing keys, missing folds/pairs, maturity failures or unexplained coverage loss fail evidence validation.

## Prediction metrics and weighting

Primary endpoint is the mean realized target_rank_21 of the predicted Top1, giving each mature signal date equal weight. Within a date, each of the three vintages has equal weight. Report the same metric separately for each vintage. Preserve the old equal-year aggregate as a labeled secondary diagnostic; a partial 2026 fold must not receive the same primary weight as a complete year.

Evaluate Top1 by descending model score and canonical ticker tie-break. Document ties and use this same rule in stability and quality calculations. For a date with N eligible candidates, define realized Top5 as the first min(5,N) by descending target_rank_21 with the same ticker tie-break, and realized top decile as the first max(1,ceil(.1*N)). Record target ties at these boundaries. Report these fixed-cardinality metrics separately from any tie-inclusive diagnostic.

Secondary date-weighted endpoints:

- Top1 hit rate in the realized top decile and exact realized Top5.
- Precision@5 = overlap of predicted and realized Top5 divided by min(5,N). Preserve the original top5_realized_overlap definition for parity on unchanged N.
- NDCG@5/@10 with the existing linear 0..1 percentile gain, and per-date Spearman IC. NDCG is not a winner accuracy or probability.
- If a retained panel actually contains a verified raw 21-session return target with the same execution definition, report regret against the maximum return and separately against mean realized top-decile return. Do not infer raw returns from percentile labels; if unavailable, label raw-return regret unavailable and do not replace it with a mislabeled rank difference.
- Counts and coverage by year/date/vintage, observed primary worst-vintage result, mean/median and year-by-year paired differences. Report a theoretical or empirical random comparator only with its actual definition and candidate counts.

Secondary endpoints are descriptive unless explicitly used in the gates below. They cannot replace a failed primary endpoint. Report all five models, including failures.

## Paired uncertainty calculation

For each common mature date, calculate the candidate-minus-BASE Top1 percentile difference separately in each vintage, then average the three paired differences for that date. Retain the complete paired date vector; the vintages are not independent replicates and are never independently resampled.

Use a noncircular moving-block bootstrap of the ordered monthly date vector: fixed block length 3 consecutive observations/months, 20,000 resamples, NumPy default_rng(seed=20261004). Draw block starts uniformly from 0..N-L inclusive with replacement, concatenate complete blocks and truncate to N observations. The same sampled date indices apply jointly to every variant and vintage. Never resample ticker rows or three vintage IDs as independent observations. Missing calendar months require reporting and block construction by calendar adjacency; do not silently bridge a gap.

Report the paired mean difference, ordinary two-sided percentile 95% interval (2.5%/97.5%), one-sided 95% lower bound (5%), and a simultaneous-promotion conservative lower bound at the 1.25% percentile (Bonferroni one-sided familywise 5% over four challengers). The latter is the primary superiority gate. Fix the resampling procedure and family size before new outcomes; do not choose whichever CI is favorable.

Repeat the same bootstrap descriptively with block lengths 1 and 6 using the same fixed seed, and report their conservative lower bounds. These are sensitivity analyses, not substitute acceptance tests. Temporal nonstationarity, overlapping information and the limited 113 historical monthly dates constrain these intervals. They quantify conditional historical sampling uncertainty; they do not establish significance after all prior development searches or forward generalization.

## Conjunctive development-qualification gates

A challenger is a DEVELOPMENT_CANDIDATE only if ALL requirements pass:

1. Reproduced controls, complete evidence, strict maturity, exact independent refit determinism and declared numeric/input contracts pass.
2. Date-weighted primary Top1 improvement is positive and its conservative paired 3-month-bootstrap lower bound is strictly above zero.
3. Each of the three vintages separately has date-weighted Top1 percentile at least its same-vintage BASE (absolute noninferiority tolerance zero). This protects against an average driven by a gain in one vintage and sacrifice in another; three positive signs do not establish independent replication.
4. Date-weighted Top5 precision/overlap is at least BASE (absolute tolerance zero). Retain the legacy equal-year overlap report, but do not apply it instead of the fixed primary weighting.
5. Date-weighted common-input rank MAD falls by at least 25% versus fresh BASE AND date-weighted native-input Top1 disagreement falls by at least 25%. Average the three pair values equally after weighting their dates equally. Each individual pair must be no worse than BASE for both gated metrics. If a BASE denominator is zero, the corresponding candidate must also be zero; no undefined percent ratio is treated as a pass. Common Top1 disagreement, native rank MAD and stability Spearman remain reported diagnostics, not additional unregistered superiority thresholds.

Report pair and annual detail; no rescue by aggregate economics. Neither date observations nor vintages are assumed IID merely to justify a confidence claim. The temporal block procedure is conditional on its dependence assumptions and is not a guarantee against regime shifts.

The percent reduction is 100*(BASE-candidate)/BASE. Use unrounded values for gate boundaries. Register any unavailable endpoint as unavailable, not pass. No result can be promoted because it passes only rank stability, only NDCG, or only CAGR. Multiple qualifying candidates remain a documented development frontier; do not select their winner from observed CAGR.

## Complete strategy and later validation

After predictive/stability gates are known, report complete raw-source replays for eligible candidates using the unchanged strategy, paired snapshots and controls. If the complete diagnostic matrix runs unconditionally for scheduling efficiency, register that purpose and keep final promotion conditional on all gates; do not exploit early economic outcomes to change or select predictors. Report decisions, CAGR, maximum drawdown, annualized turnover, Sharpe and snapshot span. Exact same-vintage Compact63/Tail/MA3 preservation is mandatory. Retain actual panels, prediction arrays, manifests and fingerprints. Old unretained MA3 discrepancies remain unresolved historical evidence.

CAGR and span here measure path sensitivity on the same historical market, not independent market trials. Explain conversion of predictive differences into decision/weight changes before recommending adoption. New vintage data and an unconsulted forward period with mature outcomes are required for a deployment recommendation. A new vintage alone establishes revision robustness, not independent temporal predictive replication. Historical universes already researched are corroborative evidence, not an untouched holdout. A further parameter search or nested temporal tuning would require a separately frozen protocol and registry; it is not authorized by this five-recipe comparison.

## Amendments and checkpoint

Only execution/integrity corrections can be made without a new scientific protocol. Document correction, timing relative to new outcome access, all affected artifacts and consistent rerun scope. Do not modify model recipes, endpoints, thresholds or weighting after observing new outcomes. Save complete outcomes including failures and a checkpoint containing provenance, control parity, prediction quality, stability, uncertainty, unavailable metrics, anomalies and the next recommended experiment. Adoption remains false.
