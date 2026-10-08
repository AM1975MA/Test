# R0-D — Ex-ante dispersion vs Top38 screening: frozen diagnostic preregistration
**2026-10-08 · AM1975MA/Test · branch research/v2-xgb-immutable-checkpoints-20261008**

**State: frozen analytic contract BEFORE looking at forward-prediction diagnostic outcomes.** This is a new **descriptive, no-training** diagnostic authorized after user asked to review the test plan and proceed. Historical Original149 is research-burned; output **must never** be cited as prospective OOS validation or evidence of an improved V2 CAGR.

## Fixed inputs and sample
- Only frozen raw Yahoo Repeat2 `titanium-repeat-2.zip`, `work/original149/candidate_raw/*.csv`, 149 tickers. No fresh Yahoo or training.
- Fixed 114 monthly `signal_date` from 2017-01-31 to 2026-06-30 and forward O2O 21-trading-session return from `OOS149_return_dispersion_monthly_repeat2.csv`. Reproduce all **114** ex-post winners and sampled SD from source raw input if practical; no synthetic substitutes.
- Frozen annual-expanding LTR OOS `evidence_v1/checkpoints/retriever_ltr_v1/OOS_PREDICTIONS.csv`, exact ranked list 149 tickers/date; Top38 contains winner 97/114 already established (see `docs/superpowers/reviews/2026-10-08-r0-frozen-top-quartile-recall.md`). LTR is **not** ETF Trader V2 Compact21.
- Dates/groups and source hash must match archived references, no dropped months silently.

## Hypothesis separated into testable components

**H1 (predictability of dispersion):** At each *signal date* t (before subsequent `entry_date`), compute adjusted-**Close** trailing 21-session and 63-session return per ticker, `Close[t] / Close[t-N] - 1`. Take cross-sectional sample standard deviation across all 149 eligible ETFs for each lookback, plus cross-sectional IQR of trailing returns as *secondary independent descriptive* metrics. Compute rank **Spearman correlation** of each predictor versus later 21-session cross-sectional **SD** (already fixed). Report 21 and 63 separately; never pick 'winner' lookback from this dataset. Prefer common-calendar reference index and exact as-of closes.

**H2 (false-negative filter vulnerability):** For same ex-ante predictors, separately report their relationship to fixed binary **Top38 contains ex-post best future ETF**, i.e. 97 positives / 17 negatives. Use correlation (point-biserial or rank), and AUROC for low-dispersion predicting misses, **without fitting a logistic model or tuning cutoffs**. Report all data and early 2017–22 vs late 2023–26 descriptive breakdown; late n=1 miss means unreliable subgroup discrimination.

**H3 (economic opportunity cost — oracle upper bound only):** For each month compute: `best_forward_21d_across_149 - best_forward_21d_among_frozen_LTR_Top38`. Zero whenever global winner retained, nonzero otherwise. Summarize 114-month mean (including 97 zeros), 17 miss-month mean, worst miss, and list largest misses. This is **perfect-foresight max attainable return loss**, not actual portfolio regret or ETF Trader V2 CAGR. Calculate only with frozen LTR Top38 membership and matched O2O21 returns. No selection model refit.

**H4 (time-regime alternative):** Compare pre-2023 and 2023–2026 descriptive summary of ex-ante dispersion; make clear that later higher win recall can reflect length of LTR training, changed sector factors or overall trends, not just realized return SD. Report two-period association but no causal assertion.

## Statistical method frozen ex ante
- Primary diagnostic: **Spearman r** for the two predictors vs future dispersion; fixed binary AUROC for each predictor predicting **miss** with decreasing dispersion; no model training. Permissible **year-block bootstrap** confidence interval with 2000 resamples, fixed RNG seed 20261008; resample whole calendar years (preserve month correlation), report 2.5–97.5 percentile **if mathematically defined** (skip bootstrap AUC samples containing only one class). The bootstrap is descriptive, not a formal p-value for a post-hoc claim.
- Compute sample sizes and clear missing-data policy: if any ex-ante returns missing, record coverage and show the affected date; do not silently replace cohort or select a different horizon. One missing ticker can alter dispersion; if missing, report N and do not call full 149 comparable.
- Report raw differences in both periods, avoid significance claims from n=114 overlapping label windows. 2017–2026 time period and chosen 2023 boundary are already known to researchers: results are exploration, not independent test.
- **No fit, no threshold tuning, no Top5/Top10 cascade replay, no adaptive K performance simulation, no full V2 replay.**

## Decision criteria fixed ex ante
- If trailing returns weakly relate to ex-post future dispersion and Top38 miss, **do not advance adaptive screener**. If strong descriptively, record as **an exploratory candidate for prospectively preregistered follow-up**, not a GO for strategy.
- Regardless of correlation, high **oracle Top38 regret** can veto aggressive first-stage hard exclusion before formal full-V2 validation.
- Original XGB leaf-structure and regularized Dense neural alternatives stay **separate workstreams** and do not get trained under this protocol.
- If retriever top38 artifact cannot be consumed locally, complete H1/H2 using frozen miss list and record H3 `BLOCKED_NO_TOP38_MEMBERSHIP`; never invent performance.

**All modifications limited to analysis scripts/reports within `Test`, with local files as optional portable support; no production repository touched.** 
