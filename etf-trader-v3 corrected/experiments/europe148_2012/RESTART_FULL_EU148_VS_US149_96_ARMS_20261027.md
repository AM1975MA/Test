# Ricerca da zero su EU148 selezionati e USA149 originali — 2026-10-27

**Protocollo di confronto bloccato:** la ricerca usa **tutti i 148 ETF ISIN completi già verificati e selezionati**, esattamente dal file \`eu148_final_corrected_ohlcv.zip\`. L'altro gruppo è il **USA149 storico originale** (\`v2-deep-leaf-frozen-raw\`). In questa campagna **NO EU10/Xetra shortlist**, NO 158, NO filtro retrospettivo sugli ETF vincenti, NO panieri costruiti ex post. **NON è il full-stack V2 da 500 panieri.**

101 segnali mensili identici 2018-01..2026-05, calendario operativo **INTERSEZIONE** degli exchange US e EU, 2076 Open economici 2018-02-01..2026-07-01, simulazione EUR, pesi uguali Top3/Top5 e 10 bp per lato. Oltre alle regole momentum, LM_RIDGE e LGBM usano **18 forecast annuali frozen e maturati cronologicamente, 125F**, non addestrati sugli esiti del periodo che prevedono. Nei prezzi US conversione FX implicita dal benchmark originale SPY/EUR: riproduzione USA entro 0.015 punti CAGR, non parità byte-esatta. Primo test 20 policies×2 top×2 mercati=80 backtest; secondo test 4 architetture meta cronologiche×2 top×2 mercati=16 backtest aggiuntivi.

## Risultati nettamente verificati Top5 EUR, no selezione degli scenari

| Variante Top5 | EU148 CAGR | EU148 MaxDD | USA149 CAGR |
|---|---:|---:|---:|
| LM_RIDGE originale | +4.34% | -30.02% | +19.64% |
| LightGBM originale | +6.77% | -33.35% | +18.05% |
| Momentum252 | +6.37% | -41.35% | **+21.23%** |
| Media percentile LM + MOM252 50/50 | +9.28% | -32.23% | +14.13% |
| Media percentile LGBM + MOM252 50/50 | +8.00% | -28.79% | +18.75% |
| Media LM/LGBM/MOM252 solo ETF azionari | +9.03% | -28.92% | +11.47% |
| Media LM/LGBM/MOM252 e as-of ADV250k | +5.74% | -31.32% | +14.87% |
| MOM252 + as-of ADV250k | +8.20% | -32.29% | +20.94% |

Top3 **EU Ridge+Momentum +11.74%**, DD -31.16% ma con molte operazioni su volume vendor zero; **US LGBM+Momentum +24.12%**, DD -32.97%. Sono risultati **esplorativi sul periodo già studiato**: differenze di CAGR nominali non sono alpha o miglioramenti validati. Bootstrap accoppiato a blocchi di 6 mesi di nuove combinazioni vs LGBM europeo: intervalli del miglioramento economico includono zero. Attenzione: imporre la medesima strategia combinata nei due mercati **può danneggiare USA**; non promuovere una nuova configurazione universale.

**Correzione essenziale**: nel primo replay i momentum sono stati calcolati su ciascun calendario venue, spostando artificialmente i TopK. Versione finale riprova **su calendario comune EU/US**, riconciliando esattamente il NAV LM/LGBM EU con B0 a ~2.22e−16 e il MOM252 EU +6.3718% identico alla baseline B0. US differenza FX ~0.014pp CAGR. I risultati del replay precedente a questa correzione non sono validi.

## Dati e opportunità: struttura del problema

I 148 ISIN sono **completi come insieme**, ma il numero medio storicamente idoneo al mese 2018–26 con 252 giorni dati utili è EU **131.73/148**, USA **149/149**. Aggiungendo volume riportato positivo almeno nel 90% delle ultime 63 sessioni e ADV mediano storicamente ≥250k valuta di mercato, EU **55.78 ETF** contro US **145.95 ETF**. Questi sono controlli vendor: volume-zero NON certifica assenza di market maker o impossibilità di esecuzione, che richiede un feed exchange/venue indipendente. Le performance EU senza tali filtri contengono alcune operazioni non certificabili (es. Top3 LM+MOM). Dato completo NON significa dati operativi certificati.

Su 65 mesi 2021–26, stessa valutazione locale EURO, dispersione media della sezione ETF **EU 2.817%** contro **USA 4.714%**. Gap **1.897pp mensili**, nominal 95% paired 6month block CI **[1.632;2.194]pp**. Il rendimento futuro medio della Top5 scelta da un oracolo (usa i rendimenti futuri: **SOLO POTENZIALE TEORICO**, non tradabile) EU +7.24% mese contro USA +14.25% mese. Universe EU prevalenza sottostante europeo, USA più ampio global/US/EM/commodity: non è una prova di maggiore inefficienza del mercato USA né una giustificazione per inventare nuovi titoli EU.

## Nuovi apprendimenti degli errori dei forecast originali

Quattro meta-stage fit annuali 2021..26 con sola serie storica di previsioni OOS 2018+ e rendimento futuro mensile già maturato a Jan1 dell'anno fit (etichetta future next-Open/next-Open vs median cross-sectional): Ridge, LightGBM regression, LambdaRank, soft tail classifier. Fonte delle feature: LM/LGBM storici, rendimenti percentuali 21/63/126/252, vol, drawdown, turnover storico e breadth. **Nessuno migliora EU148**. Top5 EU: META_RIDGE −1.09%, META_LGBM −0.11%, META_RANK +2.04%, TAIL_SOFT +4.67%. Top5 US: +19.51, +18.99, +10.22, +14.88%, rispettivamente. Nessuna prova di alpha corretta per mining dello storico.

## Decisione

1. **Mantenere congelati V2 USA149 e B0**; non sostituire con ensemble perché sembra migliore in alcune sottoparti.
2. **Non promuovere una nuova versione EU**, perché nell'universo selezionato originale, coi limiti dei dati, non emerge un salto netto statisticamente difendibile.
3. Prima di rifare ML complessi: verificare exchange/issuer EOD, corporate actions, prezzo eseguibile e spread di tutte le 148 serie, imparando a prevedere *rendimento netto/rischio relativo dentro i cluster EU* con validazione nested, mantenendo originale 148. L'obiettivo "30%" **non è stato conseguito**.
4. Non confondere **500 panieri USA V2 22% CAGR medio per paniere** con i Top3/Top5 liberi EU e US qui testati.

**Dettagli riproducibili:** nella consegna chat \`EU148_US149_RESEARCH_RESTART_96_TESTS_20261027.zip\`, che contiene tutte le 96 righe di scorecard, 80×2076 NAV, vettori dei fattori per 101 mesi, tutte le nuove OOS predictions, i 18 audit annuali, bootstrap temporale, report completo e sorgenti Python + dataset congelati. Nessuna modifica al codice di produzione. Tutti i risultati negativi sono conservati.