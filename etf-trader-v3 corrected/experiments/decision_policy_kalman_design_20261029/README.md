# ETF Trader — dynamic allocation, Kalman and residual design specification

**29 October 2026. RESEARCH SPECIFICATION ONLY.** No newly executed Kalman tests, no new performance claims, no changes to original B0/V2/V3/USA149 or production.

## Critical empirical premise

B0 MOM252 EU155: 2018–2024 CAGR ~2.6%; 2025 +76.8%; whole February 2018–July 2026 CAGR ~8.8%, MaxDD ~-35.3%. A 2025 bank-sector success does **not** make 252-day momentum the validated winner. The objective is to improve pre-2025 weak regimes while retaining persistent sector trends. V2/V3 EU165 were only natively tested in a 2025 fitted pilot; never infer multi-year superiority.

## Reframe from ranking to decision

Given historical ETF eligibility, daily OHLCV, current weights and all observable information through signal date t, choose HOLD vs SWITCH vs REDUCE/INCREASE; maximize uncertain **incremental forward net expected utility relative to the assets already held**, after costs, drawdown/tail risks, uncertainty and factor exposure. Six macro-clusters represent candidates, not mandatory equal weights.

## Separately testable hypotheses

1. Group-economy trend (sector/country/market/bonds/duration) drives much of B0's performance, particularly banking ETF duplicates. Distinguish group selection from within-group ETF selection.
2. Momentum252 is too slow at leadership transitions; estimate 21–63 day relative acceleration and leader persistence independently.
3. **One-sided Kalman filtered estimates** of latent relative drift and covariance add information over cheap EWMA/multihorizon momentum. Never use *smoothed* states or full-window parameters in historical signals: those contain future information. A constant-gain Kalman filter can reduce to an EWMA; incremental predictive benefit must be proven.
4. Do not confuse a time-series one-step Kalman **innovation** with an ETF cross-sectional **factor residual**. An innovation should be close to unpredictable if the filter is well specified. A positive standardized surprise is not necessarily expected continuation. Model group drift and within-group ETF deviations separately.
5. The original V2 Hybrid24 is 47.5% base, 52.5% Tail; V3 Pair25 changes 25% of base or only 11.875% of nominal final score. Do not let risk models silently override opportunity/sector ranking. The 2025 Tail suppresses banking, but bearish-year value is untested.
6. Switching requires an uncertainty-aware **no-trade region** and next-Open execution; expensive frequent changes can overwhelm ranking skill.

## Ordered falsifiable studies

- Phase 0: Verify PIT ETF universe, adjusted total returns/dividends, trading line currencies, historical market closings, cash proxies, synthetic gaps and exact source engine parity.
- Phase 1: On pre-2025 diagnostic replay, decompose late trend entry, premature exit, false switches, sector allocation and within-sector selection. Use 2025 as explicitly mined trend stress and 2026 as partial stress; not pristine holdouts.
- Phase 2: Blind-style *chronological expanding fit*: compare MOM252, 12−1 month MOM, 63/126 momentum, EMA, simple Kalman drift, group Kalman, factor-residual features and innovations. Evaluate 5/21/63-day forward excess returns, monthly rank IC, switch-vs-hold net classification and lead/lag, using matured labels only.
- Phase 3: Keep identical allocation/risk/cost policy for V2 Titanium, V3 Pair127, B0 and new Kalman candidates. Ablate Tail only separately. Assess CAGR/net log growth, MaxDD, CVaR, turnover, spread stress and 2018/2020/2022 weakness; ensure the pre-2025 gain is not explained by selection of the 2025 bank rally.
- Phase 4: Paired month-level dependence-robust uncertainty, multiple testing, source hashes, no promotion until additional unseen data.

**Authoritative downloadable expanded technical report** (includes equations, causal Kalman model, distinction between two types of residuals and methods) was created in conversation artifact `ETF_TRADER_MODELLAZIONE_ALLOCATIVA_KALMAN_RESIDUI_20261029.md`, SHA256 `3e8c20d6147f3e7b3087e5f62177758689d06950dd11c3e2bbeff8f50852c4f5`.

Theory: Gârleanu & Pedersen (2013) dynamic trading with costs (NBER w15205); Daniel & Moskowitz (2016) momentum crashes (NBER w20439); Moskowitz/Ooi/Pedersen (2012) time-series momentum; Statsmodels state-space filtered vs smoothed states.
