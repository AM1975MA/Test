# OLC08 feedback — 1 November 2026

## Verified status, not a completion claim

On the current runtime check, /mnt/data/olc08_systematic_20261101 is absent and no process matching calendar_rebuild.py, calendar_train.py or run_experiment.py is running. The GitHub workflow query for research/olc08-whole-chain-20261101 returns total_count=0. The branch still contains PROTOCOL.md, EARLY_LAYERS_FIRST.md and FEATURE_LEVEL_DIAGNOSTIC.md. Those are protocols, not saved model fits or economic results. Previous temporary build logs cannot be taken as evidence of completed/available forecasts. No new OLC08 CAGR is verified. Parent ZIP archives remain accessible in the conversation runtime. This status does not assert that a complete new training dataset or new OLC08 model checkpoint has been recovered.

## Two freshly reproduced source diagnostics

Read the authenticated parent EU_Original39_RH50_Checkpoint_20261031.zip, source/research/tail-only-and-allocation-ablation-20261017/vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py. Kernel SHA256: fd799f7044f7dd67eb9f2e928e2dbd764b0156d45e59ccb8f2d39d7dfc65229e.

Extracted and executed the original rolling_rsi and rolling_downvol definitions without modification on synthetic data. No model refit and no portfolio simulation.

1. Input inventory: Compact125 =46raw+46percentile+33robust-deviation; Hybrid42. This is an inventory, not proof of relevance or redundancy for every column.
2. RSI: after60 strictly rising closes the source returns NaN; after60 flat closes it also returns NaN; after60 strictly falling closes it returns0. This identifies a domain convention to repair/test explicitly. It does not establish how frequent or economically consequential those cases are in the ETF data.
3. Downside statistic:63 identical daily log returns of -0.01 produce0 for the original negative-only conditional standard deviation at21sessions. Lower-partial RMS on all observations is0.15874507866387544 annualized. These measure different quantities; a zero conditional standard deviation is not a mathematical error. The replacement's predictive/economic usefulness is untested here.

Reproducible synthetic check: for RSI pass DataFrame columns up=arange(1.,61.), down=arange(60.,0.,-1.), flat=ones(60) to the original rolling_rsi; inspect final row. For downside pass DataFrame({'constant_log_loss':[-.01]*63}) to rolling_downvol(...,21); contrast sqrt(clip(returns,upper=0)^2.rolling(21,min_periods=21).mean()*252).

## Remaining work

Restore and persist exact baseline input panels/models before reporting completed annual fits; then execute the predeclared feature/label interventions on both USA149 and EU165. Feature-by-feature out-of-time permutation, learned ablations and downstream portfolio comparisons are not marked complete. No strategy has been promoted, no previous CAGR overwritten, and no background training is implied by this update.
