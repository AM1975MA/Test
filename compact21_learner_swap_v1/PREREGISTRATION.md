# COMPACT21_LEARNER_SWAP_V1

Frozen 2026-10-04 before any results from this line. Starting commit:
53f43cdd2a618609a47673ade62b3e5e45ddd6d6 in AM1975MA/Test.
Research branch: research/compact21-learner-swap-v1.

## Purpose and scope

Test whether replacing Compact21's learning formulation can reduce sensitivity
to tiny input revisions while preserving useful selection and full strategy
behavior. Original149 is repeatedly inspected development evidence. Three
downloads of the same historical market are engineering perturbations, not
three independent markets or a population variance estimate. No production
adoption, parameter optimization against CAGR, new feedback or allocation rule.

Only Compact21's learner/target formulation changes. Feature definitions and
125 unquantized inputs, native eligibility, annual scheduling, Compact63, Tail,
macro, MA3, signal blend, allocation, risk and execution remain canonical.
Canonical percentile normalization of component predictions before blending
is preserved. Negative feedback remains unchanged. The Ridge comparison changes
both learner and objective; it does not identify a pure learner-only effect.

## Frozen three-model matrix

| Variant | Compact21 learner | Training target |
| --- | --- | --- |
| BASE | Canonical XGB rank:pairwise | round(target_rank_21 * 100) |
| RIDGE | Median imputer, StandardScaler, Ridge alpha=30 | Continuous target_rank_21 |
| LGBM_LAMBDARANK | Frozen Phase B LGBMRanker | Canonical rounded labels |

BASE preserves COMPACT_PARAMS, 360 rounds and seeds 101/202/303. Ridge retains
the exact Phase B pipeline, with training-only imputation/scaling and no new
alpha search. LightGBM retains objective=lambdarank, n_estimators=360,
learning_rate=.035, max_depth=4, num_leaves=15, min_child_samples=40,
subsample=.85, subsample_freq=1, colsample_bytree=.8, reg_lambda=8,
reg_alpha=.1, seeds 101/202/303, n_jobs=1, deterministic=true,
force_col_wise=true and label_gain=0..100. No early stopping or validation-based
parameter selection. No feature quantization or new noise injection.

## Inputs, folds and execution

Benchmark diagnostic inputs: frozen TI_COMPACT.parquet artifacts from GitHub
run 37150436612, repeats 1/2/3. They are never full replay inputs.
Full strategy: frozen per-ticker raw snapshots from run 37121749852. The
canonical compare source blob is ebd578e0d92e986adb5c2fbf265a346f87b7218e.
Full features, labels, models and scores are regenerated from raw and source.

Benchmark years 2017-2026. Training retains each snapshot's own rows, sorted
by signal_date,ticker, with signal_date and exit_date_21 strictly before Jan1
of the annual fit and nonmissing target; canonical >=30 valid features.
Training cohorts are NOT intersected. Inference signals end 2026-06-30;
quality uses outcomes mature by 2026-07-01, on the same native unmodified
target and rows across models. Future labels do not select inference rows.

All three snapshot pairs are measured: 1-2,1-3,2-3. Primary common Repeat2
inference isolates fitting sensitivity; secondary native inference measures
total sensitivity, aligned only for diagnostic keys with coverage reported.
Means weight annual folds and pairs equally; per-year and per-pair values
remain visible. Repeat2 is fitted again independently in every year and must
produce exact predictions. Learned-state/future-row invariance and canonical
BASE/Compact63 parity are tested with actual synthetic worker integration.

Pinned runtime: Python3.13, numpy2.3.5, pandas2.2.3, scikit-learn1.8.0,
xgboost3.1.3, lightgbm4.6.0, scipy1.17.0, pyarrow23.0.1, numba0.65.1,
yfinance0.2.66. All numerical worker and MA3/ExtraTrees threads are one;
PYTHONHASHSEED=0. Hardware/runtime details and source/input hashes are retained.
Any infrastructure correction is documented and does not change model recipes
or acceptance thresholds after outcomes.

### Execution-only amendment, before using full-strategy outcomes

Initial CI run 37194714662 passed 45 tests and all three MA3 double-build
checks. Several full jobs were blocked before training by the declared
environment equality guard: GitHub supplied AMD EPYC7763 and Intel Xeon6973P-C
hosts with different NumPy runtime SIMD profiles despite identical wheels.
This is an infrastructure mismatch, not a candidate economic screen result.
No full-strategy outcome was used to choose the correction.

All three learners, all preflights and all nine raw replays are rerun uniformly
with OPENBLAS_CORETYPE=Haswell and NPY_DISABLE_CPU_FEATURES set to
AVX512F,AVX512CD,AVX512_KNL,AVX512_KNM,AVX512_SKX,AVX512_CLX,AVX512_CNL,
AVX512_ICL,AVX512_SPR. Both observed CPU families support the resulting AVX2
profile. Fresh-process checks on the pinned wheel verify identical declared
SIMD selection and Haswell kernels. Hardware details remain recorded and
exact semantic/preservation checks remain mandatory; this does not guarantee
cross-host equality in advance. No model, target, recipe or threshold changes.
The initial attempt and partial diagnostic artifacts are retained separately;
its results are never mixed with the corrected run. Final aggregation consumes
the benchmark artifact from its own run, independent of branch checkpoint
timing. Environment failure now retains actual and expected fields for audit.

## Diagnostics and benchmark qualification

Report percentile rank MAD, Spearman, Top1 disagreement, Top5 Jaccard,
NDCG@5/@10, target IC, Top1 realized percentile and realized Top5 overlap.
Score-margin diagnostics use an explicitly shared per-query centered/unit-RMS
scale. Record margins, observed score perturbations and sufficient-margin
fractions. margin > 2*observed_epsilon is a sufficient check for the observed
pair, not a confidence interval or universal future-noise certificate. A swap
necessarily violating that inequality does not establish economic near-parity.

A challenger qualifies only if ALL hold against the fresh BASE:

- Primary rank MAD falls at least 25%.
- Primary Top1 disagreement does not worsen.
- Primary stability Spearman does not worsen.
- Native-inference Top1 disagreement does not worsen.
- Mean native NDCG@5 is at least 95% of BASE.
- Mean native Top1 realized percentile is at least 95% of BASE.
- All annual maturity and exact repeated-fit determinism checks pass.

The added Top1 quality guard is fixed before this line's outcomes. Phase B
Ridge had similar NDCG but weaker realized winner quality; this guard avoids
equating stable ranking with useful selection. Prior Phase B numbers are
development motivation, not new-protocol results or a certified noise floor.

## Full replay matrix and semantic integrity

All NINE BASE/RIDGE/LGBM_LAMBDARANK x repeats1/2/3 full runs are unconditional
diagnostics, frozen before results, even if a benchmark gate fails. This
measures whether a stable fit preserves portfolio utility. It does NOT waive
the benchmark gate or allow CAGR to rescue a failed candidate.

Before full runs, three preflight jobs independently build canonical MA3
panels from the same raw/source, repeat construction and retain panels,
cluster memberships, maturity audits and semantic fingerprints. Full runs
regenerate their own MA3 inputs, then require exact semantic equality with
their same-repeat preflight reference. They do not consume reference panel
values to force equality. Final aggregation also compares same-repeat MA3
semantics to BASE. Schema, keys/order, dtypes, missingness and values are
checked; canonical NaN/zero representation conventions are recorded separately
from numerical tolerance. Any finite-value difference, including one ULP,
fails exact equality. File byte hashes remain separate diagnostics.

Retain RAW_FEATURE_PANEL.pkl, cluster membership, ensemble predictions,
annual Compact predictions, Titanium scores, input contracts and all fit
audits. This addresses the prior missing-artifact limitation prospectively;
it does not retroactively turn COMPACT21_STABILITY_V1's three MA3 failures
into passes. Any mismatch remains visible and blocks qualification.

Full runs preserve strict maturity for both Compact horizons and MA3. Every
challenger's Compact63 matrices, labels, groups and predictions must match its
same-repeat BASE; nonintervened components are audited. Same raw/source,
complete identical daily date/session coverage and no historical output
consumption are required. Fresh BASE uses the same execution profile.

## Full economic screen and final decision

For full diagnostic qualification ALL must hold:

- CAGR max-minus-min span <=75% of fresh BASE span.
- Mean pairwise daily Top1 disagreement <= fresh BASE.
- Mean CAGR >=95% of fresh BASE.
- Mean MaxDD is no more than 2 percentage points worse than BASE
  (signed negative MaxDD: candidate >= BASE - .02).
- Mean annual turnover <=110% of fresh BASE.
- Every source, maturity, coverage, unchanged-component and semantic-integrity
  check passes.

Joint research-candidate qualification requires BOTH benchmark and full
screens. Report every raw CAGR/MaxDD/Sharpe/turnover and daily Top1/Top2
disagreement, including failed models. There is no choice of parameters from
these economic outcomes and no production promotion. New independent or
forward evidence is required before investment use.
