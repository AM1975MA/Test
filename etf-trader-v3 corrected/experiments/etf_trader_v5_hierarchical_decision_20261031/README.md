# ETF Trader — V5 hierarchical active-return decision architecture, 2026-10-31

**Research only; NO source/production modifications. Do not confuse this DESIGN with a fitted/tested V5 model.**

## Why CLEAN V4 is insufficient
A fixed percentile mixture of V3 Pair25/Hybrid24 (60%), V2 Full Hybrid24 (25%) and Momentum252 (15%) is a static ensemble, not a calibrated predictive model of net incremental return. Percentile ranks of different prediction targets cannot be interpreted as expected return differences. Portfolio optimization and market beta remain separate.

## Already-executed falsification: online single-expert contextual router
From frozen EU165 yearly-trained native V2/V3/MOM/Tail scores, select ONE specialist monthly using 21-day realized prior (matured before date) top5-minus-eligible-pool return, EWMA half-life 12 months, conditional EXSA above/below 200-day MA and shrinkage 12 months. Monthly PIT eligible union, next real Open trade, 10bps each side, EXSA MA200 half exposure. Baselines reproduced to max absolute NAV difference 6.66e-16.

**2019–24** V3 Pair25 half MA200 CAGR **12.27%**, MaxDD **−22.69%**; fixed CLEAN V4 **13.52% / −22.61%**; single expert router **7.35% / −25.29%**; router Top7 persistence **10.03% / −23.51%**; router Top7+invvol **10.71% / −23.47%**. Paired month bootstrap router minus reference annual log return **−4.55pp**, 95% CI **[−10.10,+0.27]pp** (includes zero). Router choice top5 average realized next21-day premium against fixed V3 Full **−0.78pp per event** across 65 comparable 2019–24 events, exploratory month-block 95% **[−1.60,−0.15]pp**, no inference after extensive prior research. Router matched best **ex post** among five experts on only ~24% of 66 months. The recent winner is a poor predictor of next winner. **Reject router, no promotion.**

## NEW V5 architecture PROPOSAL (not yet tested)
1. **Causal dynamic factor/state estimation**, 2–3 economically interpretable regimes with uncertainty and change-point probability, no retrospective smoothed latent states.
2. **Hierarchical forecasting** of ETF future total return as factor exposures × latent factor returns + ETF-specific alpha + noise, all exposures point-in-time; separate geographic beta, banks/tech/duration and ETF-wrapper alpha. Weakly identified groups shrink to broad priors.
3. **Native V2/V3/Tail/MOM scores are inputs or shortlist generators, NOT weighted outputs.** Explicit joint calibrated predictive distribution for candidate-minus-incumbent and candidate-minus-passive benchmark at 21,42,63 sessions. Report conditional expectation, quantiles, win probability, tail risk. Train only mature labels and eliminate basket duplicates.
4. **Robust receding-horizon allocation**, include hold, partial/full switch, cash AND investible passive benchmark as outside option; maximize expected growth less transaction costs, turnover regularizer, factor exposure and CVaR constraints, ex ante confidence.
5. **Falsification gate before portfolio CAGR**: match ETF-date/holdings, evaluate probabilistic calibration (CRPS, pinball, Brier), conditional forward alpha net of factor beta and costs, decile uplift, regime stability versus zero-alpha and MOM/factor baselines. Only if validated change portfolio construction, otherwise no active trade.

Fundamental limitations: 2018–26 extensively mined; 2026-curated EU165 ETFs, price-only returns, uncertain dividend adjustment, real spreads, market closures and delistings; **no pristine holdout**. An independent future vintage is required for prospective alpha. No performance of this V5 hierarchical model has been claimed.

Portable standalone audit of R0 negative router and architecture memorandum: ChatGPT attachment `ETF_TRADER_V5_RESET_ARCHITETTURA_E_TEST_ROUTER_20261031.zip`, SHA256 `3a9f8509d264335989865a5e5e669b4aefe52436fe3f52020e19eb3237e0e471`. Contains code runnable within original CLEAN V4 full data archive, 21-day delayed-feedback and causal decision logs, daily portfolio NAV in original working directory and quantitative scorecard; 9 artifact files, CRC passed. The complete runnable EU165 historical input is frozen separately in the earlier CLEAN V4 artifact.