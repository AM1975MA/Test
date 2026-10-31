# ETF Trader — studio e falsificazione di un predittore di leadership fattoriale (31 ottobre 2026)

**Risultato: modello supervisionato NON promosso.** Ricerca EU165 (ETF UCITS quotati in Europa, alcuni con sottostanti statunitensi), prima studio di letteratura/architettura e poi test effettivo. Nessuna modifica alla produzione o al ramo main.

## Ipotesi e test implementato

La letteratura sostiene che parte del momentum azionario deriva dalla leadership industriale (Moskowitz & Grinblatt, 1999) e mette in guardia sulle inversioni in regime di stress (Daniel & Moskowitz, 2016). V5 mostra alta esposizione a USA/tech nei forti trend 2023–24. Test: verificare se la previsione di rotazione a livello di fattore sia superiore a momentum/equiponderazione.

- Universo F4 originario: EXSA.DE, SXR8.DE, EXX1.DE, LYQ2.DE. Universo F9: F4 più QDVE.DE, SXRV.DE, XDWT.DE, VVSM.DE, EXV3.DE; **F9 è selezionato retrospettivamente dopo aver osservato il 2023**, NON holdout indipendente.
- 873 righe storico fattore-mese, 102 date con sufficienti dati dal 2018; modelli Ridge (14 feature) e Ridge+Kalman (16 feature, filtro one-sided sulla deriva relativa). Target: rendimento logaritmico futuro meno la media dei fattori disponibili, orizzonti 21/42/63 sedute.
- **72 fit annuali 2021–2026**, training etichette maturate prima del 1 gennaio di ogni anno. Fit 2021 su **33 soli mesi indipendenti** (21 sedute): non confondere le 260 righe ETF×mese dei nove fondi con 260 shock indipendenti.
- Baseline: Mom63/126/252 e portafogli F4/F9 equiponderati. Costi 10bps per lato, prezzi Open reali, ledger self-financing, MA200 uguale al V5; 2021–24 primaria, 2025 separato già minato, no ricerca di parametri per CAGR.

## Prognosi della leadership: mean cross-sectional rank IC 2021–24

| Modelo | F9 21d | F9 42d | F9 63d |
|---|---:|---:|---:|
| MOM252 | +0.021 | −0.063 | ~0.000 |
| MOM126 | +0.084 | +0.029 | +0.017 |
| Ridge | +0.069 | −0.064 | +0.068 |
| Ridge+Kalman | +0.049 | −0.051 | +0.053 |

Nessuno ha vantaggio robusto sui vari orizzonti. Gli intervalli con bootstrap mensile di sei mesi sul vantaggio predittivo hanno lo zero all'interno.

## Rendimento 2021–2024 (simulazione, NON forward investibile)

| Policy | CAGR | MaxDD | Annual gross turnover |
|---|---:|---:|---:|
| F4 equiponderato | 12.72% | -10.64% | 0.73× |
| F4 MOM252 Top2 | 14.73% | -17.22% | 3.29× |
| F4 Ridge multi-orizzonte Top2 | 10.88% | -18.04% | 5.51× |
| F4 Ridge Kalman multi Top2 | 11.37% | -14.72% | 8.73× |
| F9 equiponderato | 16.12% | -17.90% | 0.80× |
| F9 MOM126 Top3 | 15.97% | -22.23% | 6.54× |
| F9 Ridge multi-orizzonte Top3 | 15.68% | -25.50% | 4.94× |
| F9 Ridge Kalman multi Top3 | 15.83% | -26.50% | 7.40× |
| Frozen V5 original | 22.03% | -20.73% | source |
| V3 Full Pair25 half MA200 | 15.67% | -16.51% | source |

Ridge F9 multi meno MOM126 annual log excess **−0.26pp**, six-month block 95% CI **[−8.51,+7.19]pp**. Kalman F9 multi meno Ridge F9 multi **+0.14pp**, CI **[−2.79,+3.10]pp**. NONE establishes improvement.

**Regime:** F9 Ridge multi CAGR +0.90% in 2021–22, +30.68% 2023–24, +13.90% 2025. F9 equiponderato +4.67% / +27.11% / +17.41%. Weak crisis regime performance persists. At **30bps per side** 2021–24 F9 Ridge multi CAGR 14.58% versus F9 equal 15.94%.

## Validation

- **Zero max NAV error on all dates** against five frozen factor baseline policies and frozen V5 original.
- Strict pre-fit outcome maturity; no retrospective Kalman smoother; no execution-day close eligibility test.
- 47 monthly returns main statistic, six-month circular bootstrap; underpowered and selected-history caveats.
- Six calendar months/monthly native V5 score coverage influence allowed rebalance calendar; no fabricated trades.
- Corporate actions, total returns, delistings, spreads, currency and stale marks not independently certified; 2026 survivorship; extensive prior testing on same history.
- Decision: reject promotion; do not tune this factor model on known 2023 rally. Improve **genuinely point-in-time economic sector factor labels, macro indicators and out-of-sample validation** before further model complexity.

## Reproducible standalone source package

Conversation ZIP: `ETF_TRADER_EU165_LEADERSHIP_4_9_FATTORI_20261031.zip`, SHA256 `2c3f15e1c62efca0be6fdd2f37112c8f4d40e5d712ed6a45a6abe8521c331e51`, 33.3 MB, 31 entries, contains the entire original V5 source dataset archive as `ORIGINAL_V5_SOURCE.zip`, four Python scripts, 873-row factor panel, 5118 OOS ETF-horizon forecasts, daily self-financing NAV, original reference 4/9 controls, trade ledger, 72 fit audits, confidence intervals and plots. CRC checked. Full code and vendor datasets are contained in ZIP; this Git branch records a concise immutable audit, not another copy of original data. Main unchanged.
