# G6 original149 — test matched weighting transfer, frozen BEFORE G6 backtest
Date: 18 October 2026. Frozen G5 prequential risk estimation verified an EWMA126 squared-return estimator, decay 0.97, beats naive 63d realized variance forecast on 320 mapped ETF sleeve events. **Do not infer return alpha from that result.**

Decision question: with the SAME six ETFs chosen in the previous R3 (one ETF per macro category at exactly the same monthly first Open) and the SAME OASIS original149 price score, does EWMA126 inverse-volatility portfolio sizing improve *realized capital survival* compared with the previously completed R3 63d inverse-vol weighting?

Two policies only:
- R3 original frozen `oasis149/results/R3_GROUP_INV_VOL.csv`, no changes. Recompute it with unchanged `oasis_v2.g2.risk_portfolio.simulate` and prove strict 2366-day wealth numerical parity <1e−8.
- R7 EWMA126_INV_VOL: exactly the same monthly membership from R3; calculate only as-of log Open returns up to the PREVIOUS signal close. EWMA variance = weighted average last 126 squared daily Open/Open log returns with decay 0.97, new relative risk weights proportional to inverse square-root of that statistic, 25% weight cap, six instruments, 100% risky. Same `execute_targets` next Open share accounting with 0.1% nominal one-way fees and no leverage. No daily rebalance, no dynamic cash, no G1/G4 failed probabilities, no additional tuned thresholds. No selection changes or growth boosting.

**Predeclared metrics and gates:** 2017–26 CAGR, daily MaxDD, ES5, Sharpe, total nominal turnover, cumulative nominal fees, 2017–20/2021–23/2024–26 era returns, 12month circular block bootstrap of paired monthly growth relative R3. "Material G6 improvement" requires R7 daily MaxDD and ES5 both better than R3 AND >99% of R3 CAGR AND paired monthly 95% interval of relative log gains >0. If anything fails, leave R3 or 60/40 as economic comparator; do NOT optimize EWMA lambda or 25% cap on same history. Risk-only G6 cannot manufacture information on new ETF opportunities.

Also report existing source 60/40 SPY/AGG same adjusted open, NOT fully cost matched. Scientific historical ETF source is survivor- and vintage-biased and already repeatedly used, with no true PIT fund universe, trading currency or spreads. No production actions. Archive full R7 daily ledger, diagnostics and hash.
