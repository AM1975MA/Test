# COMPACT21_XGB75_RIDGE25_V1 — one fixed, non-tuned hybrid (2026-10-09)

## Status, question and reasons
Registered after original 3-vintage source-attribution diagnostic, the 2026-10-06 BLOCKBAG failed-quality result, and the read-only near-tie result from run 37933141010. This Original149 history is **development evidence** with accumulated multiple comparisons, not pristine out-of-sample or evidence of statistical significance. This is one frozen recipe, not a weight grid.

The high-sensitivity canonical XGB Compact21 ranker supplies predictive selectivity; the previously evaluated median-imputation/StandardScaler/Ridge(alpha=30) learner has much more stable ranking but may lose selected-Top1 quality. A fixed small Ridge contribution might break near-tied XGB scores while retaining XGB's forecast quality. That is a hypothesis, not a conclusion. No future returns are used to select weight, model, votes, tickers, or inference eligibility.

## Frozen algorithm and existing source
Inputs must be the original *full-year* native and common predictive vectors for BASE and RIDGE, each sourced from immutable GitHub Actions run 37229180477 (`predictive-BASE` and `predictive-RIDGE` artifacts), trained annually on each of three frozen TI_COMPACT source acquisitions, 2017–2026. Both artifacts must pass legacy parity, strict source and numeric contract and exact native/common keys/outcomes. No model is retrained or altered in this stage; original underlying 125 features, fit schedule, continuous Ridge labels and rounded XGB labels stay those already frozen in their respective algorithms.

On every `(vintage,signal_date)` with complete exact same ticker cohort (native separately and Repeat2 common separately), calculate within-query average-tie percentile ranks `R_XGB` and `R_RIDGE`. For every ticker define

`score = 0.75 * R_XGB + 0.25 * R_RIDGE`

Use float64 arithmetic on the two ranked percentile vectors in that exact order. For complete-score ranking use descending score, ascending ticker tie-break. No normalization, post-hoc score threshold, cross-vintage mixing, margin trigger, smoothing, horizon blend change, or use of outcomes. As a consequence this hybrid is deployable on **one contemporaneous data acquisition** (both learners trained on that one snapshot); unlike the preceding cross-vintage factorial, it does not use Repeat2's training data for a different native vintage.

## Gated endpoints (preregistered)
Compare to original BASE on same 114 monthly signal dates for each pair (1,2),(1,3),(2,3); common inference fixes Repeat2 feature inputs, native inference uses original each-vintage eligibility. Retain exact per-date and per-pair source matrices, no key loss, no target/exit/value corruption, no missing years, identical maturity and fingerprints. Independently recompute baseline stability from physical score vectors.

The joint preregistered **pilot stability** criterion (unchanged from BLOCKBAG prior work) requires (a) common mean rank-MAD <=75% BASE, (b) native mean Top1 disagreement <=75% BASE, (c) none of the three pair-specific common rank-MAD or native Top1 disagrees more than BASE. Report native/common all pair metrics, Top5 and year distribution.

The joint **quality preservation** criteria (unchanged from BLOCKBAG prior work) require: overall equal-date/equal-vintage mean mature selected-Top1 target_rank_21 >=95% BASE; same >=95% for each individual vintage; overall mature Precision@5 >=95% BASE; and paired three-calendar-month block bootstrap one-sided 95% lower bound of candidate minus BASE selected-Top1 percentile strictly greater than negative 5% of original overall BASE. 20,000 bootstrap replicates, NumPy default_rng(20261004), block lengths primary 3, sensitivity 1/6, with the same date draw applied across all vintages, from original predictive metric routines. A strict positive superior-quality check is reported independently; no NDCG gain substitutes for a failing Top1 gate. If either pilot-stability or quality preservation fails, **stop: no full economic replay**.

A "near operational repeatability" label additionally requires each native pair's Top1 disagreement <=5% AND each common pair's rank-MAD >=90% below corresponding BASE; do not substitute weaker pilot pass for such a claim.

## Conditions before CAGR
Only if both stability pilot and predictive preservation gates pass, next stage is a **separate full raw** reimplementation of this *exact* 75/25 ranking on all daily inference dates, training Ridge and XGB in each source-vintage annual fold from causal historical maturity-only training, without using any old prediction outputs, retaining canonical Compact63, Tail, MA3, macro, negative feedback, allocations, rebalance, costs, execution, and all exact source/MA3 parity gates. Compare three raw original acquisition snapshots with unchanged BASE replay and require: mean CAGR >=95% BASE mean, mean MaxDD >= BASE minus 2pp, turnover <=110% BASE, daily Top1 disagreement <= BASE, CAGR spread <=75% BASE spread, all provenance/integrity checks true. A full replay is the **only** authority for CAGR; a 21-session selected-return mean is not CAGR. No automatic production adoption even after those gates; fresh historical universe and forward-date confirmation still necessary.

No weight/hyperparameter sweep or interactive threshold changes. All failures must be retained.
