# R0-G — Read-only Yahoo Repeat1/Repeat3 rank-pair and tie-transition audit

**Date 2026-10-08.** **NO XGBoost fitting, no full V2 portfolio replay, no Original149 parameter search.** This is an original, *descriptive* derivative of the already frozen Original149 Repeat1/3 vendor acquisitions, **not a new financial OOS sample**.

**Pre-registration before computing outcomes:** [R0-G protocol](2026-10-08-r0g-label-pair-transition-prereg.md), commit `dc37f6f08febb4ae051818946d85b11922009b0d`.

## What was actually evaluated

Frozen GitHub artifact counterpart `yfinance-repeatability-v1-raw.zip`, SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`. Raw adjusted `Open` files `_repeat1/<ticker>.csv`, `_repeat3/<ticker>.csv` with 149 original ETF tickers. Canonical `source_only/kernel.py:add_labels` convention: monthly signal last market day, entry next open, exit after 21 or 63 additional market sessions; forward O2O return `Open[exit] / Open[entry] - 1`, within-month `rank(pct=True,method='average')`, integer `round(100*rank_pct)`. Pair signs are taken from the **integer labels** actually used by `rank:pairwise`, not merely floating forward returns.

**Important scope:** reconstruction concerns the raw **price-derived labels**, not all 125 feature validity / actual eligibility / model training matrices. The training row cohorts therefore are **not independently asserted identical** to the source-only worker, although the label disagreement count agrees at the published cutoffs (below). No XGB objective gradients or original fitted tree splits were reconstructed here.

## Result: extraordinarily sparse ordinal differences

Across **267 monthly rows per horizon** with sufficient future data, 149 tickers nominally present (the actual comparable-pair count excludes missing tickers by month):

| Measure | Compact21 (forward 21 sessions) | Compact63 (forward 63 sessions) |
|---|---:|---:|
| All comparable unordered ETF pairs across months | 2,333,613 | 2,333,613 |
| **Changed integer relevance labels (row observations)** | **16** | 10 |
| **Strict pairwise sign inversions** (higher→lower or vice versa) | **8** | 5 |
| **Rank tie→ordered** | 7 | 3 |
| **Ordered→rank tie** | 7 | 3 |
| Raw realized-return ordering inversions (before 0–100 integer grades) | 15 | 6 |
| Months with ≥1 strictly reversed integer pair | 8 | 5 |

A strict inversion is a pair whose grade difference changes sign; **a mere integer-grade increment without a sign change does not qualify**. Ties disappearing or appearing are recorded separately because the XGB pair generator may change which candidate pairs contribute to the ranking gradients. The three columns are not additive measures of unique revised observations and cannot be read as “22 independent mistakes.”

### Critical agreement with pre-existing 4-year feature/label forensic

For Compact21, cumulative integer-grade changes among mature price-derived label months before Jan 1 cutoff:

| Annual fit cutoff | Earlier `COMPACT21_XGB_FORENSIC_V1` inferred changed labels | New raw-label audit |
|---|---:|---:|
| 2017 | 12 | **12** |
| 2020 | 16 | **16** |
| 2023 | 16 | **16** |
| 2026 | 16 | **16** |

**4/4 exact count consistency** with the previously stored `integer_label_disagreement_fraction_1_3 × training_common_rows`, independently from the read-only raw source; this does not imply all per-row feature eligibility or fitted-booster state has been recovered.

Evidence from prior `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json`: changing training labels alone (X held fixed) generated Top1 disagreement on 2017/2020/2023/2026, while inference-feature-only perturbations under frozen booster had 0% Top1 disagreement. This earlier result is **not rerun**, and its canonical fit/portfolio repercussions must not be conflated with these descriptive pair counts.

## Interpretation — nuanced, not a claim of complete causal proof

The question has narrowed from “features and labels vary slightly” to a much more precise **learning-to-rank discontinuity candidate**: a *very small number of flips in the sign of within-query relevance pairs plus creation/destruction of ties* can alter the pairwise gradient/eligible pair set, and thereafter many XGBoost histogram-tree splits and predictions. R0-F's new deliberately rank-reversing one-label synthetic experiment demonstrates the **possibility** of that effect at 360 rounds, including under `max_leaves=8`, but is not authentic reconstruction of the 2017–26 tree fits.

**Do NOT conclude** that all Golden 43.146%→Oct2 fresh 31.604% historical return difference is caused by the eight pair sign changes. Training X-feature differences independently cause major instability; MA3 cluster state and execution vintage also differ. The old 3 Yahoo repeats are not 3 independent markets.

## Decision

1. **Freeze max_leaves=8 as NO GO** (R0-F refutation under new synthetic worlds); do **not** search nearby max leaf settings or retrain historic Original149 to maximize CAGR.
2. Prioritize a **read-only label-margin forensic**: for only the detected rank-inverted or tied pairs, record original (as-of) 21d forward adjusted Open return difference in currency/percent units, the revised-vintage difference, tie crossing, group relevance changes and their date; confirm whether market-data adjusted price revision at entry or exit dominates. No model fit needed. After that, determine whether a theoretically justified *pair eligibility margin* or loss-specific robustness objective could be evaluated on new synthetic data **with user approval**, not on burnt Original149 performance. A pair margin **must not be fitted or chosen** using the 2017–26 returns.
3. Keep **feature-side X instability** as a separate source; it was **62.5%** Top1 disagreement in the earlier 4-year diagnosis on X-only inputs. Any label-only cure is incomplete unless this is addressed.
4. Preserve Dense MLP as an independent candidate, but do not assume Dense stacking reduces overfit; preserve 25%-retriever diagnostic 97/114 with caveat 17 lost winners and ex-ante dispersion AUC~0.5, no adaptive K.
5. Financial validation only on **genuinely new, prospectively time-stamped as-of data**, a single preregistered challenger, identical full V2 MA3/risk/cost and same-universe side-by-side economic gates.

**Data QA:** repeat1 and repeat3 shared 149 tickers; **267 monthly observations** per 21/63 horizon; no training, exact cutoffs agreed at 4/4; Python support artifact `r0g_pair_audit.py`, JSON `r0g_pair_audit_results.json`, monthly CSV `r0g_pair_monthly.csv` accompany this conversation in a ZIP, not silently claimed as GitHub files.
