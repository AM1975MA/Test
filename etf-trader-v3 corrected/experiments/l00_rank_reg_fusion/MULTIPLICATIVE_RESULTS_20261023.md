# Multiplicative weighted ranker vs regression — actual 101-month results (2026-10-23)

**Executed successfully:** [GitHub Actions 40030122839](https://github.com/AM1975MA/Test/actions/runs/40030122839), [CSV artifacts 12533899183](https://github.com/AM1975MA/Test/actions/runs/40030122839/artifacts/12533899183).

This is a **postranking, no-retraining** experiment. It is not training the ranker with regression-based sample weights. The underlying predictions are out-of-year, 2018-Jan..2026-May, from the validated original run 40016809498. Frozen data: 149 ETF; canonical 500x24 baskets; 101 fully matured calendar months; 50,500 basket-month decisions (highly overlapping, NOT independent). Preserve original CORRECTED125 production model.

## Exact formula

First convert original XGBRanker predictions and selected regression predictions into their **same-date global ETF percentiles** `R_i,G_i in [0,1]`. Do not multiply raw ranker outputs since they can be negative. Then calculate

`weighted_score_i = R_i * (1 + lambda * (2*G_i - 1))`.

Test lambda in `{.02,.05,.10,.20,.35,.50,.75}` and five regressors (relative 125, relative 101 without volatility, absolute 125, absolute 101 without volatility, relative pseudo-Huber 125). In **WALL**, reorder all members by weighted score. In **W3**, reorder strictly the original Top3 candidates and leave all other original basket positions unchanged, preserving original Top3 coverage by construction.

## Selected observed metrics

Values are basket-month mean percentages for Top1 and Top3, and arithmetic forward excess 21-day return vs the basket's average, **not CAGR**.

| Variant | Top1 | Top3 | mean forward selected excess | nDCG3 |
|---|---:|---:|---:|---:|
| CORRECTED | 14.5525% | 35.4713% | +0.7122% | .542279 |
| W3 ABS101 lambda .02 | 14.3743% | 35.4713% | +0.7592% | .543290 |
| W3 REL125 lambda .02 | 14.3149% | 35.4713% | +0.7529% | .542862 |
| W3 REL125 lambda .05 | 13.9327% | 35.4713% | +0.8235% | .543316 |
| W3 REL125 lambda .10 | 13.4891% | 35.4713% | +0.8282% | .543417 |
| W3 REL101 lambda .20 | 12.8733% | 35.4713% | +0.8326% | .543537 |
| WALL REL125 lambda .05 | 13.9248% | 33.6554% | +0.8248% | .544515 |
| WALL REL125 lambda .10 | 13.4535% | 32.2871% | +0.8411% | .546386 |

## Paired uncertainty on 101 dates
3,000 six-calendar-month circular-block bootstrap replications. The 500 baskets are overlapping and first aggregated within the month. The interval on **W3 REL125 lambda=.05 vs CORRECTED** is:
- Top1 delta `-0.6198 percentage points` (95% interval `[-1.3248, +0.0952]`);
- Top3 delta `0`, exactly by design;
- selected excess delta `+0.11135 percentage points/21D` (95% interval `[-0.1338,+0.3720]`).

W3 REL125 lambda=.10 Top1 deterioration is statistically supported within this exploratory comparison: `-1.0634 percentage points`, interval `[-2.0455,-0.1009]`. Its selected-excess increase is **not** statistically supported.

WALL REL125 lambda=.10 loses `-3.1842 percentage points` Top3 (interval `[-4.5070,-1.8967]`). It is not a suitable replacement for baseline Top3 selection.

## Regime dependence: CRITICAL
The apparent forward return benefit of REL125 regression weighting over the **entire** 101-month history is mostly due to the five 2026 months (January-May). For **W3 REL125 lambda=.05**, observed difference in selected excess vs the baseline:
- 2018–2025 (96 months): **+0.0130 percentage points per 21D**;
- 2026 January-May (5 months): **+2.0001 percentage points per 21D**;
- 2018–2026 May (101 months): **+0.11135 percentage points per 21D**.
Approximately 89% of the observed whole-period improvement comes from 2026's five months.

Yearly excess deltas vs baseline for W3 REL125 .05: 2018 +.279 pp, 2019 +.179 pp, 2020 -.254 pp, 2021 -.052 pp, 2022 +.059 pp, 2023 +.191 pp, 2024 -.294 pp, 2025 -.004 pp, 2026 +2.000 pp. These are highly regime-sensitive.

## Assessment

No tested variant improves **Top1 winner-hit rate** over the original CORRECTED125. Full-basket multiplication still loses Top3, albeit less than original naive 75/25 linear fusion. W3 constraints preserve the baseline's Top3 membership, and slightly improve selected relative mean return and nDCG in some arms, but mostly at the expense of Top1 winner hit-rate.

**Do not promote** multiplicative regression weighting to V3 or V2 production on the evidence at hand. Forward return gain has an inconclusive calendar-block interval and is strongly affected by the 2026 window. The test grid was explored on historically reused research dates; it is not a pristine independent holdout. Further logical research would be a genuinely causal confidence/uncertainty-conditioned reranker *within Top3*, or learning when Top1 is suboptimal (not more blind global score blending), and a separate executable after-cost validation if selection skill is convincingly improved.

Files: `weighted_ranker.py`, workflow `v3-ranker-weighted-regressor.yml`, and artifact CSV: `SUMMARY.csv`, `PAIRED_MONTHLY.csv`, `PAIRED_BOOTSTRAP.csv`, `CORRECTIONS.csv`, `YEARLY.csv`, `MANIFEST.json`.
