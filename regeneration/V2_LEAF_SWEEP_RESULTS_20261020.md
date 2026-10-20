# ETF Trader V2 — 4 / 8 / 15 / 31 leaf ablation (20 October 2026)

## Execution
- GitHub Actions run: https://github.com/AM1975MA/Test/actions/runs/39476054906
- Result: SUCCESS, source-only validation PASS.
- Branch: research-v2-leafcaps-20261020.
- Original 149 ETF historical OHLCV snapshot (frozen through 2026-07-01), 500 official baskets × 24 names.
- 125 V2 Compact features, original rank:pairwise XGBRanker, 360 trees, learning_rate 0.035, seed ensemble 101/202/303.
- Annual causal training and mature 21-day ranks; OOS signals from 2018-01-31 through 2026-05-29 (101 months, 2017 skipped due training minimum).
- Experiment variants: XGBRanker grow_policy=lossguide, max_depth=0, max_leaves=4,8,15,31.
- Control: original depth-wise XGBRanker max_depth=4 (not exactly the same growth policy).
- The V2 fixed 70% Compact21 + 30% Tail + macro bonus blend is held constant across variants; no F3/H1/H3.
- Replay uses 500 baskets, cost=0.001, and otherwise unchanged simulation.

## Results: 500 24-ETF baskets, 2018-2026 May

| Model | True winner selected (Top-1) | Winner among predicted Top-3 | Mean CAGR | Mean max drawdown | Mean 21D selected excess |
|---|---:|---:|---:|---:|---:|
| 4 leaves | 9.5525% | 21.9327% | 10.3905% | -43.3349% | 0.4978% |
| 8 leaves | 9.8178% | 23.0238% | 8.7368% | -44.6895% | 0.3715% |
| 15 leaves | 10.9287% | 26.1307% | 8.9457% | -46.5276% | 0.4113% |
| 31 leaves | 12.7842% | 30.9465% | 7.3384% | -52.0495% | 0.3767% |
| Original V2 depth4 | 12.9782% | 30.3069% | 8.9398% | -51.3204% | 0.5165% |

The winner-identification metrics are means over basket-date observations (500 correlated baskets per date). **Do not** treat 50,500 basket-months as independent statistical replications.

## Source-level signals (universe-wide)

| Variant | Cross-sectional Spearman IC | Top-1 | Top-3 | 21D selection excess |
|---|---:|---:|---:|---:|
| 4 leaves | 0.08236 | 2.9703% | 9.9010% | -0.1744% |
| 8 leaves | 0.07877 | 4.9505% | 5.9406% | 0.6671% |
| 15 leaves | 0.07040 | 3.9604% | 8.9109% | -0.3362% |
| 31 leaves | 0.05270 | 6.9307% | 13.8614% | -0.2035% |
| Original depth4 | 0.06577 | 6.9307% | 12.8713% | 0.5426% |

## Paired uncertainty (exploratory)

Paired circular 6-month block bootstrap, 10,000 resamples of **month-level average** metrics across 500 baskets, not bootstrap over independent basket rows.

| Comparison 31 leaves vs | Top-1 improvement (percentage points) | Approximate 95% CI (pp) | Top-3 improvement (pp) | Approximate 95% CI (pp) |
|---|---:|---|---:|---|
| 4 leaves | +3.23 | [+1.44,+5.13] | +9.01 | [+6.39,+11.61] |
| 8 leaves | +2.97 | [+1.34,+4.67] | +7.92 | [+5.38,+10.39] |
| 15 leaves | +1.86 | [+0.55,+3.28] | +4.82 | [+2.72,+6.94] |
| Original depth4 | -0.19 | [-1.50,+1.11] | +0.64 | [-1.60,+2.68] |

The 31-leaf model more frequently finds the best ETF than the shallower experimental models. That advantage does **not** automatically mean better realized return, CAGR or drawdown. In this sample, 4 leaves performed best on replay's mean CAGR and mean maximum drawdown. The native depth4 model is a separate architectural reference (lossguide vs depthwise), so do not use its small difference vs 31 as proof of an isolated leaf-count effect.

**Caveats:** data end on 2026-07-01; only May 2026 has matured 21D OOS evaluation. The 2017 OOS year is absent due to insufficient eligible training months. Results are historical, not future forecasts. A stricter economic analysis should use independently held-out final data and corrected paired risk metrics.

## Archived detailed files

GitHub Actions artifact `v2-leaf-caps-results` (artifact ID 12290896039), uploaded at completion:
- `runs/v2_leaf_sweep/RESULT.json`
- `runs/v2_leaf_sweep/REPLAY.csv`
- `runs/v2_leaf_sweep/UNIVERSE_MONTHLY.csv`
- `runs/v2_leaf_sweep/BASKET_MONTHLY.csv`
- `runs/v2_leaf_sweep/OOS_SCORES.csv`
- `certification/source_only_input_gate.json`

GitHub Actions artifacts have retention expiration (30 days in this workflow). This Markdown report keeps aggregate results versioned in Git.
