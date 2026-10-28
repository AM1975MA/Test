# 28 ottobre 2026 — primo test scientificamente motivato: momentum residuo su EU155 e USA149

**Stato eseguito e concluso localmente: 112 configurazioni (84 EU, 28 USA), ricerca storica esplorativa, NON nuova validazione indipendente, non promossa in produzione.**

### Risultato Top5 con filtro storico di liquidità 50k (NAV in EUR, 10bp/lato, 101 segnali e 2076 barre Open)
| Score | EU148 original | EU155 con 7 nuovi | USA149 |
|---|---:|---:|---:|
| Momentum252 | +8.22% | +8.80% | **+21.23%** |
| Ridge + momentum252, ranghi 50/50 | +12.30% | +10.47% | +14.67% |
| **Ridge + momentum residuo, ranghi 50/50** | **+12.91%** | **+13.31%** | +18.19% |
| Momentum residuo puro | +7.23% | +7.04% | +13.57% |

EU155 Ridge+Residual MaxDD -31.69%; EU155 momentum252 MaxDD -35.35%. USA149 Ridge+Residual non mantiene il CAGR di momentum252; per ora **non sostituire strategia USA**.

**Formula effettivamente testata, non una copia esatta del paper multifattoriale:** `mom252skip21_ETF - beta126_ETF_vs_BENCHMARK * mom252skip21_BENCHMARK`. Benchmark EXSA DE0002635307 per EU, SPY per USA; regressione beta con dati passati e target Ridge frozen annuale. Portafoglio Top3/Top5 equal capital, liquidity eligibility as-of BASE/LIQ50, historical sourced full-isins with 6 same-ISIN Yahoo vendor quote repairs and 7 European index ETFs; overlapping IBEX 35 omitted within same TopK.

### Predittività / bootstrap
- EU155 LIQ50 monthly mean Spearman IC: Ridge +0.0491; residual +0.0393; Rank50/50 Ridge+Residual **+0.0883**.
- EU155 Top5 paired monthly NAV log-alpha annualized Ridge+residual vs momentum252 **+4.06 percentage points**, 6-month circular block-bootstrap 9000 samples CI95 **[-4.46, +12.31]pp**. **Not significant.**
- vs Ridge + Momentum252, **+2.53 pp log annual** IC95 **[-0.31,+5.55]pp**. Also includes zero.
- EU155 Ridge+Residual descriptive CAGR **2018–21 +5.13%**, **2022–26 +20.90%**. Regime dependence significant caveat.
- At least 2 trades at vendor zero-volume, execution quality not fully certified.
- Historical time interval repeatedly explored with 112 checks and universe 2026 surviving ISINs; nominal CI too optimistic for multiplicity; don't assert newly discovered alpha or 30% CAGR.
- Original momentum252 EU frozen parity exact; EU155 and repaired baseline same-vintage replay difference <=0.011 pp CAGR due vendor CSV precision/ties. USA149 baseline momentum252 +21.23% matches original B0.
- No 500-basket fullstack equivalence in this experiment.

### Scientific basis verified
- Blitz, Huij & Martens (2011) *Residual Momentum*, Journal of Empirical Finance DOI 10.1016/j.jempfin.2011.01.003; **paper on stocks; here simple 1-factor ETF proxy**.
- Moskowitz, Ooi & Pedersen (2012) *Time Series Momentum*, JFE DOI 10.1016/j.jfineco.2011.11.003.
- Daniel & Moskowitz (2016) *Momentum Crashes*, JFE DOI 10.1016/j.jfineco.2015.12.002.
- Harvey, Liu & Zhu (2016) *...and the Cross-Section of Expected Returns*, RFS DOI 10.1093/rfs/hhv059.

All results, 112 exact scorecards, 101 monthly IC per EU universe, 6m bootstraps, 101 months of selections, 2076 daily NAV per policy, and Python executable research scripts saved in local conversation archive `ETF_RESIDUAL_MOMENTUM_USA149_EU155_PRIMO_TEST_20261028.zip`. Supporting frozen RAW archives already supplied separately in the conversation. **Do not modify production or frozen V2.**
