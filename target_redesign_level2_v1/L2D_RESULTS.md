# L2-D — Same-data XGBRanker canonical vs Ridge stable (2026-10-08)

**Status: COMPLETE, VALIDATED DIAGNOSTIC; NOT APPROVED FOR PRODUCTION.** User authorizes writes **only to `AM1975MA/Test`**, and neither `Etf_trader` nor `Trader_selector` was touched. L2-D specification frozen before fitting in [L2D_PREREGISTRATION.md](L2D_PREREGISTRATION.md).

## Provenance, configuration and fit integrity

- Yahoo frozen acquisition repeats 1/2/3 from completed [GitHub run 37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact `11272972639`, ZIP SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`. Same 149 ETFs, same market history 2004-2026; vintages are **not independent holdout datasets**.
- Compact21 fixed 125 canonical features computed causally from adjusted Open/High/Low/Close/Volume. Strict fit training `signal_date < Jan 1 fit year`, `exit_date_21 < Jan 1 fit year`, ≥30 nonmissing features. Same maturity-eligible training cohort per vintage and cutoff for both learners.
- XGBoost canonical source-only Compact21 objective `rank:pairwise`, eval `ndcg@3`, max_depth 4, eta .035, subsample .85, colsample_bytree .8, min_child_weight 8, lambda 8, alpha .1, 360 rounds, three independent seeds 101/202/303; training label `round(rank_pct_21*100)`; native isolation one fit per Python process, QuantileDMatrix with signal-date ranking group.
- Ridge frozen from L2-C; same feature training/eligibility/cutoffs, continuous `rank_pct_21`, `SimpleImputer(median,keep_empty_features=True) -> StandardScaler -> Ridge(alpha=30)`.
- **30 annual vintage/year XGB ensembles actually refitted**, 90 isolated seed fits, 2017-2026. Python 3.13.5, pandas2.2.3, numpy2.3.5, xgboost3.1.3, scikit-learn1.8.0. Worker nthread=1.
- Independent audit verified **51,405 native predictions per learner** (includes immature July 2026 inference rows not used in quality metrics), no duplicate keys, identical native XGB/Ridge keys and identical forward realized returns/ranks per key; strict fit label maturity all 30 yearly fits. Evaluation: **113 dates** Feb 2017–Jun 2026, 149 ETFs/date, 16,837 rows/vintage, 50,511 rows/model across three vintages, exits mature by 2026-07-31.
- **No BIL economic target**: cash benchmark removed; BIL remains an ETF candidate only in the unchanged Original149 universe.

## Matched model selection quality

Equal-weight 113 monthly decision dates after averaging three vintages within each date. All returns below are 21-session next-Open to Open **ETF selected labels with assumed flat 0.1% cost per side**, not a CAGR.

| Metric | Canonical XGB | Stable Ridge |
|---|---:|---:|
| NDCG@5 | 0.554145 | **0.561932** |
| Rank IC | 0.064807 | **0.092917** |
| Selected Top1 realized 21-session net return | **+2.4605%** | +1.7618% |
| Chosen ETF actually within realized Top5 | **19.1740%** | 7.9646% |
| Chosen ETF is realized exact winner | **6.4897%** | 5.3097% |
| Selected ETF mean realized percentile | **0.588545** | 0.548752 |
| Regret vs best retrospective ETF | **16.6777 percentage points** | 17.3764 pp |

**Development-only paired three-calendar-month moving block bootstrap** (10k replications; within-date vintages averaged before sampling; nominal unadjusted 95%):
- XGB minus Ridge selected next-21-session net return = **+0.006987**; CI **[-0.011109, +0.024253]**, includes zero.
- XGB minus Ridge NDCG@5 = **-0.007788**; CI **[-0.050073, +0.030910]**, includes zero.
- XGB minus Ridge Rank IC = **-0.028110**; CI **[-0.064935, +0.010743]**, includes zero.
- XGB minus Ridge realized Top5 winner hit = **+0.112094**; CI **[+0.038348,+0.188791]**, excludes zero for this uncorrected exploratory endpoint. This does not establish true future superiority after many tried variants.

## Data vintage robustness

Three pairs repeat1–2, repeat1–3, repeat2–3:

| Stability metric | XGB | Ridge |
|---|---:|---:|
| Native Top1 agreement across data vintages | **45.13%, 56.64%, 46.90%** | **99.12%, 100%, 99.12%** |
| Native mean percentile rank-MAD | 0.053428, 0.053204, 0.053884 | 0.001029, 0.000987, 0.001146 |
| Native mean Top5 overlap | 66.90%, 66.55%, 68.32% | 100%, 99.65%, 99.65% |
| **Frozen Repeat2 common inference** Top1 agreement | **45.13%,56.64%,46.90%** | **100%,100%,100%** |

The common-input diagnostic shows **XGB instability is driven overwhelmingly by the fitted models changing with minuscule training vintage revisions**, not by instantaneous inference-input changes. This is consistent with earlier independent diagnostics but does not prove an underlying unique numerical bug.

**Within each same vintage and month**, the XGB and Ridge Top1 selections coincide only **7.3746%** of the time. Their predictive emphases are materially different; naive blend weights must not be optimized on already burned Original149.

## Fixed standalone monthly Top1 economic execution proxy

An independent checker reconstructed capital from historical next-open prices and switch-dependent trading fee counts exactly. Buy next open after signal, hold until next month's next open; 112 nonoverlapping monthly periods **2017-03-01 to 2026-07-01**, long-only one ETF at a time; fee 0.1% on each buy and each sell, waived if continuing same ETF; buy first period / sell final period counted. No intramonth stop, MA3, HighCAGR24, baskets, governor, modeled slippage or full Hybrid24 execution. Drawdown sampled *monthly only* can understate actual peak-to-trough risk.

| Data vintage | XGB CAGR proxy | Ridge CAGR proxy | XGB monthly sampled max DD | Ridge monthly sampled max DD |
|---|---:|---:|---:|---:|
| Repeat1 | **19.5572%** | 17.0896% | -52.6814% | -31.6598% |
| Repeat2 | **22.1447%** | 17.1216% | -41.8777% | -31.6597% |
| Repeat3 | **31.8815%** | 17.0896% | -46.8404% | -31.6597% |

The *same* model and market, only a tiny Yahoo price-vintage change, yields a **12.32 percentage-point CAGR spread for XGB** versus ~0.032 pp Ridge. This is the most decision-relevant evidence about unstable reproducibility; it is not a valid performance prediction for 2026 onward.

Independent second computation of wealth = product of gross next-open period returns times `(1-0.001)^(2*switches + 2)` verified all six wealth totals to machine precision; live signals always precede execution entry, and one period exits exactly at the next period entry.

Paired log monthly return difference XGB−Ridge, vintages averaged per date, 3-month-block bootstrap 10k: **+0.005050/month**, descriptive 95% interval **[-0.013331,+0.020887]**, including zero.

## Limits and decision

1. The canonical XGB has greater *top-5 winner selection precision* and higher point-estimate next-21-session selected return. Ridge has moderately stronger broad ranking metrics (NDCG@5, Rank IC) and **dramatically superior numerical stability**. A claim of more money from XGB is unsupported statistically; a claim Ridge has higher top1 alpha is unsupported by the observed means.
2. Three Yahoo vintages are identical market periods; they only diagnose sensitivity. Original149 and Holdout70 are development-burned; no new prospective out-of-sample holdout was created. Any future adoption requires an independently collected later period and predefined prediction/risk gates.
3. This is a **matched Compact21 component comparison**, NOT a full Hybrid24 source-only substitution and replay. Canonical MA3, Tail, blending and 500 basket selection may alter economics. The single-name CAGR is explicitly labeled an execution proxy.
4. Different learner families necessarily use different target representations (XGB rounded relevance vs Ridge continuous percentile), so model-vs-target causal effects remain entangled. Never claim a pure learner-only attribution.

**Next research hypothesis**: preserve an XGB-like high-recall opportunity generator but address training-data amplification via explicit model stability constraints, robust cross-vintage consistency, and a separate continuous stable model anchoring decisions. Avoid weight/threshold searches on burned history; preregister prospective robustness-vs-quality gates before a new test. Alternatively explore ranker teacher→stable student distillation or ranker aggregation over independently perturbed training vintages *without* using future data. No hyperparameter changes or production decisions authorized by this report.

## Reproducible code and artifacts

Full executed runner `l2d_compare.py` SHA256 `4a3476c7783a096cdebfc73b02a81dfc595d4ef70c54034dd33b0f18bd66e3f8`; single-name proxy code `l2d_trading_proxy.py` SHA256 `4c42a71090fe75fe7511fb0c386464407bdf0351fdf6065ba2737d41b5cd44c4`; independent audit code `l2d_independent_audit.py` SHA256 `8025b5225c78db707c06621acb12963ea7fb0de538ad5fd08ced567e0825a74d`. Their executed outputs, native/common predictions, fit audits, yearly/per-date metrics, block-bootstrap estimates and standalone trading-proxy paths are included in the companion conversation ZIP artifact; input price files are retrieved separately by the frozen GitHub artifact ID and were not re-uploaded or committed.

Final independent audit **PASS**. No full-portfolio replay yet. **Promoted=false**.
