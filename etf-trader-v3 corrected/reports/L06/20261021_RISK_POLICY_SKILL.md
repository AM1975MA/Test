# V3 L06 — strictly causal bottom-decile risk classifier and risk-veto test

**Date:** 21 October 2026. **COMPLETED — operational risk veto REJECTED.** Preserve separate OOS risk model for research; **do not filter portfolio selections using this rule**.

Successful [Actions run 39662062361](https://github.com/AM1975MA/Test/actions/runs/39662062361), artifact **12375515870**, complete 149 ETF-month OOS risk scores, annual fit audit, paired monthly and bootstrap results.

## Single-variable intervention

- Frozen **Tail45 expert** predictions (39655513813); frozen **Top3 50/30/20 allocation** from L05; all other scores and portfolio settings held fixed.
- Only risk layer modified: independently re-fit `LogisticRegression(C=.2)` on mature, 21-day bottom-decile ETF labels, using 45 corrected Tail features. Full training eligibility requires forward-63-day labels matured before annual cutoff. No label from test year leaks into fit.
- Ex ante fixed risk rule: among the basket's highest ranked Tail ETFs, **exclude candidates in the upper 15% of predicted bottom-decile risk across the full 149 ETF universe** and replace them with the next eligible Tail-ranked ETF; keep exactly 3 positions at weights **50/30/20**. Same original 500 fixed 24-member baskets and 101 month-end signals.
- Original raw source 39482809691, OOS expert scores 39659903643. No CAGR, active macro or scoring-model retraining.

## Standalone risk identification

| Classification measure | Score |
|---|---:|
| Bottom-decile risk Average Precision | **0.289746** |
| Bottom-decile risk ROC AUC | **0.755226** |
| Risk percentile flagged | 15.436% of ETFs |
| Precision of flagged bottom-decile events | 24.666% |
| Recall of observed bottom-decile events | 40.523% |
| False-positive rate | 12.835% |

The classifier has information about **relative future loser risk**, but many flags are not true bottom-decile events.

## Effect on frozen Top3 selection

| Functional metric | No risk override | Exclude top 15% predicted risk |
|---|---:|---:|
| Best ETF present among the 3 selections | **42.747%** | 20.642% |
| Weight on actual basket best ETF | **15.218%** | 7.343% |
| Weight on actual 3 worst basket ETFs | 26.695% | **17.709%** |
| Weighted realized ETF rank quality [0,1] | 0.512941 | 0.514875 |
| Ex post weighted regret vs best ETF (21D fractional return) | **0.107137** | 0.107456 |
| Target-weight churn | **0.383364** | 0.539562 |
| Mean replaced holdings per basket | 0 | **2.133** |
| Share of removed candidates NOT in worst-three | — | **71.790%** |

Paired six-calendar-month block bootstrap over 101 month ends, 6000 replications, *not* treating 500 overlapping baskets as 500 independent trials:
- Top-3 winner capture falls **−22.105 pp**, 95% CI **[−26.790,−17.374] pp**.
- Bottom-three exposure decreases **−8.986 pp**, CI **[−11.792,−6.282] pp**.
- Target weight churn increases **+0.1562** (roughly +41% vs control), CI **[+0.12545,+0.18452]**.
- Weighted rank-quality +0.001934, CI [-0.027108,+0.030400]: no demonstrated general selection improvement.

The rule removes too many attractive but volatile or otherwise high-scoring ETFs and replaces 2.13 out of 3 proposed names on average. The specific financial mechanism cannot be established just from this study, but the severe winner-loss is directly observed.

## Decision and next gate

**REJECT operational `RISK85` veto**, retaining `Top3 50/30/20` as candidate portfolio allocation without this override. Preserve `P(bottom10%)` as a separately validated research risk signal, not a hard rejection rule or ranking penalty.

A more conservative risk overlay, if explored, must be **predeclared** and evaluated for sensitivity/specificity, preserved opportunity capture, replacement turnover, and error asymmetry *before* global integrated model evaluation. Do not search thresholds on the same OOS months then proclaim independent success.

## Limitations

Prior years 2018–2026 have already been heavily examined; every uncertainty statement is exploratory, not an untouched future holdout. This is a **selection/risk skill** test, not a live execution simulation, drawdown policy, or full ETF Trader V3 financial-performance certification. No production changes.
