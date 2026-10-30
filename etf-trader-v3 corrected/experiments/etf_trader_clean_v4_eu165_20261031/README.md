# ETF Trader CLEAN V4 — independently replayed EU165 research, 31 Oct 2026

**RESEARCH-ONLY; MAIN/PRODUCTION V2/V3/B0 UNCHANGED.**

## Frozen design

- Eligible investment pool: per-month as-of union of all 500 STABLE_HASH_MONTHLY baskets of 24 European-listed UCITS ETFs, rather than any one constrained basket.
- Ranked predictive score = **60% V3 Pair25/Hybrid24 percentile + 25% V2 Full Hybrid24 percentile + 15% Momentum252 percentile**. Original annually trained scores frozen; no ranker model was refit.
- Choose 5 assets. Continue to hold an eligible incumbent if its new rank is <=7, filling available slots with best new candidates.
- Inverse of causal trailing 63-session Close-return volatility to size five holdings, normalized, each <=35%.
- Market overlay: only 50% invested when EXSA.DE close as of signal < past 200-session SMA, otherwise 100%. Remaining cash earns 0%; no leverage.
- Monthly signals, genuine next Open trades only; 10bps commission on every buy or sell notional. Missing Open forbids a trade; valuation may carry forward prior Close.
- 10 predetermined controls/ablations; no retrospective grid search or tuning.

## Results, February 2019 through December 2024

Policy | CAGR | Maximum drawdown | Annual gross turnover
---|---:|---:|---:
V3 Pair127 Top5 | 11.00% | -34.14% | 16.34x
V3 Full Pair25+MA200 half | 12.27% | -22.69% | 12.77x
**CLEAN V4 (original design)** | **13.52%** | **-22.61%** | **11.30x**
CLEAN blend+MA200+Top7 buffer, equal weights (ablation only) | 14.38% | -22.53% | 10.54x
CLEAN blend+MA200+inverse vol, no buffer | 11.71% | -22.11% | 12.61x

V4 vs V3 Full MA200 annualized log-return difference +1.12pp, nominal 6-month block bootstrap 95% CI **[-4.21, +7.04] pp**: not statistically significant. Do not promote the highest-performing historical ablation without unseen data.

Regimes show instability: CLEAN V4 CAGR +13.49% in 2019-20, +4.36% in 2021-22, +23.53% in 2023-24; 2025 +27.82% vs V3 Full +36.24% and MOM252 +61.95% (2025 already mined). COST STRESS: raising one-way cost from 10bps to 30bps reduces CLEAN V4 2019-24 CAGR to **10.99%**.

Risk-matched passive benchmark: SXR8.DE (S&P500 UCITS) with the same EXSA-based half-MA200 exposure returned about **15.33% CAGR / -23.59% drawdown** 2019-24. CLEAN V4 fails to exceed its CAGR, although underlying geography is not matched. Paired annualized log difference -1.61pp, block 95% CI [-8.32,+4.73].

## Verification and limits

- 165 European-listed (not necessarily European-underlying) funds, 1,939 market-calendar sessions and 89 proposed monthly PIT events 2019-26; 82 rebalance dates actually executed, 7 skipped due to insufficient month-end scores/quotes.
- Exactly reproduced each of 3 frozen original native V3 daily NAV controls on 1,539 overlapping 2019-24 trading days, max error <=8.9e-16. Ticker scores strictly precede trade Open, with same PIT eligibility.
- Frozen original source-native V2/V3 scores were annual mature-label fits from prior research, not independently trained here.
- Price-only and unknown dividend reinvestment, 2026-surviving ETF universe, no delisted ETF coverage, missing bid/ask, multi-venue market closures, repeated exploration of 2018-26 and no independent untouched holdout. These invalidate confident prospective alpha claims.

**Complete runnable research artifact** ETF_TRADER_CLEAN_V4_EU165_RESEARCH_20261031.zip, 27.7MB / 210 files, SHA256 30f5c356bca938daf38d45c31fb77eac90a620ddbc36d6354f41573d97a65a17. Includes 165 original price histories, 101-month basket PIT source, all frozen native ETF scores, independent Python replay and integrity tests, costs stress, daily NAV, trade ledger, paired bootstrap, passive benchmarks, and Italian report. The GitHub branch holds this concise versioned spec and scorecard; fully runnable code and raw data are in the linked archive from this ChatGPT research run.

**Decision: candidate frozen for prospective validation, no production promotion.**