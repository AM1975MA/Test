# ETF Trader V3 Corrected

**Research track isolated in `AM1975MA/Test` main.** Created 21 October 2026.

## Purpose

Rebuild ETF Trader one layer at a time, with mathematically corrected features and strictly chronological, audited OOS training. No existing V2 source, main workflow, production strategy, or archived baseline is overwritten.

**Status: L00 input/feature layer UNDER TEST. No V3 layer yet promoted as validated.**

The completed historical V2 experiments showed that merely correcting 125 features, removing representations, or adding three negative-day fractions did **not** establish a ranking or CAGR improvement. We do not relabel that data as a virgin holdout.

## Frozen reference contracts

- 149 canonical ETF tickers and the exact frozen OHLCV from GitHub Actions run `39482809691`, artifact `12292840548`.
- 500 fixed baskets × 24, SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- 2018–2026 annual expanding fits, strictly matured 21-trading-day labels and identical original eligibility.
- 127-leaf XGBRanker, 360 boosting rounds, 3 deterministic seeds (101,202,303) while investigating **features only**.
- V2 reference OOS scores from successful GitHub Actions run `39515716383`; exact 15,198 legacy ETF-month predictions matched the official V2 results numerically.
- All features calculated from prices available on the signal date. Features and targets must not mix adjusted and raw price semantics silently.
- Keep legacy production running; no merge of corrected formula PR until separately validated end to end.

## Layer order (strict single-variable experiments)

| Gate | Layer | Frozen while optimizing | Deliverable |
| --- | --- | --- | --- |
| L00 | Data/source + feature definitions | All model hyperparams and all downstream layers disabled | Complete 125+ feature contract, missingness audit, OOS feature-family ablations |
| L01 | Predictive ranker | Winning L00 feature schema, no tail/macro/risk | Annual nested walk-forward feature/model stability, balanced IC, Top1/Top3, regret |
| L02 | Tail and asymmetric-loss model | L00+L01 fixed | Incremental paired analysis incl. drawdown-sensitive target |
| L03 | Market regime and RMT/macroeconomic context | L00–L02 fixed | Causal regime features vs gating, no ex-post switching |
| L04 | Expert blend and final rank | L00–L03 fixed | Frozen blending weights vs train-only OOS calibration |
| L05 | Basket allocation/rebalance and cost | All score layers frozen | Next-open execution, stable portfolio weights, costs, turnover |
| L06 | Risk, drawdown, stop/tail controls | All selection/allocation frozen | DD/risk trade-off, exposure/stops without price lookahead |
| L07 | Integration/certification | All layers locked | Full strategy replay, source-only rebuild and comparability against immutable V2 |

Move to the next layer **only after** recording a numeric baseline, OOS paired uplift/uncertainty, per-regime/year sensitivity, economic replay, winner/loser decision and source hash. Do not revise previously frozen layers in the middle of a downstream comparison; any reversion creates a new V3 version.

## Qualification rules

1. A layer with better one-off CAGR but worse Top-3/IC/regret or increased tail drawdown is not automatically better. Show the multi-objective trade-off and use a predeclared hierarchy by layer.
2. Treat the *calendar month* as the statistical unit for prediction experiments; 500 overlapping baskets are not independent. Use paired 6-month block resampling and Holm-adjust for tested arms. Show year-wise results.
3. Never tune selection to 2018/2022/2025 and then call the same years an independent holdout. 2018–2026 has already been used for research and is an **exploratory historical replay**. Reserve new temporal/source vintages for independent validation before promotion.
4. Always rerun the original baseline in the exact same setup or fetch its separately audited, numerically identical OOS scores and prove date and ETF parity.
5. Keep all rejected variants and their artifacts; no silent disappearance of unsuccessful experiments.

## Layout

- `src/etf_trader_v3/source_only/`: self-contained versioned baseline corrected implementation, copied from tested V2 corrected kernel and shared source files.
- `experiments/l00_features/`: candidate feature engineering and isolated feature-only experiments.
- `docs/`: methodology, audit and layer register.
- `reports/`: frozen results and accept/reject decisions.
- `workflows/`: actual CI/CD logic lives at `.github/workflows/v3-l00-feature-engineering.yml`.

**Historical technical studies**
- [Mathematical corrections and economic comparison](https://github.com/AM1975MA/Test/blob/research-v2-formula-retrain-20261021/regeneration/V2_FORMULA_RETRAIN_RESULTS_20261021.md)
- [Negative-day frequency experiment](https://github.com/AM1975MA/Test/blob/research-v2-negative-frequency-20261021/regeneration/V2_NEGATIVE_FREQUENCY_RESULTS_20261021.md)
- [Feature family ablations](https://github.com/AM1975MA/Test/blob/research-v2-feature-confirmation-20261021/regeneration/V2_FEATURE_CHANNEL_ABLATION_RESULTS_20261021.md)
