# ETF Trader V2 — R0: Cross-sectional return dispersion and Top38 winner recall

**8 October 2026, READ-ONLY quantitative diagnostic.** Repository `AM1975MA/Test`, development branch `research/v2-xgb-immutable-checkpoints-20261008`. No new training, no trading backtest, no strategy updates, no repeated Cascade/L2 experiment.

## User hypothesis
"In 2023–2026 ETF returns are more dispersed, making it easier to identify the best ETF; that may explain the higher first-stage Top38 retention."

**Finding: partially supported, not proven causal.** Extreme winners are further ahead of the cross-sectional median after 2023 and missed winner months have lower return dispersion. However total cross-sectional dispersion has changed only modestly, its interquartile spread is slightly smaller in 2023–2026, and the winner-versus-runner-up gap barely changes. The near-20-percentage-point rise in retriever Top38 recall cannot be attributed solely to standard-deviation differences without a causal predictive test.

## Inputs and exact method (NO new model fitting)
- `/mnt/data/titanium-repeat-2.zip` prior 149-ETF raw-adjusted candidate OHLC snapshot, **SHA256 `1fc7348e0e88329b99e2339a0d488ed94ae102b90b3d05e8e79f1ea06fed4e9a`**; data files `work/original149/candidate_raw/{ticker}.csv` and schedule `work/original149/TIT_R_CANDIDATES_ONLY.csv`.
- Use 114 saved monthly `signal_date`, 2017-01-31 through 2026-06-30, and **exactly 21 trading sessions** forward from `entry_date`, pricing adjusted **Open[end] / Open[entry] - 1**; do **NOT** substitute next monthly `exit_date` (some dates differ).
- Cross-sectional 149 tickers on **every** monthly signal. Compute sample standard deviation `std(ddof=1)`, `Q3-Q1`, `P90-P10`, `best - median`, `best - second-best`, and `mean(Top5) - median`; then average monthly statistics unweighted by date.
- Frozen prior winner source `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/MONTHLY.csv`, Git blob `85ce4db4600efdb701b045d87d89cd099310459a`. Winners from these newly reconstructed O2O21 returns **match 114/114 frozen global_winner ticker IDs**; no missing ETFs.
- Top38 inclusion status drawn from a **previously frozen** `evidence_v1/checkpoints/retriever_ltr_v1/OOS_PREDICTIONS.csv`, Git blob `1745a6d12b6957bc629998c7ac3417550ac9bceb`, as documented and audited in [R0 Top-quartile recall](2026-10-08-r0-frozen-top-quartile-recall.md). There were 97/114 Top38 retained winner months and 17/114 misses; these aren't V2 Compact21 predictions.
- Local stand-alone analysis performed entirely on the frozen archive; 114-row output `OOS149_return_dispersion_monthly_repeat2.csv`, SHA256 `0ded2d6134a35252361adbc57855c97ee3a28cfc293b4d1cf6700b9bbe9f7340`. The local script `dispersion_diagnostic.py` reads only archive OHLC and recreates the descriptive return panel.

## Results (unweighted average of monthly 21-trading-day statistics)

| Cross-sectional metric | 2017–2022 (72 months) | 2023–2026 (42 months) | Description |
|---|---:|---:|---|
| Standard deviation (sample) | **4.5237%** | **4.7518%** | +0.2281 percentage points (~+5.0% relative) |
| Interquartile range (Q75-Q25) | **4.8156 pp** | **4.4155 pp** | -0.4001 pp (smaller later) |
| P90-P10 | **9.7596 pp** | **9.5385 pp** | -0.2211 pp (slightly smaller later) |
| Best ETF - median ETF | **17.4421 pp** | **20.5253 pp** | +3.0832 pp; upper extreme more separated |
| Best ETF - runner-up | **4.5841 pp** | **4.7418 pp** | +0.1577 pp; little change |
| Mean realized Top5 - median ETF | **11.9950 pp** | **14.3089 pp** | +2.3139 pp; upside top tail more separated |
| Frozen retriever Top38 retains future best | **56/72 = 77.78%** | **41/42 = 97.62%** | improvement not proportional to standard-deviation change |

**Conditioned on retention**, using *the same fixed Top38 frozen membership*:
- Across all periods, **retained** 97 months had average future 21d cross-sectional std **4.7202%**, vs **3.9658%** for **missed** 17 months.
- Within **2017–2022**: retained 56 months std **4.6774%** vs missed 16 months std **3.9857%**.
- 2023–2026: 41 retained months std **4.7787%**, **only one missed** month std **3.6469%**: no reliable inference on late-period missed population from n=1.
- Average best-minus-median gap 19.2107 pp in retained months vs 14.9681 pp in missed months (across all 114 dates).

### What is, and is not, established

**Supported:** Extreme positive-return ETFs tend to be further above the median in the later regime. Higher subsequent return dispersion is **associated** with having the realized winner retained inside the frozen Top38. A first-stage 75% elimination has genuinely different risk when the cross-section is compressed vs strongly dispersed.

**Not supported yet:** The claim that overall ETF return heterogeneity is substantially wider in 2023–2026; IQR and P90-P10 are narrower. More importantly, ex-post dispersion is measured **AFTER** the trade decision, and cannot be known when choosing the screen. It might be that years with greater predictability, mature retriever training sample, volatility regimes, ETF constituent makeup or signal structure also drive the higher 2023–2026 recall. Correlation does not establish that spread causes easier forecasting. Nor does ranking the best within broad Top38 guarantee the best strategy portfolio trades or its full V2 CAGR.

**Actionable new analytic question, NOT authorized model fit:** Can a robust *ex-ante* cross-sectional dispersion **proxy** (e.g. cross-sectional spread of trailing 21/63d realized returns known on signal date, not forward returns) predict both future dispersion **and** failure probability of the Top38 filter, with genuinely time-forward validation? Only then consider a variable-strength, recall-constrained funnel. Any adaptive threshold must be predeclared on clean new prospective data; don't tune `K` over already-burned Original149, and do not repeat Top5/Top10 rerankers.

## Audit/provenance
- All 149 prices present per month and correct date calendar; **114/114** reproduced best-ETF identifiers match previously archived global-winner source.
- Original 2026 Repeat2 snapshot is a *different historical Yahoo vintage from Golden*. This measures market cross-sectional return dispersion on frozen Repeat2, **not the Golden source** and is not a new independent performance holdout.
- No uncertainty intervals asserted for regime differences: only 72 and 42 temporally correlated monthly observations, the 2023 cut was under discussion, and repeated past historical research risks selection bias.
- Original full-V2 CAGR differences 29.75–34.68% across Yahoo vintages remain a **separate** stability problem; this descriptive investigation does not prove that a cascade or a different training architecture fixes them.
