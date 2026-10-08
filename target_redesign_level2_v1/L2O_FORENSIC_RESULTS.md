# L2-O — Ricostruzione forense della V2, 43% Golden e drawdown 2025

**8 ottobre 2026 | COMPLETATO | Audit indipendente PASS | Nessuna nuova strategia.** Unico repository interessato: `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. **`Etf_trader` non modificato.** [Protocollo congelato prima degli output](L2O_FORENSIC_PROTOCOL.md), commit `f42d239d93ceb3814cc253ba3df0f3749c0585eb`.

## A. La perdita 43,146% → ~31,604% è stata già isolata sul piano della provenienza

Una correzione ai nostri rapporti recenti: l'Annual V2 Golden **43,1459524203%** è **già riprodotta esattamente da un audit di parità archiviato**, `gap_analysis/results/PARITY_43PP.json`. Non è corretto chiamarla genericamente una baseline non riprodotta. La V2 con **la stessa catena produttiva** (hash Git blob gate passato, 3 file normalizzati al newline terminale) su nuovi dati Yahoo del 2 ottobre 2026 dà **31,6039945629%** con parity, differenza **−11,5419578574 punti percentuali**. Entrambi su Original149, 2.366 sessioni 2017-02-01→2026-07-01, costi e metriche Annual V2 equivalenti.

Fonte: [baseline lineage](../gap_analysis/results/BASELINE_LINEAGE_DECISION.md), [matrice code/data](../gap_analysis/results/CROSSED_REPLAY_MATRIX.json), [lineage Golden](../gap_analysis/results/SOURCE_LINEAGE_43PP.json), [identità source code](../gap_analysis/results/SOURCE_IDENTITY_43_VS_31_V1.json).

**Dato acquisito:** la differenza di *raw-data vintage* è fattore confermato a livello di esperimento, e produce anche score Titanium e MA3 differenti. **Non quantificato:** quota dei −11,54 pp imputabile al mutamento delle decisioni rispetto a quella dovuta ai prezzi di esecuzione o agli stati del clustering. L'ambiente di build storico esatto non è stato dimostrato byte-identico. Le cinque matrici Parquet del Golden sono fingerprinted ma non presenti nel pacchetto locale Repeat2; nessuna nuova decomposizione “mix scores × prices” è stata inventata.

Il baseline **matched Repeat2** usato qui è **30,84370492564604% CAGR / −25,6896102667% MaxDD giornaliero / Sharpe 1,08699295**. È una terza acquisizione Yahoo distinta dalla fresh 31,604%: non confondere i tre risultati.

## B. Motore monetario V2 completo, parity riprodotta

Fonte locale frozen `titanium-repeat-2.zip` SHA256 `1fc7348e0e88329b99e2339a0d488ed94ae102b90b3d05e8e79f1ea06fed4e9a`, 149 ETF con adjusted OHLCV, previsioni Titanium/MA3 source-only già mature, calendario. Motore reference invariato dal test L2-N, basato su `vendor/p45/v2_stage19_kernel.py::simulate_arch`: ranker storico, MA3, concentrazione Top1/Top2, DD-first/HighCAGR24, V6, cash BIL/SHV, costi 0,1% per controvalore modellato e stop condizionali.

`l2o_forensic_replay.py` (nel pacchetto allegato alla conversazione) implementa un **secondo motore monetario Python** e produce ledger per ticker e giorno, costi e trade stop. Max differenza sul vettore capitale **0 contro il simulatore Numba**, **1,776e−15 contro L2-N DAILY_CAPITAL**, turnover **0**; 2.366 valutazioni, 2.365 giornate operative, 4.721 righe di contributo per asset e 20 stop eseguiti *in tutto il periodo*. `l2o_independent_audit.py` ricontrolla a parte le identità di capitale: massimo residuo contabile giornaliero **5,676e−15**, contributi dei singoli ETF vs ledger **3,053e−16**, totale drawdown riconciliato **esattamente**.

### Data economica (differenza di un trading-day nei precedenti report)
Lo storico usa `E[k]` segnato con `ds[k]`, ma `E[k]` è capitale valutato al **successivo Open[k+1]**. Le date di reporting del maxDD sono 18 giugno→7 ottobre 2025, ma i corrispondenti valori sono calcolati agli Open del **20 giugno→8 ottobre 2025**. Ciò cambia l'etichetta economica, non CAGR o grandezza del drawdown.

## C. Quanto ha perso il portafoglio, davvero, e su cosa

**Peak/trough contabile:** 2025-06-18→2025-10-07, 76 giorni, capitale da **10,235132× a 7,605767×** = **−2,629366** unità di capitale iniziale, pari al **−25,689610%** del capitale al picco.

| Origine P&L | Capitale iniziale, unità | Contributo additivo al DD rispetto al picco |
|---|---:|---:|
| **UNG, top1/top2** | **−2,035490** | **−19,887 pp** |
| **ARGT, top1/top2** | **−1,020052** | **−9,966 pp** |
| IGV, DBO, EPOL saldo positivo | **+0,456309** | **+4,458 pp** |
| Fee rebalance | **−0,030133** | **−0,294 pp** |
| Fee stop e riempimento stop | **0** | 0 pp |
| **Totale** | **−2,629366** | **−25,690 pp** |

Sono **contributi monetari additivi**, non somme di rendimenti mensili. SPY negli stessi giorni guadagna circa **+12,64%** sui Close rettificati. Non fu dunque una crisi di mercato generalizzata: il portafoglio prese un rischio concentrato su due ETF mentre il mercato era forte.

Scelte rappresentative: giugno IGV/UNG (60/40); luglio UNG/DBO (60/40); agosto **100% UNG**; settembre **100% ARGT**; ottobre EPOL/ARGT. Contributi monetari netti per mese del tratto di drawdown: giugno −0,571710; luglio −0,235861; agosto −0,788289; settembre −0,971134; ottobre −0,062372. **0** giornate di riduzione gross, **0** stop, **0** attivazioni V6 alternative, **0** stress sistemici intraday. Neppure l'overlay L2-N ridusse gross nelle 76 giornate.

## D. Root cause: il gate dello stop dipende da stress di mercato generale

Fonte `vendor/p45/v2_stage19_kernel.py::simulate_arch` e `vendor/etf_trader_v2/src/etf_trader/ma3/ddfirst.py`. Il livello di stop `PC[k,t]*(1−0.055)` usa **Close della seduta precedente**, NON prezzo di carico. Per vendere serve inoltre segnale UH/SA (tecnico su dati precedenti) e `sysm OR ud1>=0.55` (ampiezza di stress degli Open dell'intero mercato/universo) e infine Low/Gap sotto lo stop.

Nel drawdown: **110 leg/giorni effettivamente investiti** su 76 sedute; **66** segnali UH/SA; **8** violazioni del livello prezzo 5,5% dal precedente Close; **6** violazioni con UH/SA simultaneamente; **zero** eventi con gate generale attivo. Max `ud1` (proporzione gap Open peggiori di −1%) **0,449664**, sotto 0,55. Max weakness votes DDfirst **1** (gross reduction richiede >=3), media breadth positiva 63 giorni **90,82%**, media volatilità SPY annualizzata 20 giorni **9,11%**. Peggior Low di un ETF investito vs Close precedente **−11,04%**, peggior gap Open **−8,72%**. **Nessuno stop poteva scattare secondo le regole esistenti**. Il sistema rischia quindi perdite idiosincratiche anche in market uptrends; non è un bug di aritmetica, ma un gap di copertura della policy.

## E. Valutazione interdisciplinare

**Machine learning:** problema osservato = concentrazione delle posizioni, non semplice errore di previsione della volatilità generale. Non togliere gli ETF ad alta volatilità: il vecchio modello cercava anche opportunità positive estreme. Eventualmente distinguere per-trade left-tail hazard vs upside, usando indicatori causali di forma.

**Econofisica:** separare shock di singole commodity/paesi dalla crisi sistemica, e studiare persistente deterioramento, gap di apertura, jump downside e correlazioni fattoriali. La volatilità residuale è solo una parte della descrizione.

**Statistica:** 2025 è stato selezionato ex post quale peggior drawdown. Non trasformare l'audit in una soglia scelta retroattivamente, né trattare Original149 come holdout.

**Risk/execution:** il prossimo progetto deve valutare esplicitamente un **budget di perdita specifica indipendente dal gate di crisi sistemica**, con realizzazione intraday/gap realistica, P&L completo, stop fittizi e fee: le modifiche restano ipotesi, **non è stato eseguito alcun nuovo overlay**. Scartare il modulo L2-N senza modificare i parametri per ottimizzarlo.

## Artefatti

**22 file** nella ZIP consegnata in conversazione `ETF_Trader_L2O_forensic_drawdown.zip`, SHA256 `5f108b6574906ce686d13aa634dc44e29d8cd9cc6a74ed9943e7c2e6d7ac6766`, ZIP test PASS. Contenuti: i tre script `l2o_forensic_replay.py`, `l2o_gate_audit.py`, `l2o_independent_audit.py`, `FULL_DAILY_ASSET_PNL.csv`, `FULL_DAILY_TRADE_LEDGER.csv`, `FULL_STOP_EVENTS.csv`, `FULL_DAILY_CAPITAL.csv`, `DRAWDOWN_RISK_GATE_DAY_ETF.csv`, 5 altre attribuzioni, `INDEPENDENT_AUDIT.json`, `SUMMARY.json`, log, README, manifest.

**Decisione: diagnostica conclusa; stop a tuning su storico 2017–26. `Etf_trader` invariato.**
