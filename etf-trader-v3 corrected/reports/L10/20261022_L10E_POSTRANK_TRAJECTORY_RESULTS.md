# ETF Trader V3 Corrected L10.E1 — post-ML trajectory veto and replacement

**22 October 2026: run 39742108852 SUCCESS, one predeclared intervention tested. Decision: REJECT E1 simple negative-momentum/drawdown veto; retain original frozen ML rank intact.**
Source [evaluate.py](../../experiments/l10_postrank_trajectory/evaluate.py), [protocol](./20261022_L10E_POSTRANK_TRAJECTORY_PROTOCOL.md), raw [monthly/annual/individual trajectory and actual substitutions/paired bootstrap](./data_run_39742108852/), artifact **12409995955**. Permanent archive Actions run [39742298365](https://github.com/AM1975MA/Test/actions/runs/39742298365), success.

## Clarification of architecture and distinction from L10.D1

The intended innovation is **conditional post-selection auditing**. Freeze the XGBoost CORRECTED Pairwise127 ranking. For every ETF *already selected* by this ML ranker, evaluate recent past-only prices for trajectory concerns; skip the selected title ONLY if a predefined warning is triggered. Fill its original slot with the next highest-ranked, unflagged name **in the same frozen ML ranking**. Keep all unaffected ML choices, selected order, and weights unchanged. The Top5 model may supply *additional candidates later in a separate experiment*, but does not rank or substitute anything here. This is not an analytic re-ranking of the expanded universe as mistakenly tested in L10.D1 (run 39738471945); that rejected experiment remains valid as a distinct negative control, not as a substitute for the post-rank hypothesis.

This E1 rule is only a *first transparent sanity gate*, not assumed optimal:
for signal close t, flag ETF i when BOTH
1. log(C[i,t] / C[i,t-21]) < 0
2. C[i,t] / max(C[i,t-62],...,C[i,t]) - 1 <= -0.10.

At the next-open signal date, slot-by-slot scan original CORRECTED ranks 4–24, replacing each flagged Top3 ETF with the first unflagged not-yet-used alternative. Unflagged incumbents remain untouched, same weights [0.5,0.3,0.2]. If none available, incumbent remains and the failure is logged. All thresholds were fixed before these E1 results, no grid search and no ML refit.

Source adjusted OHLCV run **39482809691** certified, frozen OOS Pairwise127 scores run **39700865721**, 149 original ETFs, same 500 canonical baskets of 24 with SHA256
\`36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e\`.
Exactly **101 label-mature monthly OOS dates**; synthetic perturbation of all future closes leaves historic flags unchanged (PASS); trajectory coverage 100% on 149 ETF universe throughout. Full 149*101 timestamped signal audit preserved. No live execution/CAGR computed. Historical dates 2018–2026 repeatedly researched; NOT a virgin holdout.

## Economically aligned *functional* 101-month paired outcomes, unchanged Top3 allocation

| Metric | Frozen CORRECTED | Trajectory-veto corrected | Delta (veto−frozen) |
|---|---:|---:|---:|
| Selected Top3 contains actual future basket best | **35.4713%** | 29.2713% | **−6.2000 pp**, CI95 [−9.0517,−3.5941] pp |
| Weight assigned to actual future basket best | **12.5818%** | 10.1826% | **−2.3992 pp**, CI95 [−3.5563,−1.3741] pp |
| Weight on ETF future21D absolute loss >=10% | 8.4861% | **6.7834%** | **−1.7028 pp**, CI95 [−3.3371,−0.0614] pp |
| Weight on future worst-three ETF names | 22.1313% | **19.9531%** | **−2.1782 pp**, CI95 [−3.8315,−0.3116] pp |
| Weighted realized next21D percentile-rank quality | **0.524852** | 0.516791 | −0.008061, CI95 [−0.032327,+0.012659] |
| Weighted actual 21D mean forward return | **1.3560%** | 1.2964% | −0.0595 pp, CI95 [−0.5736,+0.4049] pp |
| Weighted oracle 21D regret vs basket-best | **0.105470** | 0.106066 | +0.000595, CI95 [−0.004049,+0.005736] |

Calendar month is the inferential unit (500 overlapping baskets averaged *within* month); 6-calendar-month circular paired bootstrap, 6000 resamples, common 101 months. These are descriptive exploratory confidence intervals on repeatedly studied periods.

## Why this flag is not safe enough

- Average **31.9556% of original Top3 capital flagged**, 31.9228% actually replaced. On average **56.6119% of baskets** changed, **0.904634 replacements per basket**; only 0.001564 flagged positions per basket could not find an unflagged next-ranked alternative. This is not a narrowly targeted exception mechanism.
- In each basket/month, capital removed from future 10% losers averaged **4.0598%**, while incoming replacement exposure to future 10% losers averaged **2.3570%**: difference 1.7028 pp improvement in severe-loss exposure.
- However it removed original capital worth **4.4952% on actual future basket-best names** and replaced it with only **2.0960% on future basket-best names**; the net winner-weight loss 2.3992 pp outweighs the desired preservation objective.
- Removed positive-future-return original capital **17.3614%**, so historical negative trajectory by itself often signifies a recoverable correction, not evidence that the future return will be negative.
- On unique initially selected ETF-months (not treating basket repetitions as independent) severe-loss10 conditional precision of flagged names averages **11.0759%** on 99 months where flags exist, compared to **7.0530%** among unflagged on 100 months. This is a signal of incremental association but insufficient to justify automatic exclusion. Per-month class-conditional ratios have different denominators, so do NOT interpret this simple difference as an inferential p-value or calibrated loss probability.
- Entire universe flag prevalence is 12.5988% but among the distinct already selected ETF names 24.6962%; the ranker can prefer momentum-reversal setups. An unconditional deterioration veto can erase the ranker's true alpha in those regimes.

## Decision and next analytical research, without posthoc rescue

**Reject this single E1 veto threshold and rank4+ substitution as investable policy.** The downside protection exists descriptively but materially reduces true winner capture and winner weight. Do not tune the -10% flag or window after reading its 2018–2026 results. No L10.D1 or L10.E1 strategy is promoted; the original frozen reference remains untouched.

Next *separate preregistered* E2 should address **trajectory quality conditional on why ML selected the ETF**, rather than simply negative momentum/drawdown. The mathematical auditor should diagnose at least direction versus recovery, continuity/coherence versus noise, acceleration/change-point, realized downside/tail risk and conditional market/peer behavior from lagged prices only. A warning mechanism should explicitly recognize high-probability recovery candidates and avoid vetoing them solely for recent drawdown. Audit *false veto of actual future winners* as the primary constraint; evaluate severity and skill on unique selected ETF-months, then test exactly one predeclared selective veto/promotion rule, not a grid search. A risk prediction component may train strictly on matured historical labels, but it must not replace the ML general rank. A future separate test can allow Top5 candidate proposals as replacement source while freezing all other layers. Any further 2018–26 results remain exploratory, and entirely newer data are needed before promotion.

## Reproducibility

- Protocol fixed on branch \`research-v3-l10e-postrank-trajectory-20261022\`, before run 39742108852.
- Successful functional signal/correction workflow [39742108852](https://github.com/AM1975MA/Test/actions/runs/39742108852).
- Exact artifact ID **12409995955** and durable [results directory](./data_run_39742108852/).
- Permanent archive workflow [39742298365](https://github.com/AM1975MA/Test/actions/runs/39742298365) success; main tracked files contain all per-ticker as-of flags, 45,684 executed candidate substitutions (individual basket/date records), monthly/annual and paired bootstrap tables.
- No model refit, no general analytic rank replacement, no CAGR optimization, no changes to original V2, production or frozen V3 reference.
