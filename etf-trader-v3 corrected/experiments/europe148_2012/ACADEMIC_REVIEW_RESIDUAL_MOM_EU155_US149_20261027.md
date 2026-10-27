# Revisione scientifica applicata: momentum residuo, EU148/EU155 vs US149 (2026-10-27)

**Esito: nessuna nuova strategia promossa; ipotesi residual momentum NON confermata.** La ricerca è stata eseguita su fonti originali congelate: [precedente EU155 corretto](EU155_YAHOO_VENUE_REPAIR_48_SCENARIOS_20261027.md), dataset EU148 legale 148 ISIN completo e USA149 storico. Questi sono portafogli **liberi Top3/Top5**, NON i 500 panieri V2. Ogni backtest è in EUR, date comuni 101 segnali mensili 2018-01..2026-05 con valorizzazione next Open Feb2018..Jul2026 (2076 giorni), commissioni 10bps per lato, TopK equal weights, **same B0 original Numba execution code**. Liquidità as-of 63 sedute con ≥90% di volume riportato positivo e ADV mediano ≥50k EUR; nessuna scelta ex post di singoli ISIN redditizi. USA conserva stesso FX proxy B0, EU155 conserva 6 riquotazioni EUR same-ISIN e 7 ETF indici nazionali.

## Ipotesi principale definita prima dei risultati
Da Blitz–Huij–Martens (*Residual Momentum*, JEF 2011, doi:10.1016/j.jempfin.2011.01.003) e da Jegadeesh/Titman (1993): sottrarre la parte di momentum spiegata dal movimento del mercato dovrebbe rendere il Top5 più selettivo, specialmente su ETF europei omogenei.

Fattore as-of `L12_1_i=log(P_i,t-21/P_i,t-252)`; beta mercato rolling126 daily returns, shrinkato al 50% verso 1, limitato 0..2.5; `RES_i = L12_1_i - beta_i * L12_1_benchmark` (EU EXSA, USA SPY). TopK per score RES; nessun fit futuro. Varianti dichiarate: 50% correzione mediana gruppo, vol scaling, piccola penalità trend negativa; controlli momentum252, momentum12-1, Ridge frozen, Ridge+mom.

## Risultati TOP5 CAGR netto EUR

| Metodo | EU148 | EU155 | USA149 |
|---|---:|---:|---:|
| **Momentum 252**, benchmark strategia semplice | **8.22%** | **8.80%** | **21.23%** |
| Momentum 12–1 | 6.07% | 6.28% | 13.57% |
| **Residual market-beta momentum** | **7.61%** | **6.99%** | **10.65%** |
| Residual relative group | 6.76% | 6.76% | 12.20% |
| Residual / historical risk | 5.06% | 4.81% | 8.49% |
| Residual + soft trend penalty | 7.76% | 6.92% | 11.27% |
| Previous Ridge model | 4.96% | 5.10% | 19.64% |
| Ridge+momentum50/50 | 11.97% | 10.76% | 14.13% |

Passivo benchmark stesso periodo dai controlli B0: EXSA Europa +8.8434% e SPY USA +15.1632% CAGR EUR. EU155 Residual **sottoperforma sia MOM252 che buy-and-hold EXSA**. USA Residual perde ~10.6pp CAGR rispetto MOM252. Il +5.10% Ridge EU155 nel nuovo simulatore non coincide esattamente col +4.79% riportato nel precedente replay EU155: scelte identiche ma piccole differenze cumulative NAV fra motori, da auditare ulteriormente; per valutare il confronto si usa il **medesimo motore per tutti gli scenari in questa campagna**, con MOM252 EU148/USA149 riconciliato a B0 ~0.02pp.

**Statistical check:** paired 6-month circular time block bootstrap 8000 repliche su 100 month-to-month NAV log changes, 72 paired comparisons. Residual Top5 vs MOM252 annualized LOG differential:
- EU148 −0.54pp, nominal 95% CI [−4.14,+2.99]pp
- EU155 −1.67pp, nominal 95% CI [−5.59,+2.38]pp
- US149 −7.41pp, nominal 95% CI [−14.81,−0.11]pp (nominal evidence that new residual approach worsens US)

**Additional exploratory sensitivity AFTER primary result:** Novy-Marx (2012) suggests momentum from intermediate horizon. Another 24 replay scenarios (3 universes × Top3/Top5 × four controls: classic MOM252, 12–1, 12–7, 12–6); 12–7 EU155 Top5 +7.71%, US149 +5.03%; 12–6 EU155 +8.87%, US149 +12.50%. Versus MOM252 EU155 12–6 +0.025pp annual log diff nominal 95% CI [−5.71,+5.75]pp, NO result. 12–7 US is significantly worse on nominal block resampling.

## Primary research bibliography, reviewed source abstracts and accessible passages, not all published papers
- Jegadeesh & Titman (1993), DOI:10.1111/j.1540-6261.1993.tb04702.x
- Moskowitz, Ooi & Pedersen (2012), DOI:10.1016/j.jfineco.2011.11.003
- Blitz, Huij & Martens (2011), DOI:10.1016/j.jempfin.2011.01.003
- Novy-Marx (2012), DOI:10.1016/j.jfineco.2011.05.003
- Asness, Moskowitz & Pedersen (2013), DOI:10.1111/jofi.12021
- Daniel & Moskowitz (2016), DOI:10.1016/j.jfineco.2015.12.002
- Barroso & Santa-Clara (2015), DOI:10.1016/j.jfineco.2014.11.010
- Gu, Kelly & Xiu (2020), DOI:10.1093/rfs/hhaa009
- Kelly, Pruitt & Su (2019), DOI:10.1016/j.jfineco.2019.05.001
- DeMiguel, Garlappi & Uppal (2009), DOI:10.1093/rfs/hhm075
- Harvey, Liu & Zhu (2016), DOI:10.1093/rfs/hhv059
- Bailey, Borwein, Lopez de Prado & Zhu (2017), DOI:10.21314/JCF.2016.322
- Sullivan, Timmermann & White (1999), DOI:10.1111/0022-1082.00163
- McLean & Pontiff (2016), DOI:10.1111/jofi.12365

## Decision
1. **Reject** replacing original V2/V3 or US momentum with residual, category-neutral, risk scaled, or intermediate momentum: empirically inferior and loses key market exposures. Full V2 original 500 panieri not changed.
2. For EU155, price-only models from the **same OHLCV** are probably information constrained; to falsify that hypothesis, bring actual incremental **point-in-time external information**: ETF constituents/changes, country EPS revision/dividend yields, factor premia, market interest/credit spreads, forex, executable EOD bid/ask and historically delisted ETF master.
3. In the next genuinely new forward cohort, compare macro/underlying factor prediction then within category residual forecast, always vs EU benchmark EXSA and US SPY; do not optimize after inspecting 2018–26 and call it independent. No evidence EU CAGR close to 30%.
4. Retain frozen B0 and explicit non-promotion status.

**All reproducible Python sources, signals, picks, daily NAV, 72 + 24 scenarios, 84 paired block bootstrap comparisons and source fingerprints** are in conversation artifact `EU155_RESEARCH_SCIENTIFIC_MOMENTUM_20261027.zip` (input raw zips referenced and hashed). No production modification.
