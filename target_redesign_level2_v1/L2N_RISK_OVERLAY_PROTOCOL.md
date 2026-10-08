# L2-N — Single fixed conditional-risk overlay on authentic V2 MA3 execution

2026-10-08, written **before inspection of L2-N backtest outputs**. Repository `AM1975MA/Test` only; do not edit `Etf_trader`. Original149 is heavily researched, so any outcome is **exploratory, not an independent test**.

## Inputs and primary parity gate
Use frozen original149 Repeat2 149 ticker OHLCV and cached source-only 16,986 Titanic `TIT_R` date×ticker scores, MA3 trained OOS `ENSEMBLE_TAIL_OOS`, all from `titanium-repeat-2.zip` anchored in L2-K. Read L2-M frozen `RESIDUAL_VOL_PANEL.csv.gz` (same Repeat2 raw) and use as-of monthly `vol_orthog_rank` and `accel_21_vs_42` only. 2017-01 no L2-M feature: identical to baseline by default; report coverage for later months.

**Must first reproduce** source `holdout70/v2_canonical_same_source_compare.py` with exact producer score=0.475*Titanium +0.525*smoothed[0.6*ET+0.4*XGB]^1.10; same universe ordering and 60%+40% concentration curve; `ddfirst.sync_c95_m75_gross`, `stage19.risk_gross_transform`, `v6.build_v6_state`, `stage19.confidence_weights(current_plus_models_riskoff)`, `stage19.simulate_arch`; baseline matched Repeat2 `compact21_stability_v1/results/FULL_REPLAY.json`: **CAGR 30.84370492564604%; MaxDD -25.689610266686813%; Sharpe 1.0869929498969455**, same date sessions 2366. Tolerances for numerical parity (not hashes): CAGR 0.0001 absolute, DD 0.0001 absolute. If parity fails, do not report risk overlay as an official full-V2 result.

## One frozen intervention — DO NOT TUNE AFTER RESULTS
For the ETF chosen as MA3 first and second rank in a month, tag *fragile* when:
- `vol_orthog_rank >= 0.80` within contemporaneous category, and
- `accel_21_vs_42 < 0` (negative change of mean daily log return latest 21 vs previous 42 sessions).

At monthly next-open the flags are frozen for the current holding month. Define `fragile_exposure=w1*fragile(top1)+(1-w1)*fragile(top2)`, where `w1` is the **canonical post-confidence MA3 top1 weight**. Intervene ONLY through an additional risky-gross cap `gross_cap=1-0.25*fragile_exposure`; daily `G2_overlay=min(G2_baseline,gross_cap)`. Missing as-of 2017-01 features -> no intervention, never future-fill. Preserve all tickers, original ranking, original w1 and stop/risk controller, `GALT=original g`, V6 alt allocations unchanged; additional cash from cap flows through canonical BIL/SHV ledger, not a synthetic 0% cash proxy. No new fit/selector model.

This tests risk-only downside conditioning; it may sacrifice CAGR. **No other cutoff, mix, cap, factor, hysteresis, lookback or regime rule may be tried on this run**. Never overwrite baseline. Do not call a new model stable because it happens to agree on the same Repeat2 history.

## Required results and QA
Reproduce exact daily equity/turnover for baseline and single challenger using same kernel for both; report CAGR, daily MaxDD, Sharpe, mean/risk gross, annualized turnover, total fees, changes of top1/top2 (MUST zero), fraction of dates/months under extra cap, differences in tail/drawdown by year and worst episodes; report trading-impact on BIL/SHV.
Independent checks of feature time causality, monthly risk-flag joins by ticker/date, counterfactual cap never increases risk, exact strategy reconciliation when no active overlay, nonnegative holdings; 3-month block-bootstrap CI on paired MONTHLY log return differences, descriptive only. **No final production endorsement even if it passes**. Golden 43.145952% remains separately unreproduced, cannot compare naïvely.
