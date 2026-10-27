# ETF EU155 / EU148 / US149 — test scientificamente motivato (27 ottobre 2026)

**Stato: 84 backtest verificati localmente, 101 segnali 2018–2026, ricerca storica altamente esplorativa; NON adottare in produzione.** Archivio completo dati, codice originale di esecuzione, sorgenti e risultati nella consegna ChatGPT `ETF_EU155_RICERCA_SCIENTIFICA_RESIDUAL_MOMENTUM_20261027.zip`.

## Letteratura e ipotesi dichiarata
Il filone più promettente è il **residual momentum**: Blitz, Huij & Martens, *Residual Momentum*, Journal of Empirical Finance 2011, [doi:10.1016/j.jempfin.2011.01.003](https://doi.org/10.1016/j.jempfin.2011.01.003). Fondamenti e rischi: Jegadeesh & Titman 1993; Moskowitz/Ooi/Pedersen 2012; Novy-Marx 2012; Barroso/Santa-Clara 2015; Daniel/Moskowitz 2016; Moreira/Muir 2017; Gu/Kelly/Xiu 2020; DeMiguel/Garlappi/Uppal 2009; Harvey/Liu/Zhu 2016; Bailey et al. 2015; Khomyn/Putnins/Zoican 2024. Riferimenti DOI e interpretazioni nel documento `LITERATURE_REVIEW_EU155_US149.md` incluso nell'archivio chat.

**Formula causal as-of:** a ogni segnale di fine mese `beta_i=Cov(logret_i,logret_EXSA)/Var(logret_EXSA)` sulle ultime 126 sedute realmente osservate; score a 12-1 mesi = `ln(Close_i[-21]/Close_i[-252]) - beta_i * ln(Close_EXSA[-21]/Close_EXSA[-252])`; US149 usa SPY come fattore. Variante corretta per rischio divide lo score per la volatilità residua annualizzata, con minimo 3%. I valori di input sono log-rendimenti numerici; nessun rendimento futuro, nessun fitting di ML. Ranking Top3 / Top5 e ribilanciamento next-Open, 10bp per lato, EUR. Pesi 1/N.

**Universi immutable:** EU148 originale con tutti gli ISIN già selezionati, EU155 con i sei cambi EUR di Yahoo venue stesso ISIN e 7 nuovi ETF nazionali, US149 originale. Importante: il gruppo EU155 è costruito/bonificato nel 2026 e non è una master-list completa *point-in-time* dei prodotti 2018; survivorship/venue selection bias da verificare con fonti exchange indipendenti. 101 segnali, 2076 giornate dal 2018-02-01 al 2026-07-01, calendario B0 congelato per USA ed EU, FX USD/EUR dall'originale B0, filtro passato 252 giorni, con/senza as-of 63d >90% vol positivo e ADV mediano >EUR50k. Un "0 volume" del feed Yahoo non certifica assenza di possibilità di scambio.

## Risultati, Top5 con medesimo storico filtro LIQ50

| Modello | EU148 CAGR | EU155 CAGR | USA149 CAGR |
|---|---:|---:|---:|
| Momentum252 | +8.22% | +8.64% | **+21.23%** |
| Momentum 12-1 | +6.07% | +6.03% | +13.57% |
| Residual 12-1 | +7.37% | +7.68% | +11.74% |
| Residual 6-1 | +2.61% | +2.11% | +15.04% |
| Residual 12-1 / resid vol | **+8.48%** | **+9.20%** | **+2.23%** |
| Residual 6-1/12-1 fixed percentile average | +4.63% | +5.30% | +13.59% |
| Total/residual momentum fixed percentile mean | +7.80% | +7.01% | +10.38% |

EU155 risk-adjusted residual: **MaxDD -19.27%**, annualized vol 15.01%, Sharpe rf0 0.600, vs same-universe momentum252 **MaxDD -35.57%, vol 20.12%, Sharpe 0.421**; EXSA buy & hold **+8.84% CAGR, -35.22% maxDD**. Riduzione del rischio deriva anche dalla beta di mercato ridotta (~0.646), e 12.3% slot sovereign EUR. EU155 residual risk-adjusted 2018–21 +7.79%, 2022–26 +10.45%, contro momentum252 +0.96%/+15.80%; questo è un vantaggio stabilità **descrittivo**, non alpha stabilito.

Paired six-month block bootstrap 5000 draws on 101 monthly returns, EU155 risk-adjusted vs 12-1 price momentum log-alpha annual +2.95pp, IC95 [-4.19,+9.85]pp; vs EXSA factor-regressed HAC alpha +3.33% ann, 95% CI [-1.91,+8.56], index beta 0.646. IC comprende zero. Multiplicity 84 candidates, repeated previous 2018–26 exploration, no independent test. **Near-30 CAGR NOT achieved.**

## Decision
1. **Keep USA original V2 full-stack unchanged**. The EU-oriented risk-scaled residual strategy would drastically underperform the US momentum+fullstack; never impose globally.
2. **EU-only challenger**, not validated alpha or production: better European drawdown in the explored sample, essentially unchanged CAGR.
3. Before any promotion: PIT venue confirmation, independent exchange NAV / bid-ask validation, delisted ISIN, dividend/split integrity, then prospective paper-trading validation.
4. The full original V2 500 USA basket CAGR 22% (individual mean) / 24.77% (aggregate) is a different strategy and **not** this free Top5 comparison.

**Full source of truth:** ChatGPT zip includes 84 results, 84 daily NAV series, 8484 monthly choices, source data EU148/EU155/USA149 and original parity reference, 5000x paired bootstrap result, HAC factor-adjusted alpha, and executable scripts `literature_residual_momentum.py`, `finish_lit.py`, `alpha_analysis.py`.
