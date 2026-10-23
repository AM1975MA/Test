# V3 parallel research — causal decision tree meta-reranker (2026-10-23)

**Actual successful CI:** [Actions run 40031144599](https://github.com/AM1975MA/Test/actions/runs/40031144599), both tree and exponential matrix jobs succeeded; [tree archive 12534862883](https://github.com/AM1975MA/Test/actions/runs/40031144599/artifacts/12534862883); [exponential archive 12534457757](https://github.com/AM1975MA/Test/actions/runs/40031144599/artifacts/12534457757).

Frozen first-stage out-of-year ranker + five regression models, run `40016809498`, canonical 149 ETF, 500 overlapping 24-ETF baskets, 101 monthly signals from Jan 2018 to May 2026. Same 21-trading-day next-open future outcome. V2/V3 production untouched.

## What trained

`DecisionTreeClassifier(criterion="log_loss")` predicts if an *alternative already among the ranker's original Top3* will outperform the ranker's Top1 at the mature forward horizon. Input features (no outcomes): same-date global ranker score percentile margin and strength, rank Top3 dispersion, and relative, absolute, volatility-removed, pseudo-Huber regression-score percentiles and inter-candidate gaps, 14 values per candidate comparison. For each month, collapse repeated original-alternative ticker pairs among overlapping baskets; equal total training weight per historical month. Exclude outcomes if signal date was less than 60 calendar days before current test. Quarterly refit with expanding or trailing 36-month historical OOS observations. First possible meta decision April 2020: >=24 fully matured OOS historical months; fallback baseline before that. Evaluate tree max depth 1/2/3, minimum 100/300 unique pairs per leaf, probabilities >0.55, 0.60 or 0.65: 36 deterministic variants plus exact unchanged baseline. Only Top3 reordering is authorized, so baseline Top3 hit rate is structurally invariant.

## Best **exploratory** outcome — TREE_expanding_D3_N100_P0.6

| Metric | Frozen baseline | Decision tree | Delta |
|---|---:|---:|---:|
| Basket Top1 true-winner hit rate | 14.5525% | 14.8099% | +0.2574 percentage points |
| Basket Top3 true-winner coverage | 35.4713% | 35.4713% | exactly unchanged |
| nDCG@3 | .542279 | .543235 | +.000956 |
| Mean selected next-open 21D forward excess vs basket mean | +.7122% | +.8496% | +.1374 percentage points |
| Top1 selected regret vs actual max | 10.4115% | 10.2741% | -.1374 percentage points |
| Top1 future loss <= -10% | 9.2614% | 8.8594% | -.4020 percentage points |
| Decisions changed | 0 | 1,501 of 50,500 basket-month choices | 2.9723% |
| Changes better/worse | — | 932 better / 569 worse | 62.0919% changes better |

The 50,500 basket-month decisions overlap. They are NOT independent observations. Top1 change 95% paired circular six-month block bootstrap interval: **[-.0554,+.6515] percentage points** (not conclusive), on 2,000 month-level-resampled draws; forward excess change interval **[+.0274,+.2547] percentage points** (excludes zero conditional on having selected this exact configuration); selection regret negative mirror. **However** 36 model/threshold variants were compared on same researched timeline: after-the-fact selection and multiple comparisons make this CI optimistic as a confirmatory claim. This is not a pristine holdout.

Alternative more conservative: `TREE_expanding_D2_N300_P0.65` changes 763/50500 cases (1.51%); 526 better vs 237 worse (68.94% better); Top1 14.6911%, mean future selected excess +.8206%; selected-excess gain +.1084 pp, paired CI [.0175,.2194] pp. Simpler depth1 ~70.45% successful changes, 599 changes, +.0987pp excess, Top1 14.6079%. Most strong results are **expanding-fit** trees; trailing 36 months generally weaker, another regime-stability caveat.

## Regimes and learning chronology

The best tree begins truly learned decisions in **April 2020**, using prior matured 2018-Jan–2020-Feb signals (26 months, 8,189 distinct ticker-pair examples). There are **300 quarterly tree fits** in the full matrix (two windows x three depths x two leaf sizes, at each fitted quarter). Strict chronological maturity enforced. For best configuration selected forward excess improvements vs baseline, in percentage points per 21-day holding period:
- 2018: +0.000; 2019: +0.000 (fallback original).
- 2020: +0.279; 2021: -0.006; 2022: +0.119; 2023: -0.002.
- 2024: +0.154; 2025: +0.294; 2026 Jan–May: +0.765.
- 2018–2025 (96 dates): mean **+0.10475 pp**; 2026 Jan–May (5 dates): mean +0.76513 pp.
- The 2026 five-month period contributes ~27% of the full-sample uplift, *not* the ~89% observed in the previous multiplicative 5% regression variant.

## No promotion yet

This is promising for a *conditional decision tree* on baseline Top3, **not evidence for replacing the original first-stage ranker**. Core model is unchanged; test uses previously researched dates and picks the best of 36 candidate trees. Next needed are precommitted hyperparameters or strictly nested chronological model selection, later truly untouched signals, and economic after-cost Top2 or Top3 portfolio checks; independently evaluate turnover, CAGR, Sharpe, maximum drawdown and risk, not merely Top1 21D selected excess. Do not compare 500 overlapping portfolios as independent trials. Train with only already matured labels. Never mix production updates until external confirmation.

Code `parallel_meta.py`, workflow `.github/workflows/v3-meta-exponential-decision-tree.yml`. Result CSVs and original artifacts linked above.
