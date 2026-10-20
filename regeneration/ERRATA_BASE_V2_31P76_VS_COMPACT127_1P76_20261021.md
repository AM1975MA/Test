# ERRATA — «Base V2» originale ≠ Compact21 127 foglie, 21 ottobre 2026

## Rettifica quantitativa certa

Le cifre **31,7581%** e **1,57099%** NON si riferiscono alla stessa strategia. È stato un errore chiamare "V2 legacy" il secondo backtest, perché indica solo il *vecchio schema di composizione Compact21 70% + Tail 30% + bonus macro 0,15 e allocazione Top2 75/25*, mantenendo il **nuovo** modello Compact21 XGBRanker 127 foglie. Non è il **BASE** di ETF Trader V2.

### BASE V2 vero, originario USA149 unrestricted

Sorgente audit: `isin_first2026/canonical_v2_same_period/results/ORIGINAL_149_FULL_SOURCE_2017_2026_AND_2021_2026.json` sul branch `research/canonical-v2-source-us149-eu48-20261020`. [Audit sorgente](https://github.com/AM1975MA/Test/blob/research/canonical-v2-source-us149-eu48-20261020/isin_first2026/canonical_v2_same_period/SCIENTIFIC_DECISION_20261020.md)

L'archivio della run [39044619710](https://github.com/AM1975MA/Test/actions/runs/39044619710) conserva 3 path giornalieri originali, **un portafoglio libero sull'universo 149 ETF per ciascuna delle 3 vintage delle quotazioni**, sotto `v2replay-ECON_TOP5_RERANK-r{1,2,3}/baseline_control/FULL_UNIVERSE_PATH.npz`. La verifica di tutte le tre curve è stata ripetuta in questo audit:
- Full 2017-02-01..2026-07-01, singole 3 vintage: CAGR 29,7534%, 30,8437%, 34,6771%. Media aritmetica CAGR **31,7581%**; MaxDD medio **-32,2164%**.
- 2018-02-01..2026-07-01 allineato al periodo in cui il nuovo Compact127 è investito, medesime NAV originale ripartite sul sottoperiodo, CAGR 31,6529%, 28,5547%, 34,5535%; media **31,5870%**. Queste sono 3 vintage del medesimo mercato, NON 3 repliche indipendenti.
- 2021-02-01..2026-07-01 media CAGR **34,9317%**, MaxDD **-26,0022%**.

Architettura di questo BASE V2:
- Hybrid24 produttore composto ExtraTrees 60% e XGB regressore 40%, target **0,45×rank21^1,5 + 0,35×rank42^1,5 + 0,20×rank63^1,5**;
- smoothing del Tail, selettore dinamico V6, DD-first + High-CAGR24;
- calendario giornaliero, rischio/gross non costanti, stop al 5,5% e slippage 0,1%, esecuzione Stage19;
- report canonico del vecchio V2 nel repository originale con **24,897% CAGR medio** descrive una **metrica differente**: la media dei 500 panieri; non contraddice il 31,758% sul portafoglio libero 149 ETF.

### Nuovo test Compact21 XGB 127 foglie USA149 unrestricted

[Run 39506923532](https://github.com/AM1975MA/Test/actions/runs/39506923532): `v2-127-free149-results`, artifact ID 12303512414, RESULT.json, NAV, TURNOVER. 149 ETF liberi come pool, ma **nuovo** ranker XGBRanker pairwise con target rank 21 giorni, ensemble 3 seed, MAX_LEAVES 127, distinto dal produttore precedente. Predizioni partono solo gennaio 2018, conseguentemente un anno inattivo nel replay 2017-26.
- "V2_legacy", etichetta **sbagliata e da NON riutilizzare**: Compact127 + score vecchio mix Tail/Macro + allocazione 75/25 (o 100/0), *risk=False*, nessuno stop giornaliero: **1,57099% CAGR full incluso inattività**, **1,75999% CAGR dal primo investimento**, MaxDD -51,9583%.
- Compact127 XGB puro + Top5 uguali: **19,8330%** CAGR includendo inattività, **22,4469%** dal primo investimento, MaxDD -42,8680%.
- Parity del nuovo replay con il **motore semplice di esecuzione Compact21** solo; non equivale a parity con Stage19 originario.

## Cause della falsa comparazione

| Asse | VERO BASE originale ETF Trader V2 | NUOVO test |
|---|---|---|
| Asset pool | Portafoglio unico 149 ETF | Portafoglio unico 149 ETF |
| Produttore | Hybrid24 ET+XGB, target 21/42/63 | Compact21 XGBRanker 127, solo rank 21 |
| Segnali | Layer Titanium/MA3, smoothing, score originali | Score Compact21 con Tail/macro **nuovi** |
| Decisione | Stage19, V6, DD-first, High-CAGR24 | Semplice TopK mensile |
| Rischio | Gross dinamico, stop 5,5%, slippage | Esposizione 100%, nessuno stop |
| Inizio OOS | 2017 | 2018; 2017 inattivo |
| Prezzi | 3 vintage di OHLCV archiviate | 1 snapshot congelato recente |
| CAGR | 31,7581% medio 2017-26 (31,5870% dal 2018) | 1,75999% nuovo Top2 Compact127 (22,4469% nuovo Top5 XGB) |

Conclusione: il BASE originale **non è regredito né è stato alterato**. Abbiamo sostituito l'intera architettura strategica quando volevamo testare una possibile evoluzione del solo ranker. Il solo fatto che entrambi usino 149 ETF non identifica l'algoritmo. D'ora in avanti **BASE_V2_STAGE19_ORIGINALE_149** e **COMPACT21_XGB127_149** devono essere due ID differenti, con origine, run e parametri obbligatori.

## Protocollo per prossimo confronto valido
1. Congelare esattamente il BASE_V2_STAGE19_ORIGINALE_149 e replicarne NAV giornaliera e metriche per ciascuna vintage senza riparazioni non certificate.
2. Iniettare il ranking Compact21 XGB127 come *challenger isolato*, preservando i moduli Stage19 V6, DD-first, High-CAGR24, esecuzione e controllo rischi; se l'interfaccia score non è compatibile, progettare un adattatore con audit.
3. Valutare differenze per data identica e vintage identica, distinguendo modifica del producer da modifica della politica TopK; testare Top1/2/3/5 **dentro il medesimo motore**, con eventuale risk-off disabilitato in entrambe le serie solo durante l'ablazione.
4. Separare prestazioni storiche di sviluppo da validazione prospettica, mai chiamare di nuovo il primo nuovo score "Base V2".
