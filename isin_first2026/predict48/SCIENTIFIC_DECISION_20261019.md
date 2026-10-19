# Miglioramento capacità predittiva — 48 ETF europei/ISIN, 19 ottobre 2026

## Decisione breve
È stato individuato un **promettente nuovo segnale multi-expert con aggiornamento causale**: combina ranking ETF Trader MA3, momentum a 21 e 126 sedute, regressione Ridge 36 mesi, usando solo le ricompense di mesi precedenti **già definitivamente maturati**, finestra rolling 12 mesi e floor 10% per ogni esperto. Non altera i 48 ISIN né filtra ex-post un settore. **È ricerca retrospettiva sullo stesso universo noto, NON validazione prospettica:** il periodo di backtest e i suoi problemi 2024–2026 erano già stati osservati nello sviluppo; non autorizzare la produzione.

Si sono eseguiti tre stadi reali su Test:
1. 16 predittori rigidamente preregistrati prima di vedere la selezione, training con label mature Jan2017–Dec2020 e walk-forward 2021–26. Si seleziona l'esperto per il futuro usando solo 2021–23; il migliore è ancora **MA3 originale**, non Ridge né momentum, anche se questi ultimi risultano migliori posthoc nei 29 mesi 2024–26. Per questo non sono stati retroattivamente promossi. [GitHub Action 39330964189](https://github.com/AM1975MA/Test/actions/runs/39330964189) SUCCESS.
2. Esperimento specificato separatamente: 4 esperti online con pesi aggiornati da 12 **mesi maturati** precedenti (MA3, Mom21, Mom126, Ridge36). Implementa score rank per ETF come media ponderata di percentile rank, senza target corrente. Softmax temperature 4, peso minimo 10% per esperto, min6 mesi validi altrimenti 25% ciascuno. Due adattivi e due statici 50:50 come controlli, nessuna scelta da 2024–26. [GitHub Action 39331524207](https://github.com/AM1975MA/Test/actions/runs/39331524207) SUCCESS.
3. Replay invariato del motore ETF Trader originale V2: Top2 all-48 senza quote per categorie; stop 5.5%, 10bps trading fee, DD-first, V6, regime SPY/HYG/IEF **USD ORIGINALI** e governativi difensivi euro IBCA/IBCN. Originale MA3 EU-fitted top1 fonte e USD-regime pari IDENTICAMENTE ai precedenti 65 mesi (parity NAV original EU 1e-11 ed economics US 1e-10), nuovo ADAPT4 applicato modificando SOLO le classifiche e pertanto le posizioni/pesi endogeni; nessuna modifica agli altri layer. [GitHub Action 39332292945](https://github.com/AM1975MA/Test/actions/runs/39332292945) SUCCESS.

## A. Capacità predittiva misurata prima del portafoglio
Metriche all-48: prossimo mese Open/ Open log rendimento, benchmark equiponderato tra i 48 ETF. Una data di segnale = una osservazione statistica indipendente, non 48 righe come 48 test indipendenti. Tutti gli ISIN deduplicati e ogni segnale le feature già disponibili.

| Metodo | Spearman cross-section media 65 mesi | Top5 future excess log medio mese (prima dei costi) | CAGR Top5 con 10bp operazioni ma SENZA stop | MaxDD giornaliero |
|---|---:|---:|---:|---:|
| MA3 originale | +0.048235 | +0.0935% | +8.1956% | -23.4215% |
| 4 Esperti CAUSAL online | **+0.056790** | **+0.6598%** | **+15.3732%** | -24.9017% |
| 2 esperti online (MA3+Mom21) | +0.055020 | +0.31496% | +10.5239% | -28.8881% |
| Blend statico MA3/Mom21 50:50 | +0.049911 | +0.2235% | +9.1650% | -28.5195% |
| Blend statico MA3/Ridge36 50:50 | +0.036766 | +0.3964% | +11.8765% | -27.1636% |

Il beneficio non è una prova di regressione fattoriale migliore in senso universale: il ranking MA3 aveva 2021–23 Spearman +0.0578 ed era il MIGLIORE del torneo preregistrato, mentre Mom21 era -0.0375 e Ridge36 -0.0694; queste ultime due danno Spearman +0.0877 e +0.1157 nel 2024–26. La combinazione si adatta in modo automatico ad un cambiamento di regime, ma il periodo è stato già esplorato. Per il nuovo ADAPT4 nel 2024–26: Spearman +0.11265, Top5 extra medio +0.8717% log per mese, contro MA3 Spearman +0.03639, Top5 extra -0.28165%. Differenza mensile paired Top5 ADAPT4 vs MA3 +1.15339 punti percentuali di log return (bootstrap circular 3 mesi 95% **+0.0817/+2.4332 punti**); differenza Spearman +0.07626, CI [-0.01387,+0.1770] comprende 0. Interpretare CI con cautela per multipli esperimenti e campione già conosciuto.

## B. Effetto sul vero portafoglio ETF Trader V2, stesse 1374 giornate EUR, 65 segnali, costi e source
Sorgente EUR48 originale: metodi MA3 Fit source, online momentum and Ridge 2017+ real maturities, non 500×24 basket; 1 solo paniere 48 ISIN tutti eleggibili. Original USA rischio SPY/HYG/IEF, difensivi euro; BIL/SHV non introdotti come 49°/50° ETF; non cambiato mercato di rischio.

| Controller/score | CAGR netto | MaxDD Open | Sharpe semplice ann. | ES5 log giornaliero |
|---|---:|---:|---:|---:|
| MA3 originario Top2 + **SPY/HYG/IEF USA**, V2 Full | **+0.6460%** | **-37.0934%** | +0.1438 | -3.6277% |
| **ADAPT4 Top2 + SPY/HYG/IEF USA**, V2 Full | **+17.6797%** | **-26.6958%** | **+0.9652** | **-2.7798%** |
| MA3 Top2 + risk EUROPE invece USA, V2 Full | +1.6362% | -37.1934% | ~0.187 | ~-3.66% |
| ADAPT4 Top2 + risk EUROPE invece USA, V2 Full | +18.1905% | -26.8812% | vedi RESULT.json | vedi RESULT.json |
| MA3 Top2 senza controller e senza stop, con 10bp | +3.4827% con risk USA; +3.8795% risk EU source margin | -36.4439% USA; -34.9955% EU | | |
| ADAPT4 Top2 senza controller né stop, con 10bp | +18.5284% | -24.5990% | vedi RESULT.json | vedi RESULT.json |

**+17.0337 punti percentuali CAGR / -10.3977 punti di DD in meno** nel confronto corretto stessa macro US originale. Original V2 risk/macros corrisponde esattamente al precedente backtest, source equity NAV parity verificata; i risultati sono già al netto di friction 10bp per trading notional e 0.1% intraday stop slip secondo codice source. La funzione di concentrazione extra V2 non scatta mai con ADAPT4 in 65 mesi, pertanto Hybrid24 completo e V2 completo sono IDENTICI per nuovo predittore: il miglioramento è l'ALLOCAZIONE scelta dai segnali predittivi, NON una scoperta a favore di V2 come concentratore di rischio.

## C. Verifica per anno civile (NON anno del segnale), NAV netto su giornate reali
2021 parte a Feb e 2026 termina il 1 luglio, quindi sono parziali; anni 2022–2025 completi sui giorni di mercato comuni.

| Anno calendario | MA3 originale / rischio USA V2 | ADAPT4 / rischio USA V2 |
|---|---:|---:|
| 2021 feb–dic | +6.87% | +8.15% |
| 2022 | -13.99% | -14.49% |
| 2023 | +27.43% | +34.23% |
| 2024 | -5.51% | +5.33% |
| **2025** | **-6.58%** | **+42.39%** |
| 2026 gen–1lug | +0.17% | +30.48% |

Una parte considerevole del vantaggio dipende dall'ottimo 2025 e dal 2026 parziale, anni e rendimenti già esaminati nelle precedenti ricerche. Il primo ETF selezionato è iShares STOXX Europe 600 Banks EXV1.DE in **14 dei 65 mesi** per ADAPT4, contro **6/65** con il MA3 originale: le performance di banche e finanziari nel nostro periodo sono una componente rilevante. All'inizio dello studio il modello non ha magia: nel 2022 perde -14.49%, leggermente PEGGIO della baseline -13.99%.

La media mensile paired della crescita logaritmica NAV tra nuova e vecchia strategia sull'intero 65: **+1.3116%/mese**, CI circular block 3 mesi 95% circa [-0.0531%,+2.8335%] (incluso zero). Sul solo 2024–26 il CI paired appare positivo, ma NON è una conferma vergine poiché il segmento era stato visionato in precedenti esperimenti e la nuova famiglia di modello è stata ideata in risposta a esso. Il benchmark passivo MSCI Europe, da confronto precedente con calendario/Open simile ma non perfettamente stesso motore, aveva ~+12.57% prima dei costi; ha DD inferiore al nuovo ADAPT4. Non dare per dimostrato alpha robusto o superiorità corretto per rischio.

## D. Tecnica e note di rigore
- Le 48 classi ISIN sono identificate in anagrafica verificata current Xetra + issuer, ma appartengono a un universo **2026 survivorship e retro price QA**, non al 2017 investible universe PIT.
- Tutte le previsioni hanno a disposizione solo dati fino al signal Close. L'entrata simulata è il successivo Open. I pesi MA3, Momentum21, Momentum126, Ridge36 sono aggiornati solo dopo maturity reale (exit date strettamente minore della data del segnale), da **max 12 mesi maturi**, con softmax e peso floor fissati anticipatamente. Nessun ricalcolo Ridge sulle 2024 labels fatto prima della maturity.
- Yahoo vendor Adjusted Open/Close storico non coincide necessariamente con quotazioni davvero eseguibili. In esecuzione intraday V6 l'input locale originale ha 49 barre High/Low con envelope corretto esclusivamente in derivati, conservando originale; non sappiamo se questi stop sono realistici. 10bps fee/leg ma non tutte le spread reali e imposte.
- L'originale USA149 aveva 7 cluster dinamici+bond; EUR48 5+governativo per necessità di coorte, dunque non è bit-identica la pipeline USA. Gli originali USA SPY/HYG/IEF sono riferimenti per CONTROLLER, ma l'originale componente predittiva MA3 in ADAPT4 è il precedente fit europeo EUR48, non il re-fit solo-USA SPY che nei test comparativi aveva sotto-performato. Distinguere queste dimensioni.
- Per CV corretta confrontare gli effetti sul prossimo periodo **non ancora aperto** con nuove quote genuine e point-in-time member set; si può usare market data dopo luglio 2026 solo se source e exact instrument identity disponibili in completa copertura, e poi altra finestra temporale 2027–2028. Non promuovere parametri in produzione sulla base del 2021–26 già scandagliato.
- Il miglioramento appare promettente e vale un'analisi prospettica nuova. Non rettificare scelte viste nel 2025 per aumentare percentuali nel backtest retroattivo.

## Tracciabilità e sorgenti
- [Workflow 16 predittori](https://github.com/AM1975MA/Test/actions/runs/39330964189), risultati in isin_first2026/predict48/results.
- [Workflow causal online experts](https://github.com/AM1975MA/Test/actions/runs/39331524207), risultati in isin_first2026/predict48/online_results.
- [Workflow Replay V2 risk original SPY/HYG/IEF](https://github.com/AM1975MA/Test/actions/runs/39332292945), risultati in isin_first2026/predict48/v2_integration_results.
- In ognuno RESULT.json e SHA256_MANIFEST.txt, monthly ranking per-ETF, ISIN selection lists, dynamic expert weights, historical annual-mature train audit, daily V2 equity curves, schedule, source source snapshots.
- Sorgenti: isin_first2026/predict48/tournament.py, online_experts.py, replay_v2.py e tre PREREGISTERED*.md, tutto research/branch su AM1975MA/Test e nessuna modifica del repo originale AM1975MA/Etf_trader.

### Decisione
**SHARE WITH CAVEATS — research PASS / production NO-GO.** 48-ETF predictor structure migliorata storicamente e aiuta vistosamente il controller V2; ma evidenza oltre venti esperimenti e periodo già esaminato non separabile dalla scoperta, CI paired pieno 65 include zero, shock 2025 estremamente rilevante, quote / PIT incompleti. Prossimo passo robustezza a static equal4, rolling regimes, dati postlug2026 reali PIT e prova strettamente successiva mai osservata, senza ricercare iperparametri che aumentano il backtest.
