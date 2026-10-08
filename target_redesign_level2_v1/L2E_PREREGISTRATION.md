# L2-E — Robust dual-ranker: pre-results frozen protocol (2026-10-08)

**Owner**: exclusively AM1975MA/Test branch research/target-redesign-level2-v1. **Etf_trader must remain untouched**. Project diagnostics, not a promoted model; all historical samples Original149 have been previously interrogated. All decisions below chosen *before* inspecting dual-ranker candidate metrics.

## Hypothesis

An XGBoost ranker gives useful high-performing candidates but is too unstable under near-identical Yahoo vintage downloads; a stable Ridge ranker might serve as an independent anchor or ranking veto. Test **two** mechanically specified decision rules using already produced, timestamp-aligned XGB and Ridge native per-ticker scores. No fitting, coefficient search, threshold optimization, or training on realized economic outcomes.

## Inputs

- Original149, 149 ETFs, three Yahoo vintages, 2017-02 through 2026-06 (113 mature signal dates), 21-session outcomes, fixed 0.1% trade fee per side.
- Read frozen L2-D exact predictions: `XGB_NATIVE_PREDICTIONS.csv.gz` and L2-C `PREDICTIONS.csv.gz`; common-input `XGB_COMMON_PREDICTIONS.csv.gz` and L2-C `COMMON_INPUT_PREDICTIONS.csv.gz`.
- At each signal_date/vintage rank available ETF native scores **within that date and vintage** with `pandas.rank(method='average',pct=True)` ascending (bigger is better); tie-break ticker alphabetically.
- No future realized return, cross-vintage mean, label percentile, or status of future vintages is used to decide the live ETF or to normalize its predictor. The three vintages are separate complete hypothetical histories.
- BIL is not a cash/market benchmark target, but it remains a normal ticker because frozen Original149 eligibility contains it. SPY is not required by either rule.

## Fixed rules (no selection or optimization during study)

- `RIDGE_ANCHORED_75_25`: score `0.75*ridge_prediction_percentile + 0.25*xgb_prediction_percentile`, select max. Percentile normalization compensates arbitrary learner score scales; asymmetric weight gives more authority to the learner already independently demonstrated robust. 75:25 is a **hypothesis**, not optimized.
- `XGB_TOP_QUARTILE_RIDGE_PICK`: find the highest scored `ceil(0.25*n_eligible)` XGB tickers (37 or 38 for n=149); choose the highest Ridge-ranked ETF from this XGB candidate shortlist. 25% is a non-tuned fixed broad shortlist, meant to preserve economic top-candidate information without relying on exact XGB top1. No dynamic retraining.
- Comparators: unmodified `XGB_CANONICAL_COMPACT21`, `RIDGE_RANK_PCT_21`. Do not evaluate another candidate or tune a hyperparameter after seeing results.

## Validation gates

- Verify exact common prediction keys, 3 vintages x 113 dates x 149 tickers, no leakage, no missing finite predictions or duplicate keys.
- Selection quality: per-date Top1 realized 21-session net return, realized return regret vs ex-post winner, realized Top5 hit, exact winner, realized percentile, NDCG@5 of combined score, Spearman Rank IC. Every date has equal weight; first average three vintages *within date*. Report year-by-year and each vintage.
- Stability: three pairwise native-input vintage agreements Top1, rank-MAD, Top5 overlap, plus **same-Repeat2 input** predictions from independently trained models. The live rule never uses cross-vintage data.
- Economic next-open monthly Top1 proxy: use only **112 contiguous periods** between successive monthly entry Opens, with per-side 0.1% fee for an actual switch, and common final liquidation, and no intraday stops, MA3, Tail, blends, turnover limit or real portfolio execution. Report vintage CAGR and monthly-sampled max drawdown, and turnover/switches.
- Paired 3-month moving-block bootstrap with 10k draws, fixed seed, on **113 date-averaged** differences of candidate minus both baselines for Top1 return, Top5 hit and NDCG@5. Descriptive CIs, not independent holdout, not multiplicity corrected. Also for realized monthly log-relative wealth for same 112 contiguous periods.
- Robustness gate for **exploratory continuation only**: all three native Top1 vintage pairwise agreement >= 0.90; mean realized Top5 hit >=0.15; selected Top1 net return mean not lower than Ridge; native rank-MAD <0.01. This simultaneous gate may be too strict; if both candidates fail, **report failure without modifying rules**. Real production promotion also requires genuinely prospective period.
- Report numerical uncertainty and class/year concentration and any data mismatch. Avoid claiming a statistically valid live edge on over-explored Original149.

## Specialist checks

**Quant/statistics**: repeated vintage dependency, paired date-level CIs, hit-rate vs opportunity baseline, no selection by luck. **ML**: feature leakage eliminated by using frozen native predictions only, rank normalized cross-sectionally without using outcomes, no retraining. **Execution/risk**: continuity of opening trades, correct side costs, turnover, drawdown sampling bias and absence of real portfolio constraints. **Data/QA**: IDs, chronology, identical benchmarks, exact cross-panel checks and reproducibility via script plus input hashes.

If passing robustness but not predictive skill, do not promote. If skill but not robustness, do not promote. Code, evidence and summary exclusively into Test.
