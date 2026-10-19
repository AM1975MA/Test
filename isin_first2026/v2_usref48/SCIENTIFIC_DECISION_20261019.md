# ETF Trader V2, 48 ISIN europei con SPY / HYG / IEF / BIL / SHV originali (19 ottobre 2026)

**Esito del confronto richiesto: negativo.** Il vero ETF Trainer V2, con un unico universo libero di 48 ETF europei deduplicati per ISIN, riaddestrato usando i fattori originali SPY in USD, passa da **+1,6362% CAGR / -37,1934% MaxDD** della prova precedente a **-0,2188% CAGR / -40,2522% MaxDD**. Le protezioni USA HYG/IEF/SPY non correggono il ranking europeo e ne peggiorano la performance. Il benchmark dello stesso refit, Hybrid24 senza l'incremento V2, ha invece +1,1102% CAGR e -36,2285% MaxDD.

## Esecuzione e fonte

GitHub Actions run riuscita: https://github.com/AM1975MA/Test/actions/runs/39326985222 . Dati SPY,HYG,IEF,BIL,SHV recuperati dai file storici originali USD dell'Action USA149 n. 36551650325; non sono ticker nuovi eleggibili per il Top1/Top2. Per BIL/SHV si presenta separatamente la variante con BIL/SHV come investimenti difensivi fuori dai 48, in euro calcolati come USD ETF ultimo close / EURUSD ultimo close precedente; non si confondono rendimenti EUR e USD.

Ognuno dei cinque scenari è stato simulato sullo stesso calendario e prezzo di 48 fondi: 65 mesi eseguibili, 1.374 Open Europe fra 2021-02-01 e 2026-07-01, 10bp costi, stop del 5,5%, slippage 0,1%, sorgente MA3 Hybrid24 e V2 congelata. 2.746 giornate Europa sorgente comuni dal 2015-08-10; fonti USD USA per SPY da 2004, HYG 2007, IEF 2004, BIL/SHV 2007. Feature di previsione USA sempre dalla chiusura di borsa statunitense di data **strettamente precedente** all'osservazione EUR; nel risk controller/V6 l'ultimo close USD del medesimo giorno entra solo via la latenza originale di 1 seduta EU, quindi noto al successivo Open EUR. ISO date e prezzi/manifest source verificati. Un certo numero di righe OHLC Europe aveva High/Low discordanti: riparazioni dell'envelope tracciate soltanto sui file derivati, mai su original raw Open/Close.

**La regressione di controllo riproduce esattamente il precedente V2 EU +1,6362% e MaxDD -37,1934%**, usando la stessa implementazione end-to-end, tolleranza hard 1e-11. Sei modelli Titanium 2021–26 riaddestrati annualmente e 6 MA3 Hybrid24 reale con maturity gate; nessun modello USA già stimato impiegato per fare previsioni; Top1 e Top2 solo tra i 48 ISIN europei.

## Matrice causale SPY e regimi originari

| Scenario | Hybrid24 CAGR netto | V2 CAGR netto | V2 MaxDD |
|---|---:|---:|---:|
| Vecchi score europei, rischio EU, difesa euro (controllo esatto) | +1,3602% | +1,6362% | -37,1934% |
| Vecchi score europei, **solo rischio US SPY/HYG/IEF**, stessa difesa euro | +0,7704% | +0,6460% | -37,0934% |
| Nuovi score riaddestrati con US SPY, rischio ancora EU, difesa euro | +0,7871% | -0,0495% | -40,7500% |
| **Nuovi score US SPY + rischio originale US SPY/HYG/IEF**, difesa euro | +1,1102% | **-0,2188%** | **-40,2522%** |
| Come sopra, ma investendo in **BIL/SHV USA** convertiti EUR anziché IBCA/IBCN | +1,1296% | -0,1549% | -39,9093% |

Differenza V2 US factor/risk rispetto a controllo precedente **-1,8550 punti percentuali CAGR** e -3,06 punti di MaxDD peggiorato. Sostituire difesa euro con BIL/SHV euro-marked cambia poco: +0,0639 punti CAGR in versione V2. I test differiscono nelle variabili indicate, senza iperparametri ottimizzati usando il risultato.

## Responsabile incrementale V2 negli USA risk states, non la sola difesa

Il vecchio V2 EU faceva scattare la condizione congiunta ExtraTrees + XGBoost e margine >3% in soli 3 mesi / 41 giornate, tutte 2022. Con nuovo score SPY e regimi US la regola V2 interviene in **6 mesi / 72 giornate**, ancora tutti 2022; spesso aumenta concentrazione sul settore auto/consumer discretionary Europa EXV5.DE. Il nuovo scenario primary 2022 rende Hybrid24 **-10,8177%** contro V2 **-17,0246%** (differenza -6,207 punti nella sola annata 2022). Gli altri anni V2: 2021 Feb-Dic +10,6115%, 2023 +23,0990%, 2024 -7,5513%, 2025 -9,5282%, 2026 Gen-Lug +4,5672%. Anni parziali non annualizzati.

Il cambio di rischio originale da solo, tenendo fissi tutti i vecchi score, porta il V2 da +1,64% a +0,65%; lo score nuovo con SPY cambia le scelte (es. EXV5.DE da 9 a 13 selezioni Top1, EXV1.DE banche da 6 a 4), con perdita economica. Non abbiamo validato un alpha predittivo robusto né con i fattori EU né con quelli USA.

## Limiti e conclusione

- Il cluster source europeo rimane 5 dinamici +1 sovrano per una disponibilità reale di 48 fondi, mentre USA149 originale ha 7 dinamici+1 difensivo. Quindi non è bitwise la simulazione USA149, ma è un confronto causale ben controllato del cambiamento delle reference equity/credit.
- SPY, HYG e IEF sono segnali USD, non titoli aggiuntivi negoziabili; BIL/SHV sono USA e nella variante difensiva espongono realmente al dollaro. Il loro euro-mark basato su prior US Close/FX è un'approssimazione, non un bid/ask Open negoziabile sui mercati europei.
- I 48 ISIN sono survivor scelti retrospettivamente nel 2026; storico Yahoo adjusted e Low/High talvolta anomali non prova reali fill Xetra. Ricerca, non trading live.
- No modifica del repo AM1975MA/Etf_trader. Nessuna ragione per promuovere V2 sui 48 europei.

**Decisione scientifica: mantenere gli originali market references USA non ripara la trasposizione europea.** È più probabile un mismatch nella capacità predittiva/asset-class opportunity e uno shock nei trigger di concentrazione V2 nei momenti sbagliati. Occorrono mercati opportunità equivalenti, medesimi periodi e validazione prospettica non compromessa prima di attribuire ad ETF Trader USA un alpha generale.

## Tracciabilità
- results/RESULT.json: dieci backtest completi e metriche.
- results/DAILY_NAV_ORIGINAL_US_SPY_HYG_IEF_AND_DEFENSE_COMPARISON.csv: tutte le dieci equity curve giornaliere.
- results/ALL_SCENARIOS_TRUE_EU48_65_MONTH_POSITION_CHANGES.csv: 65 segnali per scenario, leader, ISIN e intervento V2.
- results/USREF_MA3_HYBRID24_65X48_FORECASTS.csv: previsioni MA3 source-only realmente riaddestrate.
- results/REFERENCE_ASOF_AUDIT.json: date e SHA dei cinque ETF US e della FX EURUSD; results/SHA256_MANIFEST.txt per altri risultati.
- Sorgente integrale in v2_usref48/train_tit.py, run.py, us_source_helpers.py, original_us_references.py, PREREGISTERED.md.
