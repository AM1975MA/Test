# V4 physics/statistical dynamics: signed-return Ridge predictive audit, 27 October 2026

**Status: completed as historical exploratory research, no production updates, NO 500-basket test and NO ~30% CAGR validation.** Exact sources, scorecards, NAV daily and trades are packaged as `V3_PREDICTIVE_ENGINE_V4_20261027_AUDIT.zip` in the ChatGPT conversation. Previous base raw data `eu148_final_corrected_ohlcv.zip`, `EU_GLOBAL_UCITS_20261026_SOURCE_RESULT.zip`. Existing [original 16F Ridge source](EU_GLOBAL_UCITS_BREAKTHROUGH_20261026.md).

## Immutable comparison
- 2018–2026 original 101 monthly signals, same dates for EU148 (European underlying only) vs EU158 (original +10 2026-selected world/US UCITS survivors, **retrospective selection bias**).
- 9 annual fits per scope, all 5/21/63 day forward signed-return labels matured before Jan1 training year, 2012+ expanding history, month-balanced samples, **future EXSA excess raw percentage target, not rank labels**.
- Baseline 16F Ridge alpha250, 8 residual physics features, 6 macro regime features, 6 momentum curvature features, risk-scaled target restored into percentage points, 3 precommitted fixed ensembles. Expanded feature family ridge alpha500. 2018–2026 has been repeatedly inspected; NOT independent untouched test.
- Same original EUR monthly Top3/Top5 economic engine, next observed Open, 10bps one-way fee, no future selection. Model selection not optimized for CAGR; all variants reported.

## Verified results, 101 months

| scope | Top3 strategy | mean monthly IC | EUR Top3 CAGR | Top3 maxDD |
|---|---|---:|---:|---:|
| EU148 | BASE16 | +0.07903 | +6.13% | -29.17% |
| EU148 | momentum+curvature | +0.07910 | +7.98% | -29.56% |
| EU148 | risk-scaled signed target | +0.06279 | **+8.39%** | -31.21% |
| EU148 | naive 12-1 momentum | n/a | +5.31% | -39.28% |
| EU158 | BASE16 | **+0.09236** | +10.15% | -30.23% |
| EU158 | residual physics | +0.07348 | +12.95% | -30.09% |
| EU158 | risk-scaled signed target | +0.08336 | **+13.34%** | -31.54% |
| EU158 | naive 12-1 momentum | n/a | +12.29% | -36.41% |

One-asset concentrated Top1 EU158 maximum in all evaluated variants +19.25% CAGR, -39.81% MaxDD. NO near-30 finding.

**No demonstrably better predictive quality.** 6-month paired 10k bootstrap vs BASE16 for EU158 residual-physics ΔIC -0.01888 (95% [-0.04623,+0.00732]), risk-scaled ΔIC -0.008996 (95% [-0.03365,+0.01320]); annual relative log-NAV vs base risk-scaled +0.0285 (95% [-0.0319,+0.0929]), residual-physics +0.0257 (95% [-0.0376,+0.0885]). These nominal intervals exclude no improvement and do not correct for history-based specification search.

2018–21 vs 2022–26 (EU158 Top3 descriptive CAGR): BASE16 +6.65% / +13.12%; residual-physics +5.96% / +19.33%; risk-scaled +8.39% / +17.58%; 12-1 momentum +5.65% / +18.46%. Sharply regime-dependent, late-only improvement.

## Forecast horizon as a possible correctness flaw
A controlled **strict same-training-row** ablation compares predicted 21 common-session future Open/Open percentage excess vs **exact realized next monthly rebalance Open/Open EXSA-excess target**. Each has same 16 features/Ridge alpha, Jan1 strict exit maturity; no future label used for preselection. On next-month actual realized target, EU148 IC 0.07505 vs 0.07906 but Top3 CAGR **6.13% vs 6.03%**; EU158 IC 0.09450 vs 0.09794 but Top3 CAGR **10.15% vs 9.83%**. Fixed horizon mismatch was real but not an economically relevant solution.

## Responsible conclusion
1. **Reject promoting all expanded mathematical physics feature groups**: more variables and model complexity often reduce IC, inconsistent across calendar regimes.
2. Preserve BASE16 as a non-production challenger reference, and risk-scaled target as a diagnostic only, NOT chosen because of highest backtest CAGR.
3. Neither a 30% CAGR nor 500-basket alpha is demonstrated. Avoid optimizing after seeing OOS returns.
4. Before further hyperparameter search, reconstruct full true broad UCITS universe with inception-aware histories/deceased ISINs (avoid 10-UCITS survivorship) and original 500 baskets, enforce independent vendor corporate-action/spread validation.
5. For true predictive improvement, isolate loss functions/regimes and verify directional IC, Top3 future decile precision, worst-tail rate, calibrated distribution; nested vintage-based tuning and untouched forward paper test. Risk/beta matched benchmark and cost realism required. The user-requested ~30% CAGR is an aspiration and should not be used to backfit parameters.

Sources packaged in the conversation ZIP are fully reproducible Python sources (V4 engine, economic replay with original NAV algorithm, bootstrap, horizon matching, Top1 concentration), all per-year audit files, all scorecards, all per-month forward forecast scores and real daily NAV. Older raw vendor data deliberately not duplicated inside package.
