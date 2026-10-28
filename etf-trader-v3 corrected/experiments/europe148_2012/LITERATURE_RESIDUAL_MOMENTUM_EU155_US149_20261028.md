# Letteratura scientifica e 72 backtest: residual momentum EU155 e controllo USA149
Data: 2026-10-28. **Ricerca esplorativa; modello produttivo invariato.**

## Fonte e metodo
- Universi: 148 ISIN europei originali, 155 ISIN Yahoo riparati (148 preservati + 6 same-ISIN venue alternates + 7 principali indici europei), e i 149 ETF USA originali.
- 101 segnali mensili 2018-01–2026-05, 2.076 NAV giornalieri EUR dal 2018-02-01 al 2026-07-01; prezzi reali Open della seduta successiva, fee 10bp one-way, Top3/Top5, filtro as-of liquido/nessuno.
- Nuovo segnale: beta rolling 252 rispetto al benchmark EXSA (EU) o SPY (US) stimato interamente con dati precedenti il segnale; residual log momentum dei 231 giorni precedenti **escludendo i 21 più recenti**; alternativa divisa per volatilità dei residui; medie di ranghi fissate con momentum 252 o LM Ridge già frozen. Sei modelli × due gate di liquidità × due TopN × tre universi = **72 scenari**.
- Fonte input congelata verificata in `EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip` e `EU148_US149_RESEARCH_RESTART_96_TESTS_20261027.zip`. Nessuno dei 10 UCITS globali scelti ex-post aggiunto. USA149 lasciato invariato. Una modifica al source dei prezzi dell'EU155 del 2026 è **anch'essa retrospettiva**.
- Simulator original parity `sim_all` estratto dal sorgente del precedente test a 96 bracci; controllo EU148 MOM252 perfettamente identico ai 4 casi del precedente studio, EU155 baseline entro 0,011 punti CAGR; USA MOM252 +21,227% vs B0 +21,23%; nessun ordine di uscita senza quote.
- Sorgente completo `run_residual_literature.py`, `compare_against_prior.py`, tutti i 72 NAV, selezioni, predizioni as-of, IC, bootstrap, manifest e report inclusi nel pacchetto ZIP `ETF_LITERATURE_RESIDUAL_MOMENTUM_EU155_US149_20261028.zip` della conversazione corrente. SHA256 ZIP `b6b3210bce74fa2feeaefec9b0c795f06017b273d8fa5ebcf67cd4c6c1670c9e`.

## Ricerca scientifica che motivò il test
1. Jegadeesh/Titman 1993, winners-losers, DOI 10.1111/j.1540-6261.1993.tb04702.x;
2. Blitz/Huij/Martens 2011, *Residual Momentum*, DOI 10.1016/j.jempfin.2011.01.003;
3. Moskowitz/Ooi/Pedersen 2012, *Time Series Momentum*, DOI 10.1016/j.jfineco.2011.11.003;
4. Asness/Moskowitz/Pedersen 2013, *Value and Momentum Everywhere*, DOI 10.1111/jofi.12021;
5. Barroso/Santa-Clara 2015, *Momentum Has Its Moments*, DOI 10.1016/j.jfineco.2014.11.010;
6. Daniel/Moskowitz 2016, *Momentum Crashes*, DOI 10.1016/j.jfineco.2015.12.002;
7. Harvey/Liu/Zhu 2016, multiple-testing, DOI 10.1093/rfs/hhv059;
8. Bailey/Borwein/López de Prado/Zhu 2017, PBO, DOI 10.21314/JCF.2016.322.

**Not an exhaustive review of all papers**. Residual momentum on stock return/factors is not mathematically equivalent to ETF momentum versus one regional benchmark; this is a hypothesis-driven adaptation.

## Real net CAGR results, Top5 and eligibility LIQ50

| Strategy | EU148 frozen | EU155 repaired | US149 |
|---|---:|---:|---:|
| MOM252 | 8.216% | **8.800%** | **21.227%** |
| MOM12–1 | 6.074% | 6.285% | 13.566% |
| RESID12–1 | 8.240% | 8.474% | 10.163% |
| RESID/sigma | 7.306% | 7.681% | 9.388% |
| Rank blend residual+momentum | 7.695% | 7.530% | 15.555% |
| **Rank blend residual+frozen Ridge** | **12.506%** | **12.615%** | 16.895% |

EU155 blended residual+Ridge MaxDD −31.122%, versus momentum252 MaxDD −35.349% and pre-existing Ridge+MOM252 MaxDD −33.909%. New +12.615% vs prior Ridge+MOM **+10.520%**; observed +2.095pp CAGR; paired annual log excess +1.86pp, bootstrap 6-month CI95 **[−1.40;+5.03]pp** (contains zero). Versus pure momentum +3.445pp annualized log excess, CI95 **[−6.102;+12.402]pp**. No verified alpha.

Monthly Spearman IC EU155 original Ridge +0.04390 vs residual+Ridge +0.07404; diff +0.03015, 6-month bootstrap nominal CI95 **[−0.00940;+0.07173]** (contains zero). The gain is not statistically verified.

EU155 blend Top5 2018–2021 CAGR +5.89%; 2022–2026 +18.78%: material regime dependency. EU155 LIQ50 selected trades: **3 lines at Yahoo volume=0** (unverified actual execution), old-quote fill errors 0. New 7 ISIN in 2026 hindsight universe and previous testing on 2018–26 preclude describing these results as virgin holdout.

## Decision
- **Do not promote** an EU155 strategy based on this repeatedly inspected history. Advance residual+Ridge as a *challenger* requiring independent future verification and vendor/venue transaction quality.
- **Keep US149 baseline unchanged**. Residual momentum materially reduces USA Top5 CAGR versus 21.23% simple momentum, and must not replace the original V2 fullstack 500 baskets.
- **No 30% CAGR**. Next meaningful study: category-conditional beta/residuals on broad EU underlying equity/bond sectors, using a forward-only 2026+ validation framework; without overfitting on 2018–26. Control coverage and cross-listing corporate actions.
