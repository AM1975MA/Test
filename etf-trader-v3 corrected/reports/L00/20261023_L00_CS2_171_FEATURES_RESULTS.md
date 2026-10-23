# L00.CS2 — 125 original + 46 normalized raw feature views (171 total), out-of-time chronological rerun

**23 October 2026, completed, NOT PROMOTED.** Research design was created **after examining CS1 result**; 2018–26 has been researched repeatedly, so this adaptive extension is evidence of mechanism, not a statistically fresh/confirmatory OOS selection. Preserve original production V2 Hybrid24 and original corrected 125-feature frozen V3 rankings.

## Exact tested model
- Fixed original OHLCV 149 ETFs [Actions raw run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691); canonical 500×24 ETF baskets, SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`; frozen original CORRECTED 125 pairwise oracle refit [39515716383](https://github.com/AM1975MA/Test/actions/runs/39515716383).
- **All 125 original corrected input columns remain byte-for-byte the same values**, including 46 original raw features + 46 percentile `_pct` + 33 robust cross-sectional deviation `_dev` channels. Add 46 extra `_csminmax` features computed from their original 46 raw columns by min/max over all *same as-of date* observable 149 ETFs, linearly map min to -1 and max to +1; missing is missing, constant is 0. Never normalize or fit scaler using later dates. Total X input dimensionality **171**, new random forest features no, only original XGBRanker.
- Exact original 127-leaf max, 360 trees, rank:pairwise 21-trading-day matured ordinal monthly target, fixed seeds 101,202,303; chronological annual expanding model fit 2018..2026, Jan1 maturity gate, 101 common matured MONTHLY signals. Daily-local normalization is valid at any trading day; this experiment uses only original monthly supervised labels/decisions and makes NO DAILY SUPERVISED LABEL claim.
- All nine year fits successful in [GitHub Actions run 40002047219](https://github.com/AM1975MA/Test/actions/runs/40002047219); its initial aggregate **failed only artifact glob name** after three successful unmodified fits. An aggregation-only workflow then reused the exact immutable original three shard artifacts with no retraining: **successful [40003064949](https://github.com/AM1975MA/Test/actions/runs/40003064949)**, artifact **12522887492**, complete OOS predictions, paired monthly score, annual score, original feature audits and 6-month block bootstrap. Independently archived to V3 main by Actions **40003374170**.

## Matched result, 101 mature monthly signals, same 500 dependent baskets

| Metric | Frozen CORRECTED 125 | CS1 all normalized 125 | CS2 125 + 46 = 171 |
|---|---:|---:|---:|
| 500 basket future winner in Top-3 | **35.4713%** | 36.9861% | 36.8713% |
| 500 basket future winner in Top-1 | **14.5525%** | 14.6812% | 14.3941% |
| 500 basket nDCG@3 | **0.542279** | 0.527750 | 0.532253 |
| Full 149 ticker universe rank IC | **0.038536** | 0.014360 | 0.019145 |
| Basket selected Top-1 forward regret | **0.104115** | 0.106932 | 0.106405 |
| Basket selected Top-1 future 21D excess return over basket mean | **0.007122** | 0.004305 | 0.004832 |

CS2 increases captured winners in the candidate Top-3 **+1.4000 percentage points vs the original control**, but loses 1.0026% nDCG3 (absolute −0.010026), reduces global rank IC by −0.019390 and selected Top-1 future return excess by 0.00229 = 0.229 percentage points. It does not beat the original strong model across its actual intended top-ranked-ETF selection quality. The 171 model is somewhat better ordered than CS1, but slightly worse Top-3 coverage than CS1. No global strategy/portfolio CAGR trial is justified yet.

Paired original-month aggregated 500-basket 6-calendar-month circular moving block bootstrap (6,000 resamples) on CS2 versus original:
- **Top-3** +0.014000, CI95 **[−0.006119,+0.034713]**, includes zero (exploratory p≈0.198).
- **nDCG3** −0.010026, CI95 [−0.022826,+0.003622], includes zero.
- **Global rank IC** −0.019390, CI95 **[−0.034551,−0.004536]**, excludes zero in unfavorable direction.
- **Top1** −0.001584, CI95 [−0.016990,+0.014654].
- **Basket regret** +0.002290, CI95 [−0.001102,+0.005598].

No bootstrap treats 500 overlapping same-month baskets as independent.

## Year-to-year stability
Mixed/unstable. CS2 Top-3 from 2018 original 31.0167% →29.7833%, from 2019 29.50%→34.233%, from 2022 45.50%→50.57%, 2023 42.48%→40.02%, 2025 37.42%→42.13%, and 2026 43.80%→39.28%. Even where captured winners increase, global rank IC often gets worse. One cannot select only favorable years or blend configs retroactively.

## Decision
**DO NOT replace CORRECTED125 with either CS1 or CS2 on present evidence.** The 149-ticker future-winner *candidate coverage* improves, but neither normalizer shows significant 500 Top-3 improvement under calendar-block uncertainty; both worsen global rank IC, and selected Top1 rank and future regret. Existing original 125 has relative percentile and deviation features; indiscriminate minmax adds redundant/tail-sensitive information and dilutes absolute regime signals. A much more targeted next hypothesis is loss-aware, factor/regime conditional ranking with feature-family ablation and true virgin holdout, but no further within-sample exploration or production promotion here.

**Not tested:** re-training the original full V2 Hybrid24 stack, weekly risk/stop overlay or fee-aware executable portfolio CAGR on these new normalized predictions. The research deliberately isolates only upstream ranker to avoid conflating the known productive 24–25% V2 500-basket or 34.47% global 149 ETF control with standalone rank skill.

## Files and verified runs
- [Adaptive CS2 protocol](./20261023_L00_CS2_171_FEATURE_ADDITION_ADAPTIVE_PREREG.md)
- [CS2 annual fit script](../../experiments/l00_cs_add171/evaluate.py), [point-in-time normalizer](../../experiments/l00_cs_add171/normalize.py), [calendar bootstrap aggregator](../../experiments/l00_cs_add171/aggregate.py)
- [Archive directory with exact predictions and source audits](./data_run_40003064949/).
- [Fit 40002047219](https://github.com/AM1975MA/Test/actions/runs/40002047219), [successful no-refit aggregate 40003064949](https://github.com/AM1975MA/Test/actions/runs/40003064949), artifact **12522887492**, [archive to main 40003374170](https://github.com/AM1975MA/Test/actions/runs/40003374170).
