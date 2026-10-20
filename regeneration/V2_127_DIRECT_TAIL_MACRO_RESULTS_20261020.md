# ETF Trader V2: ritaratura DIRETTA Tail e macro con XGBoost 127 foglie
Data: 2026-10-20. Stato: **completato e verificato indipendentemente**.

## Provenienza e controlli
- Repository originale: `AM1975MA/Etf_trader`.
- 500 panieri canonici di 24 ETF, 149 ticker, file membership identico byte per byte nel repo `AM1975MA/Test`.
- Git blob SHA: `e7d75a83f161a56aa8846088d6c5869d80a72af3`.
- SHA256 membership: `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- Input predizioni XGB a 127 foglie congelate della run [39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691); snapshot OHLCV identico, 102 segnali OOS da gennaio 2018 a giugno 2026, di cui 101 etichettabili a 21 giorni.
- I soli Ridge **Tail e Macro** sono stati rifittati causalmente per anno usando cutoff e maturazione label invariati: nessun riaddestramento XGBoost.
- **Gate di fedeltà al modello storico superato**: 15.198 predizioni ricostruite e punteggio finale V2 con `Tail=0.30, macro_bonus=0.15` identico entro `1.11e-16` ai frozen score originali. L'importazione CSV richiede `float_precision='round_trip'` per evitare artefatti di ordinamento su punteggi quasi uguali.
- Replay Top2/Top3 con **risk=False**, next-open, commissioni 0,1%, regole e periodi originali. Replica baseline legacy 9,4370% CAGR medio e -52,4451% MaxDD medio. Due motori indipendenti hanno prodotto per 126 alternative massima differenza di `1.11e-16` su CAGR e MaxDD.
- Esecuzione GitHub: [39496306356](https://github.com/AM1975MA/Test/actions/runs/39496306356) SUCCESS. Artifact `v2-127-direct-tail-macro-results` (contiene FROZEN_COMPONENTS.csv, audit, risultati mensili, griglia, JSON).

## Esperimento
- Tail `0,.1,.2,.3,.4,.5,.6` con peso residuale `1-Tail` a XGB, in luogo dei vecchi 0,70 XGB + 0,30 Tail.
- Bonus macro `0,.05,.1,.15,.20,.30`, applicato solo ai titoli per cui `top_macro==macro_category and macro_gap>=.75 and tail_rank>=.8`.
- Acquisti Top2 50/50, Top3 33/33/33, Top3 50/30/20: **7×6×3 = 126 varianti**; V2 legacy come controllo 127°.
- Per ogni variante: CAGR medio per paniere, drawdown medio, CAGR e drawdown della NAV aggregata, turnover e bootstrap appaiato dei rendimenti logaritmici su blocchi di 6 mesi dei 101 mesi operativi.
- Il risultato 2018–2023 è diagnostica di sviluppo; **2024–2026 NON è un holdout prospectively unseen**, essendo stato già consultato nelle fasi antecedenti.

## Risultati principali

| Score e allocazione | CAGR medio | MaxDD medio | CAGR NAV aggregata | MaxDD NAV aggregata | Turnover /anno |
|---|---:|---:|---:|---:|---:|
| **V2 originale**, Tail 30%, macro 0,15, Top2 75/25 (o 100/0) | 9,44% | -52,45% | 12,05% | -38,20% | 13,88 |
| **XGB puro**: Tail 0%, macro 0, Top2 50/50 | **11,27%** | -47,53% | **12,92%** | -39,66% | 13,90 |
| **XGB puro**, Top3 50/30/20 | 11,16% | -45,45% | 12,52% | -39,59% | 13,30 |
| **Tail 30%, macro OFF, Top3 33/33/33** | **10,70%** | **-43,29%** | 11,85% | **-37,77%** | 10,79 |
| Tail 30%, macro storico 0,15, Top3 33/33/33 | 10,49% | -43,49% | 11,64% | -37,77% | 10,76 |
| Tail 30%, macro OFF, Top2 50/50 | 10,57% | -47,86% | 12,34% | -37,79% | 12,57 |

Le metriche NAV aggregata equivalgono a investire inizialmente il medesimo capitale in tutti i panieri e poi aggregare le loro curve: non sono la media aritmetica dei singoli CAGR.

## Evidenza fondamentale sul macro
L'attuale gate macro **si attiva in soli 2 mesi su 102**:
- Segnale 30 settembre 2022, categoria C06_REAL_ASSETS, 9 ETF con bonus;
- Segnale 29 dicembre 2023, stessa categoria C06_REAL_ASSETS, 11 ETF con bonus.

Il bonus interessa **20 assegnazioni ticker-data su 15.198 (0,132%)**. Tutte le 21 coppie Tail×allocazione mostrano CAGR decrescente all'aumentare del bonus nel campione, ma l'effetto dipende da soli due shock di allocazione, **non** prova che le feature macro siano prive di utilità generale. La soglia `macro_gap>=0.75` rende inoperante la regola nel 98% dei mesi. I cambiamenti marginali di NAV si propagano lievemente a mesi successivi per compounding e commissioni.

## Tail: contributo dipendente dalla struttura del portafoglio
Senza macro:
| Peso Tail | CAGR Top2 pari | CAGR Top3 pari |
|---|---:|---:|
| 0% | 11,27% | 10,41% |
| 10% | 10,91% | 10,50% |
| 20% | 10,41% | 10,43% |
| 30% | 10,57% | **10,70%** |
| 40% | 9,61% | 10,30% |
| 50% | 9,08% | 9,92% |
| 60% | 8,65% | 9,47% |

Quindi un Tail al 30% aiuta la diversificazione Top3, ma indebolisce il CAGR Top2 rispetto a XGB puro; non è corretto dire semplicemente "Tail non serve".

## Capacità di cattura dei vincitori a 21 giorni, 500 panieri ×101 mesi
- V2 storico Tail 30% / macro 0,15: Top1 15,19%, Top3 38,17%.
- XGB puro Tail 0% / macro 0: Top1 15,09%, Top3 35,75%.
- Tail 30% / macro 0: Top1 15,32%, Top3 38,23%.

Questo è compatibile con la natura complementare di Tail: migliora la probabilità di cattura Top3, ma non garantisce maggior CAGR se il portafoglio privilegia Top1/2.

## Incertezza e limite decisionale
Uplift log annuo vs V2 legacy, bootstrap a blocchi di 6 mesi e 3.000 repliche, unità indipendente mese e NON 500 panieri:
- XGB puro Top2 50/50: +2,04 punti percentuali log/anno; IC95 [-0,96; +5,41].
- XGB puro Top3 50/30/20: +1,96 punti; IC95 [-1,01; +5,37].
- Tail 30% macro OFF Top3 pari: +1,54 punti; IC95 [-1,10; +4,27].

Gli intervalli includono zero. Il confronto di 126 candidate sullo stesso storico comporta anche **multiple-testing/data snooping**. Il 2024–26 è già stato esaminato: non trattarlo come prova di generalizzazione.

## Decisione e prossima ipotesi
1. **Non cambiare il modello operativo e non accendere ancora il risk layer.**
2. Conservare come tre **candidate da validare**:
   - Rendimento: XGB solo + Top2 50/50.
   - Compromesso rendimento/diversificazione: XGB solo + Top3 50/30/20.
   - Minimo drawdown medio / migliore cattura Top3: Tail 30% + macro 0 + Top3 equiponderato.
3. Evitare nuove ricerche del "migliore" sulla medesima storia senza correzione per data snooping. Se si approfondisce il macro, testare **come fonte di regime continuo e informazione per il ranking**, senza usare il bonus sparse storico come proxy di efficacia dell'informazione stessa.
4. Scelte di coefficienti e schema devono essere preregistrate prima di valutare nuove osservazioni temporali; successivamente, e non prima, testare separatamente il layer rischio.
