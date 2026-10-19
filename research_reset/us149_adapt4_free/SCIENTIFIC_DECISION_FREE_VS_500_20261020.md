# ETF Trader V2: verifica 149 ETF liberi contro 500 panieri — 20 ottobre 2026

## Risultato fondamentale

Il **+30,557% annuo storico V2** è una **media di 500 panieri da 24 ETF** nel **2023–2026**. Il **+24,897%** è la stessa metrica sui **2017–2026**. Nessuno dei due misura una strategia unica libera su tutti i 149 ETF.

Il +10,479% è invece una singola strategia MA3/V2 con tutti i 149 ETF eleggibili, con training nuovo e periodo 2021–luglio 2026. Il +29,175% dello stesso esperimento è il NUOVO ranker ADAPT4, non il vecchio MA3.

## Controllo causale riuscito con previsioni, date e motore identici

GitHub Action 39339600413: SUCCESS. Sono stati rigenerati 149/149 prezzi OHLC Yahoo originali dall'archivio conservato nel run 36551650325, rifatti i 6 fit annuali originali Titanium+Hybrid24 senza storico di previsioni; 65 segnali, 1.360 sedute USA da febbraio2021 al primo luglio2026, SPY/HYG/IEF e BIL/SHV originali, 10bp turnover, 5,5% stop, stessi punteggi per due diverse membership. Riprodotti esattamente i valori del run precedente 39338133099 entro 1e-10 di CAGR e DD per le due strategie free149.

| Metodo e V2 | UN solo paniere libero 149 ETF | MEDIA 500 panieri canonici 24 ETF |
|---|---:|---:|
| MA3 originale, V2 | **10,4794%** | **14,2279%** |
| MA3 originale, Hybrid24 (senza regola V2 extra) | 10,5062% | 14,4489% |
| ADAPT4, V2 | **29,1748%** | **21,1324%** |
| ADAPT4, Hybrid24 (senza regola V2 extra) | 29,1748% | 20,8371% |

La membership dei 500 migliora il vecchio MA3 di **+3,7486 punti di CAGR** nello stesso periodo. Per ADAPT4 invece la piena scelta fra i 149 migliora di **+8,0424 punti CAGR** rispetto alla media 500. Le 500 prove condividono molti ETF e non sono indipendenti; la loro CAGR media non equivale a un unico portfolio aggregato.

Distribuzione dei 500 MA3-V2: CAGR mediano 14,05%, 10° percentile -7,04%, 90° percentile 35,61%, 80,4% positivi. MaxDD medio -44,81% contro -47,51% del MA3 libero; il 500 originale 2017–26 aveva MaxDD medio -34,27% e una finestra differente.

## Motivo della forte differenza: top2 e scala del margine

Nel libero149 il MA3 sceglie Top1 molto spesso temi ristretti: KWEB 9/65 mesi, GDXJ 6/65, SOXX 5/65, GDX 5/65. I 500 basket includono soltanto quattro ETF per macro-categoria e costringono il sistema a variare la scelta. Il vecchio libero subisce -26,44% nel 2021 e poi recupera. Non imputare questa perdita al solo layer di rischio V2: il vecchio Hybrid24 libero vale +10,506% e il V2 libero +10,479%.

La differenza di numero dei candidati altera anche il margine top1-top2 della regola di concentrazione 3%:
- MA3 libero 149: gap medio 0,01707, mediano 0,01200, >=0,03 nel 20,0% dei 65 segnali, intervento V2 reale 1 mese /18 sedute.
- MA3 500 x24: gap medio 0,05086, mediano 0,04009, >=0,03 nel 59,63% di 32.500 basket-month, interventi V2 11 mesi e 22.346 basket-days complessivi.
- ADAPT4 libero149: score finale espresso in percentile rank, gap top1-top2 **matematicamente fisso a 1/149 =0,0067114**. Quindi >=0,03 impossibile, regola incrementale V2 INATTIVA su tutti i 65 mesi. ADAPT4+V2 è realmente MA3/Hybrid24/risk con nuova selezione ADAPT4, non prova del beneficio della clausola V2. ADAPT4 500x24 dà gap medio 0,04013, mediano 0,02685 e 19.710 basket-days di intervento V2.

## ATTENZIONE: residuo storico ancora non attribuito

Il 500 MA3 V2 sul 2021–2026 nuovo rende **14,2279%**, mentre il report di settembre della stessa famiglia ETF Trader su 2017–26 annunciava **24,897%**, differenza nominale **10,669 punti**. I due periodi NON sono uguali, quindi non sottrarli come misura causale. Non è stata comunque dimostrata la parità byte-per-byte del nuovo dataset con il dataset sorgente certificato del 24/9/2026.

Quello originale certificava Parquet OPEN SHA256 c9f64a63..., CLOSE 90bbab..., LOW b1d7ee... e altri, 2.366 sedute tra 2017-02 e 2026-07. Il nuovo archivio è un file di quote Yahoo regenerato nella campagna del 18/9/2026 in formato CSV (run 36551650325) con sedute COMUNI a 149 e riparazione locale dell'envelope High/Low; non si è verificato l'identico content-hash con i Parquet originali. Il manifest di uno snapshot ricostruito distinto nel repository originale dichiara esplicitamente historical_parity=false; è prova che DIFFERENZE di vintage erano già note, non prova che questo archivio sia necessariamente errato.

La verifica forense in ETF Trader originale del 24/9 aveva anche scoperto che la ricostruzione degli ID cluster alterava le feature e i risultati di più punti percentuali. Quella campagna ha poi ricertificato il suo preciso source current raw, ma non ha certificato che tutti i futuri Yahoo CSV abbiano uguali matrici.

Per dichiarare spiegato il residuo va ripetuto il MEDESIMO vecchio run 2017–26 esattamente sugli stessi Parquet con SHA autorizzati, verificare la serie mensile predetta 2021–26 e infine isolare la differenza di periodo. Il semplice cambio a 500 panieri qui ha spiegato solo 3,75pp; non chiamare il restante divario un bug o overfitting senza aver confrontato identici dati.

## Valutazione predittiva

ADAPT4 all 149 libero resta +29,1748% CAGR, MaxDD -38,8694%, riproducibile nel simulatore invariato sui 65 mesi. È un successo di backtest NON un successo di validazione prospettica: rendimento 2025 +79,12%, 2026 parziale +59,15%, e la correlazione media monthly Spearman migliorata soltanto da 0,02864 a 0,04967, paired bootstrap CI relativo comprende 0. Perciò non promuovere produzione senza unseen post2026, verifica origine quote e reale broker trading.

## Evidence e sorgenti

- Nuova Action completata: https://github.com/AM1975MA/Test/actions/runs/39339600413
- Run single149 di riferimento: https://github.com/AM1975MA/Test/actions/runs/39338133099
- Originali 149 storici: https://github.com/AM1975MA/Etf_trader/blob/main/docs/ETF_TRAINER_V2.md
- Report originale source current raw: https://github.com/AM1975MA/Etf_trader/blob/main/results/MA3_SOURCE_ONLY_ENSEMBLE_CURRENT_RAW_20260924.json
- Fonte data-vintage originale: https://github.com/AM1975MA/Etf_trader/blob/main/data/provider_snapshot/MANIFEST.json
- Storico difetti cluster: https://github.com/AM1975MA/Etf_trader/blob/main/results/MA3_SOURCE_FIDELITY_FORENSICS_20260924.json
- Risultati nuovi: research_reset/us149_adapt4_free/matched_results/RESULT.json, ORIGINAL_SOURCE_FULL149_VS_500_US149_METRICS_BY_BASKET.csv, ORIGINAL_SOURCE_TRUE_MONTHLY_FREE_VS_500_SELECTIONS.csv, SHA256_MANIFEST.txt. Sorgente matched_geometry_audit.py e protocollo MATCHED_500_VS_149_PREREGISTERED_20261020.md.

Originale Etf_trader produzione **non modificato**.
