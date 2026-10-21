# V3 L06.2 — Soft-risk weight adjustment, same three candidate ETFs

Date: **21 October 2026**. Status **EXPLORATORY — NOT PROMOTED**. No changes to live or baseline V2, L00–L05, Tail, ranker, signal horizon or risk classifier.

Successful [GitHub Actions run 39669570005](https://github.com/AM1975MA/Test/actions/runs/39669570005); complete artifact ID **12378279032**, named `v3-l06-soft-risk-keep-top3-results`.

## Predeclared one-variable intervention

- Original OOS risk model from [run 39662062361](https://github.com/AM1975MA/Test/actions/runs/39662062361) is **frozen**, annual refit logistic45 with maturity-safe labels. OOS Tail winner scores also frozen from successful run 39655513813. 149 original ETF histories, 500 fixed canonical baskets ×24.
- Preserve exactly the same three Tail-selected ETF tickers in each basket, identical month/ETF observations and future-21-day evaluation labels; **do not apply risk exclusion or replace any ticker**.
- Original weights: `w=(0.50,0.30,0.20)`.
- One new preregistered treatment: `w'_i = w_i*(1-0.50*risk_percentile_i) / Σ_j(w_j*(1-0.50*risk_percentile_j))`. `risk_percentile` is known at the signal date (cross-universe current OOS estimated bad-event risk), bounded 0–1. All three positions retain positive weights.
- No coefficient search, no retraining, no CAGR/Sharpe, no extra risk/regime/Tail layer.
- Exact baseline calculation checked against previous successful L06 original monthly metrics, all six key fields to tolerance 2e-12. Same membership verified by construction; winner Top-3 identical across all 101 months.

## Functional result: 101 fully matured month-ends, 500 overlapping baskets

| Metric | Frozen Top3 50/30/20 | Soft risk 0.50 | Paired delta and 95% 6-month block bootstrap interval |
|---|---:|---:|---|
| Winner in selected three | 42.7465% | 42.7465% | Exactly 0; invariant |
| Weight on realized winner | **15.2176%** | 14.9645% | -0.2531 pp, CI [-0.3366,-0.1667] pp |
| Weight on realized bottom-three of 24 | 26.6952% | **26.3915%** | -0.3037 pp, CI [-0.4021,-0.1999] pp |
| Average future within-basket rank quality | 0.512941 | 0.513404 | +0.000463, CI [-0.000659,+0.001502] |
| Weighted next-21D oracle regret | 0.107137 | 0.107063 | -0.000075, CI [-0.000295,+0.000147] |
| Target-weight churn per month | **0.383364** | 0.399407 | +0.016043, CI [+0.014594,+0.017621] |
| Effective number of positions | 2.63158 | 2.67043 | +0.03885 |
| Average max position weight | 50.000% | 48.739% | -1.261 pp |

Mean half-L1 change of target weights from the original three weights is **0.027271**; no ETF is removed. The lower bad exposure is demonstrable on historically examined months but offset by reduced exposure to true future winners and more churn; neither rank quality nor regret improves convincingly. No unambiguous Pareto improvement or functional gate success.

## Root cause indicated by conditional predictive diagnostics

The **same risk model** has historical universe-wide 21D bottom-decile ROC AUC **0.7552**, but **when evaluated exclusively among the three ETFs picked by the frozen Tail expert in each canonical basket**, its ability to distinguish next-21D basket-bottom-three candidates is weak:

- Conditional AUC **0.575161**;
- Conditional Average Precision **0.403919**, versus conditional bottom-three event prevalence **0.258792**.

Important distinction: the selected-basket conditional event (bottom 3 of 24) is **not** exactly the same label as global bottom 10% of 149 ETFs. Basket entries overlap heavily and are averaged monthly, not treated as 151,500 independent events. Conditioning and target change both explain part of the AUC difference; these diagnostics do NOT prove unconditional risk miscalibration.

## Decision and next isolated proposal

**Do not promote `TOP3_SOFT_RISK50`** as a better-risk construction; retain frozen Top3 50/30/20 control. Do **not** sweep the risk coefficient over already-examined OOS years.

Next strictly isolated L06 question: can a prequential, selection-conditional risk model trained on **already matured historical OOS Tail selections** distinguish true basket bottom-three positions *better than the globally trained risk head* on later years? Preserve the future Top3 policy and weights for this first diagnostic; compare conditional AP, AUC, Brier, false-negative/positive rates, train-only prevalence baseline. Only after intrinsic conditional risk skill is demonstrated consider a separate weight-adjustment experiment.

Historical data are repeatedly explored; even a favorable result requires a newly untouched vintage before production promotion.
