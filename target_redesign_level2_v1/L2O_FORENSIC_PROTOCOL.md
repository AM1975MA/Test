# L2-O — Golden/Vintage lineage and June–October 2025 drawdown forensics

**October 8 2026.** No strategy intervention or parameter search. Repository scope exclusively AM1975MA/Test branch research/target-redesign-level2-v1; never modify Etf_trader.

## Questions fixed before forensics calculations
1. What is the true evidence for 43.145952% historical Golden annual V2, and where does the subsequent ~31.604% result differ? Determine whether code, acquisition or execution engine changed; distinguish **data-version effect at the experimental level** from attribution between (a) model score changes and (b) realized price changes. Preserve original GitHub provenance; no fake 43% parity against Repeat2.
2. On same frozen Repeat2 source-only 2017-2026 V2 engine validated in L2-N (CAGR 30.8437049%, daily MaxDD -25.6896103%, daily 2366 sessions), investigate June–October 2025 drawdown with a **day-level self-financing ledger**, decomposing total change into executed selected ticker positions, alternate ETF, BIL/SHV, rebalance costs, stop sale costs and overnight price movements.
3. Describe month-end selections, score margin and concentration, gross caps, shock flags, alternative V6 selection, stop events, market regime (SPY vol/credit/breadth), pathwise opportunity losses and concentration. Split realized loss into return exposure categories and timing, without claiming any factor alpha from ex-post periods.
4. Check whether L2-N failed because high residual volatility and negative acceleration flags were absent in the exact worst peak-to-trough interval, or other policy constraints prevented action.

## Primary source and QA
- GitHub `gap_analysis/results/CROSSED_REPLAY_MATRIX.json` is already a code-hash-gated crossed run: historical Golden 43.1459524%, fresh acquisition Oct2 2026 31.6039946%, *same productive code*, acquisition vintage differs. It did **not** isolate signal vs realized-price effect. `gap_analysis/results/canonical_v2_determinism_control_v1/RESULT.json` finds zero repeat-run changes on byte-identical Repeat2.
- Read unmodified `titanium-repeat-2.zip`, `l2n_risk/l2n_full_replay.py`, `l2n_risk/DAILY_CAPITAL.csv`, `l2n_risk/MONTHLY_RISK_FLAGS.csv`, freeze their hashes.
- Independent financial ledger uses an **independently written Python state machine** reconstructed from `vendor/p45/v2_stage19_kernel.py::simulate_arch` with no model retraining. Reconcile its full 2366 daily wealth array and turnover against the trusted frozen L2-N result to tolerance 1e-9. Reconcile `Σ holding-price contributions − trading fees + stop-sale-gap contributions` to wealth differences. If mismatch, FAIL and omit unsupported quantitative causation.
- Peak-trough date must be derived programmatically using entire daily base equity series, including prior wealth peak; no selecting a different drawdown for convenience. Group by day/month/ticker/category, report **additive P&L in initial-capital units** and optionally normalized monthly impacts. Never sum compounded percentage returns and call the result an exact wealth loss. Track market SPY path for context only.
- No threshold tuning and no counterfactual “what if we sold earlier” strategy; any inference around 43% historical Golden must disclose that raw source snapshots for crossed replay are not included in Repeat2 cache and independent exact mixed replay is not possible from this single vintage.

## Outputs
L2O forensic report, reproducible script, audit checks, peak-to-trough daily/monthly/ticker attribution, regime table, provenance and exact source references. The completed full-V2 forensic must not be described as an independent forward test and must not change production.
