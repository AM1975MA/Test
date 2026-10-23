# L00.CS1 — cross-sectional daily-asof minmax of ALL 125 feature inputs

**2026-10-23, completed and permanently archived: reject as globally superior model.** Source-exact input: original 149 ETF certified raw OHLCV run 39482809691, original frozen `CORRECTED` OOS Pairwise127 annual control run 39515716383, 500 canonical 24-ETF basket membership SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.

Executed [GitHub Actions 40000704024](https://github.com/AM1975MA/Test/actions/runs/40000704024), [artifact 12521274938](https://github.com/AM1975MA/Test/actions/runs/40000704024/artifacts/12521274938), three independent annual-fit shard jobs **all successful**, 9 chronological annual refits, each using three seeds (101,202,303), objective `rank:pairwise`, max 127 leaves, 360 trees and exact original fit criteria (training 2012–Dec previous year, 21-day exit strictly matured before Jan1). No train/test lookahead. Features: 125 original numerical definitions, but for each available date and feature, ranks of all observable 149 tickers on that SAME date are linearly mapped using same-day min/max to [-1,+1], missing values preserved, constants 0. Original existing 46 `_pct` percentile and 33 `_dev` deviation columns also transformed, no additional model features. Never fit scaler across multiple dates. During this isolated research pass the economic prediction TARGET remains originally monthly 21-trading-day labels; transform is daily-compatible but there are 101 **monthly** matured evaluation dates, not 2,000 daily supervised predictions.

## Matched ranking capability across exactly same 101 mature months and 500 baskets

| Metric | Original CORRECTED125 | CS1 minmax125 | CS1 − control |
|---|---:|---:|---:|
| Future basket winner in Top3 | 35.4713% | 36.9861% | +1.5149pp |
| Future basket winner Top1 | 14.5525% | 14.6812% | +0.1287pp |
| Basket nDCG@3 | **0.542279** | 0.527750 | **−0.014530** |
| Global 149 rank IC | **0.038536** | 0.014360 | **−0.024176** |
| Mean basket Top1 forward 21-day regret | **0.104115** | 0.106932 | +0.002817 |
| Mean selected Top1 forward 21D excess over basket mean | **0.007122** | 0.004305 | −0.002817 |
| Global future-winner Top3 | **16.8317%** | 13.8614% | −2.9703pp |

**Important tradeoff:** higher basket future-winner *coverage* but worse ordering, lower average selected excess return and lower rank IC. Do not confuse higher winner-set hit rate with selected Top1 realized portfolio CAGR improvement; no fee-aware portfolio backtest executed on this research lane.

Paired 6000 replicates × circular **6-calendar-month blocks** over 101 matched monthly basket-aggregated metrics (500 overlapping baskets NOT 500 independent outcomes), results for CS1−control:

| Metric difference | Estimate | Exploratory CI95 | Interpretation |
|---|---:|---:|---|
| Basket Top3 | +0.015149 | [−0.012079,+0.041802] | crosses zero, NOT demonstrated reliably |
| Basket nDCG3 | −0.014530 | [−0.029734,+0.001591] | mostly worse, crosses zero |
| Global rank IC | −0.024176 | [−0.046422,−0.003623] | consistent deterioration |
| Basket Top1 | +0.001287 | [−0.018158,+0.021683] | no material evidence |
| Basket regret | +0.002817 | [−0.001431,+0.006697] | no reliable improvement |

Research only. Original full V2 production and frozen V3 unchanged.

## Calendar heterogeneity
- 2018–2020: mean 500-basket Top3 **29.38% control →32.73% CS1**, while universe rank IC **0.0756→0.0102** and nDCG falls.
- 2021–2023: Top3 **41.81%→41.42%**; global IC −0.0273→−0.0109; Top1 small increase.
- 2024–2026: Top3 **35.17%→36.76%**; global IC 0.0743→0.0508; 2026 worse Top3 than control.

These are all extensively researched years, not independent virgin OOS.

## Decision
**CS1 REJECTED AS FULL REPLACEMENT.** Do not change the original V2 working producer/Hybrid24, frozen Pairwise127, allocation or risk. Cross-sectional day-local information may still be useful as *additional channels*; historical primary Top3 improvement is not significant and global IC worsens. Adaptive exploratory CS2 hypothesis therefore separately predeclared **after observing CS1**: keep the original 125 values and append 46 minmax relative views of only its raw base features (171 total) without changing architecture or fit. This is a new hypothesis-generating trial; do not cherry-pick years or claim CS2 is independent confirmation.

## Reproducibility
- [Preregistration](./20261023_L00_CROSSSECTIONAL_DAILY_MINMAX_PREREG.md)
- [Exactly tested pure normalizer](../experiments/l00_crosssectional_minmax/normalize.py) (at `etf-trader-v3 corrected/experiments/`; relative path GitHub path adjustment if needed)
- [Eval source](../../experiments/l00_crosssectional_minmax/evaluate.py)
- [Aggregate/paired block bootstrap](../../experiments/l00_crosssectional_minmax/aggregate.py)
- [Permanent data archive, all 15,198 OOS ETF months×arm source-original labels plus FIT and normalization audits](./data_run_40000704024/)
- Successful GitHub run above, artifact 12521274938.
