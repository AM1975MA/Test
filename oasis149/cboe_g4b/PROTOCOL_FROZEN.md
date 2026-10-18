# OASIS149 G4b — option-implied volatility information (CBOE): protocol FROZEN
Data: 18 Oct 2026. Branch: `research/oasis149-cboe-impliedvol-g4b-20261018`.
Universe: the EXACT original 149 ETFs and their immutable raw price SHA; no Top150, 69 or EUR60. Core causal pair generation, labels and training unchanged from original149 G1: choose up to eight as-of challengers for two current shadow holdings, plus 64 deterministic cross-group probes per independent 21-session monthly anchor. 64 evaluation anchors 2021–26, 5120 pair forecasts; labels Open-to-Open realized 21 sessions later, conventional 0.003 log cost, never read before maturity.

## Independent source, not an ETF OHLCV proxy
Official CBOE closing implied-vol indices downloaded from `https://cdn-api.cboe.com/api/global/us_indices/daily_prices/{SYMBOL}_History.csv`:
- VIX — SPX 30-day implied volatility;
- VVIX — VIX-of-VIX second-order uncertainty;
- OVX — oil ETF implied volatility;
- GVZ — gold ETF implied volatility;
- VXEEM — emerging-market ETF implied volatility.
Five different risk processes from listed option prices, not ETF trailing returns. Official data archive: https://www.cboe.com/tradable_products/vix/vix_historical_data (also historical source disclaimer). All five CSV source raw content must be downloaded fully, schema validated, date coverage from <=2016 to >=2026-07, duplicates rejected, observed Close positive finite, raw and filtered hash manifest committed. **No fallback** to ETF-derived pseudo-implied-vol.

For every as-of signal close s only use CBOE observation Close `date <= s - 7 calendar days`; for changes use value as-of 21 calendar days earlier. Last observation must be <=14 calendar days older than respective cutoff; if not, abort. Time fence makes accidental future-date joins impossible, but **not a full point-in-time vendor vintage certification** for historical CBOE restatements. Do not claim actual option execution or fund investability.

## Predeclared direct hypothesis comparison, NO return-driven hyperparameter search
- H0 PRIOR: same online matured-label empirical advantage rate, clipped [0.1,0.9].
- H2 PRICE_GROUP: unchanged 13-dimensional factor-adjusted price score, logistic L2 C=.15, scaler train-only.
- **H5 IMPLIED_VOL_CONDITIONAL (primary):** H2 features + log1p of each of five implied-vol levels (5) + changes in those levels over 21 calendar days (5) + 10 fixed asset group interactions: `logVIX*group_diff_vector_of_6`, `logGVZ*realasset_diff`, `logOVX*realasset_diff`, `logVXEEM*emerging_diff`, `logVVIX*US_broad_diff`; total 33 features. L2 C=.08 and training-only standardizer.
- H6 IMPLIED_VOL_COMPACT (ablation): H2 + five log levels only, 18 features, C=.08.
Do not retune regularization, dimensions, smoothing, sample, candidate list, cost or success threshold after seeing results.

All 4 probabilities fitted only on matured labels `label_exit_OPEN < asof_signal_CLOSE`. Per-anchor equal total sample weight. Same group identifiers and original P3 shadow holdings as the previous run; no G1 H2 prediction integrated into trades.

**Score gate:** H5 challenger-task Brier and logloss better than BOTH H0 and H2 over all 64 anchors, lower Brier than H0 separately 2021–23 and 2024–26, and 95% three-anchor block bootstrap H5-vs-H0 Brier improvement entirely positive. No new backtest of execution unless gate passes. Shadow acceptances p>.65 and margin over H0>.10, maximum one per anchor; labels ex-post only, never train/lookahead.

**Why this experiment is genuinely different:** macro information from options can reflect prospective dispersion and changing demand for insurance in equities/energy/gold/emerging risk; target remains pair advantage *net* of costs. Negative results must be retained. It is a five-factor diagnostic in an ALREADY-mined 149 ETF sample, not an independent prospective holdout. All original ETF OHLCV is Yahoo-adjusted, not verifiable broker fills, and only six broad (sometimes overlapping) categories are supplied. No actual EUR cash/FX/fees. Even a G4b score-gate PASS is research-only pending PIT provenance and new out-of-sample dates.

**Persistence:** raw official CBOE input, hash-and-availability manifest, 5120 full out-of-development records with each factor as-of source date, proper scoring with per-era results, uncertainty CI, and coordinator conclusion saved under `oasis149/cboe_g4b/results/`. Original production `etf_trader` unchanged.
