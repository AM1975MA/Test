# V6 scientific review and 56 exact EU155 / USA149 residual momentum backtests — 2026-10-27

**Status: COMPLETED / EXPLORATORY / NOT DEPLOYED.** Raw 148 fully selected legal EU ISIN preserved; 6 same-ISIN Yahoo EUR quotation alternatives (2026 audited); plus 7 EU national-index UCITS, final **EU155**, not opportunistic global Xetra 10. The original 149 US ETF group (US149) is unchanged.

## Scientific research motivating *one* primary model
- Blitz, Huij, Martens (2011): [Residual Momentum](https://doi.org/10.1016/j.jempfin.2011.01.003). Residual return momentum can remove common equity-factor exposure, but paper concerns stocks, **not** direct validation on UCITS.
- Moskowitz, Ooi, Pedersen (2012): [Time Series Momentum](https://doi.org/10.1016/j.jfineco.2011.11.003). Persistent price trends motivate fixed simple control.
- Daniel & Moskowitz (2016): [Momentum Crashes](https://doi.org/10.1016/j.jfineco.2015.12.002). Momentum can crash in adverse rebound regimes, be careful with risk gates.
- Gu, Kelly, Xiu (2020): [Empirical Asset Pricing via ML](https://doi.org/10.1093/rfs/hhaa009). Nonlinear predictors can help huge equity-stock datasets but no guarantee in 155 ETFs.
- Harvey, Liu, Zhu (2016): [Cross-Section of Expected Returns](https://doi.org/10.1093/rfs/hhv059). Avoid data-mining, adjust multiple testing.
- Bailey et al.: [Probability of Backtest Overfitting](https://escholarship.org/uc/item/4w1110bb). Historic repeated specification search invalidates virgin OOS interpretation.

**Primary pre-economics model:** `residual12_1 = simple_return_ETF(t-252,t-21) − beta_126(t)*simple_return_benchmark(t-252,t-21)`; beta estimated only up to signal close. EU market benchmark `DE0002635307`, US benchmark `SPY`. Combine frozen annually matured 21-session signed-percentage Ridge predictor monthly percentile with residual momentum monthly percentile at fixed equal 50/50 weight. No rank-label training in Ridge. Companion controls predeclared: MOM252, momentum12–1, Ridge21, Ridge+MOM252, pure residual, raw+residual, Ridge+residual.

## Input and QA
101 shared historical monthly decision dates Jan2018–May2026; execution next actual Open Feb2018–June2026; terminal 1-Jul-2026; 2076 daily marks. EUR for both (US FX from earlier frozen SPY passive reference), fees 10bp each actually traded side, equal weight Top3 and Top5; eligibility base or as-of liquidity (63d volume positivity ≥90% and median ADV ≥50k). 7 policies × 2 top widths × 2 eligibility × 2 universes = **56 actual fully executed scenarios**. EU duplicate IBEX35 products are prevented from being simultaneously selected.

All 56 trades/NAV executed with **zero missing holding quote failures**. Historical venue data are not independently validated executable prices; **3 trades with zero Yahoo volume in EU155 Ridge+Residual Top5**, cannot claim feasible liquid fills. 2026 venue selection and survival create selection bias. 2018–2026 thoroughly researched previously; no independent holdout.

## EU155/USA149 comparative net EUR Top5, as-of liquidity
| Policy | EU155 CAGR | EU155 MaxDD | USA149 CAGR | USA149 MaxDD |
|---|---:|---:|---:|---:|
| Momentum252 baseline | **8.80%** | -35.35% | **21.23%** | -37.27% |
| Momentum12–1 | 6.28% | -33.69% | 13.57% | -38.44% |
| Residual momentum pure | 7.04% | -31.99% | 12.29% | -37.61% |
| Frozen Ridge21 | 5.10% | -40.51% | 19.64% | -44.44% |
| Ridge+Momentum252 | 10.90% | -31.49% | 14.13% | -35.45% |
| **Ridge+residual12–1** | **13.64%** | **-29.71%** | 18.15% | -32.31% |

EU155 Top3 Ridge+residual **14.21%** MaxDD -29.39%, vs Ridge+MOM252 10.11%, MOM252 6.13%; USA Top3 Ridge+residual 14.28% vs original MOM252 21.05%. **US must remain on its frozen winning line**, no one-size-fits-all selection.

## Chronological uncertainty (NOT causal independent validation)
Paired 101-month **6-month circular block bootstrap R=15000**, nominal CI unadjusted for testing 56 candidates:
- EU155 LIQ50 Top5 Ridge+Residual vs MOM252: annualized log-return delta **+4.35pp**, nominal CI95 **[-4.24pp,+12.80pp]** — includes 0.
- EU155 LIQ50 Top5 Ridge+Residual vs Ridge+MOM252: **+2.44pp**, nominal CI95 **[-0.26pp,+5.20pp]** — includes 0.
- EU155 LIQ50 Top3 Ridge+Residual vs Ridge+MOM252: **+3.65pp**, nominal CI95 **[-0.13pp,+7.72pp]** — includes 0.
- EU155 historical 2018–2021 Top5 MOM252 +1.07%, Ridge+Residual +6.11%; 2022–2026 MOM252 +16.00%, Ridge+Residual +20.62%. Already-explored subsamples.

Monthly cross-sectional Spearman IC mean for EU155 liquid eligibility: MOM252 +0.0380, Ridge +0.0491, combined Ridge+residual +0.0901, residual pure +0.0393. Correlations descriptive only.

Controls: EU155 MOM252 Top5 +8.80% reproduces previous 8.79%; USA149 MOM252 +21.23% and frozen Ridge +19.64% reproduce original benchmark. Original V2 USA500 Hybrid24 +22.01% **mean basket CAGR** is DIFFERENT from this free ETF Top5.

## Decision
**Keep Ridge+Residual as EU155 candidate but do not promote**. No 30% result; no statistically demonstrated alpha above benchmark. Keep USA149 momentum252 and original V2 separate, untouched. Require independent ETF venue EOD/spreads, split-dividend QA, delisting survivorship and genuinely new forward vintages.

**Full exact-source code, forecast factor panel (101×155, 101×149), 56 scorecards, all 2076 daily NAV series, 101 monthly TopK selections, 15k block bootstrap results and calendar splits** in conversation file `V3_EU155_US149_SCIENTIFIC_RESIDUAL_MOMENTUM_20261027.zip`, sources `run_residual.py`, `bootstrap_finalize.py` and `MANIFEST.json`. Source archives retained separate, no production changes.
