# ETF Trader V2 ORIGINALE — 149 USA vs 48 Europa, audit del 20 ottobre 2026

## Risposta
Il precedente **31,7581% annuo** è il BASE autentico del sistema completo ETF Trader V2 su **UN universo libero USA149**, calcolato come media dei CAGR ricavati da tre revisioni delle quotazioni storiche dello stesso mercato USA. **Non sono 500 panieri da 24 ETF**. Il 30,9578% è una variante distinta di reranking ECON_TOP5_RERANK. Il successivo +10,48% americano era un nuovo fit/replay del MA3 Hybrid24 in un altro percorso di simulazione e NON è il vero backtest BASE completo del 31,76%.

La verifica dei 3 originali percorsi NAV giornalieri ha ricostruito il 31,7581% sull'intera finestra 2017–2026 (MaxDD −32,2164%). Sulla stessa finestra CIVILE dei nuovi test europei, febbraio 2021–1 luglio 2026, il V2 BASE originale USA149 rende **34,9317% CAGR medio** e **−26,0022% MaxDD medio**, su 1360 sedute comuni USA. Il reranking Top5 americano rende +33,5296% CAGR e −25,3559% di MaxDD nello stesso sottoperiodo.

### Replay del vero stadio finale V2 Stage19 su Europa48
È stato applicato il sorgente originale immutato del simulatore Stage19 della versione V2 USA, SHA256 f4fc206acf8aa7408e8ba819e56d407eeedb0b9bd806955fe292c9d10e598920, anziché il precedente replay V6/Hybrid24 semplificato. I 48 ETF sottostanti sono rigorosamente europei, con ISIN unici; un solo universo libero per Top1 e Top2; nessun paniere 500x24 né restrizione per settore. Stesse 65 date mensili di segnale 2021–2026, prezzi Open degli ETF EU osservati in 1374 sedute europee, commissione 10bps per notional, stop 5,5% e slip intraday originale.

Sono stati ripristinati gli originali macro reference **SPY, HYG, IEF USD** e la parte difensiva originale **BIL/SHV USD**. I prezzi di difesa USA sono calcolati nel NAV EUR con l'ultimo US Close e EURUSD precedente noto prima dell'Open EU; sono asset US effettivamente detenuti SOLO nel layer difensivo e non diventano il 49° e 50° ETF eleggibile per Top1/Top2.

| Esperimento, febbraio 2021–luglio 2026 | CAGR netto | MaxDD |
|---|---:|---:|
| **V2 BASE autentico originale USA149, media 3 raw-vintage** | **+34,9317%** | **−26,0022%** |
| V2 EUR48 con ensemble originale Titanium/MA3 riaddestrato e vero Stage19 full | **−0,1549%** | **−39,9093%** |
| EUR48 **variante distinta**: punteggio BASE dell'ensemble sostituito dal Compact21 125-feature originale, riaddestrato in EUR48 | **+5,9763%** | **−34,7898%** |

Il Compact21 sostitutivo è un diagnostico source-based (XGB pairwise 360round x3seed originali EUR48 maturi) e **non** rappresenta il porting immutato del BASE. Il primo scenario EUR48 è il porting più vicino della pipeline originale del 31,76; non è comunque bit-identico al dataset/modelli USA.

### Limiti
1. L'algoritmo finale Stage19 è immutato, MA il training 48 Europa proviene da 2017–20+ quote con refit annuale 2021–26. Il modello USA originale dispone di storia e quote diverse e comincia OOS 2017. Le 3 vintage USA sono osservazioni correlate, non repliche indipendenti.
2. L'architettura USA richiede 7 cluster dinamici con min8 ETF ciascuno e 1 bucket difensivo min8, **non realizzabile sui 48** (solo 41 non-government e 7 sovereign). Il panel europeo era stato necessariamente adattato a 5 cluster dinamici+1 governativo: non pretendere parità totale di architettura feature.
3. Europa e USA hanno calendario e valuta diversi. Europa48 ha 1374 sedute reali e USA149 ne ha 1360 nel periodo civile comune; la contabilizzazione di BIL/SHV in EUR su last published close FX è approssimata, non una quotazione bid/ask eseguibile. Le 49 riparazioni High/Low nel solo input derivato EU sono auditabili; dati EUR Yahoo rettificati retroattivamente.
4. L'universo Europa selezionato nel 2026 è un survivor roster, non un anagrafico point-in-time del 2017. Il backtest storico USA è stato ripetutamente analizzato/ottimizzato nel corso dello sviluppo. Non dedurre alpha futuro dalla differenza.

**Verdetto:** il risultato storico del V2 originale USA149 (+31,76% su 2017–2026, +34,93% sul sottoperiodo 2021–2026) è genuino come backtest verificato. Il porting più fedele possibile del suo Stage19 originale, con modelli EUR48 annualmente riaddestrati e macro SPY/HYG/IEF originali, resta nettamente negativo nel backtest (~−0,15%). Pertanto il problema di generalizzazione non è risolto e il precedente +10,48% USA è stato impropriamente confrontato come se provenisse dal 31,76% canonico.

## Fonte, archivi e esecuzione
- SUCCESS originale USA149 verifica di tutti e tre gli archivi, Action 39397300396: https://github.com/AM1975MA/Test/actions/runs/39397300396
- SUCCESS port originale EUR48 stadio finale Stage19: Action 39398272973: https://github.com/AM1975MA/Test/actions/runs/39398272973
- Riepilogo originale USA: isin_first2026/canonical_v2_same_period/results/ORIGINAL_149_FULL_SOURCE_2017_2026_AND_2021_2026.json
- Source EUR48 2 prove: isin_first2026/canonical_v2_same_period/results/EUROPE_48_ORIGINAL_FULL_V2_STAGE19.json
- Curve quotidiane EU: results/ORIGINAL_V2_STAGE19_EU48_DAILY_NAV_COSTED.csv; posizioni mensili: results/ORIGINAL_V2_STAGE19_EU48_MONTHLY_LEADERS.csv; audit SHA256; macro original USD EURUSD audit.
- Codice di ricerca: isin_first2026/canonical_v2_same_period/original149.py ed europe48.py, workflow Actions sul branch research/canonical-v2-source-us149-eu48-20261020. Il repo di produzione AM1975MA/Etf_trader è INALTERATO.
