# ETF Trader V2 — independent 31/63/127/255/511 leaf sweep
20 October 2026 · verified success

## Provenance
- GitHub Actions: https://github.com/AM1975MA/Test/actions/runs/39482809691
- Full result artifact ID: `12294125130` / `v2-deep-leaf-complete-results`.
- Three year shards (2018–2020, 2021–2023, 2024–2026) successfully trained on a **shared, certified 149 ETF OHLCV snapshot** (cutoff 2026-07-01).
- 500 official baskets, 24 members each; source-only canonical gate PASS.
- 102 score dates incl. 2026-06-30, but only **101 matured forward-21-day labels** (2018-01 through 2026-05).
- Causal annually refitted `XGBRanker` with the original 125 features, `rank:pairwise`, 360 trees, 3 seeds, and fixed 70% compact / 30% tail / unchanged macro overlay.
- Configs differ only by leaf cap among the `lossguide` variants; the original `max_depth=4` depthwise model is a separate reference.
- Reports: RESULT.json, REPLAY.csv, UNIVERSE_MONTHLY.csv, BASKET_MONTHLY.csv, REALIZED_LEAF_COUNTS.csv, PAIRED_MONTHLY_BOOTSTRAP.csv and full OOS_SCORES.csv.

## Main results — 500 overlapping baskets

| Model | Basket Top-1 % | Basket Top-3 % | Mean CAGR % | Mean MaxDD % | Used leaves avg. |
|---|---:|---:|---:|---:|---:|
| Original depth4 | 12.683 | 30.143 | 9.136 | -50.640 | 12.80 |
| 31 leaves | 13.220 | 32.279 | 8.331 | -51.893 | 31.00 |
| 63 leaves | 14.301 | 35.566 | 8.266 | -52.463 | 63.00 |
| 127 leaves | 15.222 | **38.178** | 9.437 | -52.445 | 113.11 |
| 255 leaves | **15.376** | 37.798 | **9.759** | -52.880 | 128.19 |
| 511 leaves | **15.376** | 37.798 | **9.759** | -52.880 | 128.19 |

Interpretation: Larger caps **help winner identification in the official baskets**, with pronounced gains from 31 to 127. At 255 the Top-1 plateaus and Top-3 slightly decreases. The 255/511 results are bit-identical: actual trees stop at ~128 leaves on average at the current min-child-weight/regularization/training data; changing only `max_leaves` further has no effect.

## Statistical uncertainty

Paired circular month-block bootstrap (6 months, 4000 replicates) comparing to 31, using one cross-basket mean metric per month. Therefore the overlapping 500 baskets are not treated as independent.

- 127 vs 31: Top-1 +**2.002 percentage points**, 95% CI **[+0.838, +3.151]**; Top-3 +**5.899 pp**, CI **[+3.980,+7.709]**.
- 255 vs 31: Top-1 +**2.156 pp**, CI **[+0.863, +3.422]**; Top-3 +**5.519 pp**, CI **[+3.271,+7.655]**.
- Separate paired 6-month bootstrap 255 vs 127: Top-1 **+0.154 pp**, approx 95% CI **[-0.261,+0.652]**; Top-3 **-0.380 pp**, approx CI **[-1.034,+0.240]**. No convincing difference between 127 and 255.
- Selected excess return difference 255 vs 31: +0.121 percentage points per 21D, 95% CI spans zero. A higher Top-1 hit rate is **not** demonstrated to be a robust economic alpha increase.

## All 149 ETFs vs basket ranking

When selecting one ETF among the entire 149 ETF universe, Top-1 hits were 31=5.94%, 63=6.93%, 127=5.94%, 255/511=4.95%. The IC of the **final V2 score** was 31=.0553, 63=.0448, 127=.0464, 255/511=.0454. Thus the apparently monotonic basket Top-1 improvement **does not transfer directly to universe-wide best-name identification or to IC**.

## Historical replay

- The 255-leaf model produces the best mean CAGR among the tested large-leaf variants: ~9.76% vs ~8.33% for 31 and ~9.14% for native depth4.
- Mean max drawdown is worse: -52.88% for 255 vs -51.89% for 31 and -50.64% native.
- Distinct year-to-year behavior exists: in 2023, 31 outperformed 255 on Top-1 (20.9% vs 18.3%); 2025 favors 255.
- The returned replay summary is historical and does **not** establish a statistically significant Sharpe/CAGR improvement. Real money choice should account for fees, turnover, execution and uncertainty.

## Reproducibility caveat

The earlier 4/8/15/31 experiment performed a separate download of historical Yahoo-adjusted OHLCV data. Its 31-leaf raw predictions differ slightly from the current shared-snapshot rerun (within-month score Spearman ~0.98 on average); **use within-run matched comparisons**, not a combination of incompatible historical snapshots. Both reruns are real experiments, but direct causal claims require frozen identical raw bytes, code and package versions.

## Decision

Large leaf limits **are worth exploring**, and the basket winner results clearly favor the more expressive configurations over 31. The optimal complexity seems to plateau around **127–255 maximum leaves** under today's other constraints. Prefer a further independent temporal holdout and corrected economic paired tests before promoting a new production model.
