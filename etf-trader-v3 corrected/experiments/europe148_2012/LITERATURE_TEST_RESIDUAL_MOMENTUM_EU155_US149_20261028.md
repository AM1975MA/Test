# Literature-informed Residual Momentum — EU148 / EU155 / USA149 (28 Oct 2026)

**Status:** 24 matching research backtests actually run locally, NOT GitHub Actions. All 101 monthly signals, 2018–May 2026; 2076 common EU–US exchange days through 1 July 2026. EUR net 10bp one-way actual trades, genuine next open, Top3/Top5 equal-weight. Research only; none promoted. The reproducible Python script and all per-day/per-trade outputs are delivered in the chat archive `EU155_RESIDUAL_MOMENTUM_PAPER_BENCHMARK_20261028.zip`, including the copied original simulator. Inputs are the four original frozen conversation archives, not included twice.

## Academic hypothesis predeclared
- Blitz, Huij, Martens (2011) *Residual momentum*, Journal of Empirical Finance 18:506–521, DOI 10.1016/j.jempfin.2011.01.003
- Moskowitz, Ooi, Pedersen (2012) *Time series momentum*, Journal of Financial Economics 104:228–250, DOI 10.1016/j.jfineco.2011.11.003
- Daniel, Moskowitz (2016) *Momentum crashes*, Journal of Financial Economics 122:221–247, DOI 10.1016/j.jfineco.2015.12.002
- Harvey, Liu, Zhu (2016) *... and the Cross-Section of Expected Returns*, Review of Financial Studies 29:5–68, DOI 10.1093/rfs/hhv059
- Bailey et al. (2017) *Probability of backtest overfitting*, Journal of Computational Finance, DOI 10.21314/JCF.2016.322

**ETF adaptation** (not the original multi-factor equities paper): at each signal t estimate rolling 252 daily log-return covariance beta to EXSA benchmark EU or SPY USA, clip beta to [-2,3] as fixed numerical safeguard; signal = sum daily ETF log returns from t−252 to t−21 minus beta × matching benchmark cumulative log return. Controls: raw 12–1 momentum, as-of BASE, as-of LIQ50 (≥90% positive-volume past 63 daily sessions and trailing ADV≥EUR50k). EU155 comprises same original 148 ISIN + 7 major Europe index ISIN and six alternate Yahoo quotations for *same* original ISINs. Nothing selected using future returns; its full present-day survivors still involve survivorship bias.

## Test results — 101m, Top5, liquid eligible, EUR, net

| Universe | Momentum 12–1 CAGR | ETF single-index Residual CAGR | Momentum maxDD | Residual maxDD |
|---|---:|---:|---:|---:|
| EU148 | +6.074% | +8.414% | −34.024% | −31.875% |
| EU155 | +6.029% | +9.093% | −33.691% | −29.993% |
| USA149 | +13.566% | +10.163% | −38.437% | −39.881% |

Top3 LIQ50: EU148 +5.489% vs residual +5.982%; EU155 +5.779% vs residual +6.267%; USA +15.730% vs residual +10.112%. These are **NOT the best historical global strategies**; previous EU155 Ridge16+MOM252 Top5 ≈+10.52%. **Residual strategy fails the requirement to preserve USA149 performance; do not deploy globally.**

Paired 6m circular bootstrap 4000 resamples, annualized logreturn difference of residual minus ordinary momentum, EU155 Top5 +2.846 pp **nominal 95% [+0.517,+5.247] pp**, EU148 +2.181 pp [+0.094,+4.349], USA149 −3.040 pp [−10.35,+4.26]. The decades analyzed have already been extensively mined; intervals are nominal and do NOT establish independently verified prospective alpha or survive multiple-testing correction.

Subperiod EU155 residual Top5 ~5.38% CAGR 2018–21 and ~12.41% in 2022–26; momentum 12–1 ~1.12% and ~10.48%. USA residual ~1.82% / ~18.34%; basic momentum ~0.75% / ~26.55%. Seven newly added EU ISIN account for only **25 of 505 Top5 residual positions** in EU155 LIQ50; not an ex-post winning-asset selection explanation. **2 zero-volume-at-quote trades** remain EU155 residual Top5, spread/executable liquidity not independently verified.

## Operational decision

Result is a European-only useful research diagnostic, not a market-wide return predictor or 30% outcome. Keep US149 V2 and B0 unchanged. Do not replace the stronger EU155 historical ensemble with this method. Future work should test residual momentum as one explicit signal *inside* predefined European index categories with nested vintage selection, a verified independent corporate-action/quote dataset and subsequent unseen forward paper test; evaluate independently of the history already exposed. NO code production updates.

## Reproduction inputs already provided

- `eu148_final_corrected_ohlcv.zip`;
- `EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip`;
- `CANONICAL_ORIGINAL_USA149_RAW_20261027.zip`;
- `paired_us149_eu148_controls.zip`.

Code and full scorecard/holdings/101 monthly returns/24 daily NAV series are included in the ZIP delivered in chat. Written report `REPORT_RESIDUAL_MOMENTUM_IT.md` provides details.