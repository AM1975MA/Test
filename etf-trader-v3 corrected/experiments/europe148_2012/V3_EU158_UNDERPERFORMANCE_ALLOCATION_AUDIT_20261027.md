# V3 EUR158: verificata sottoperformance +9% e causa nell'allocazione (27 ottobre 2026)

**Studio diagnostico sul modello Ridge europeo, non un modello promosso in produzione. Non sono stati eseguiti i 500 panieri in questo studio.**

## Input invariati
101 decisioni mensili, 2018–2026, 148 ETF a sottostante europeo più 10 UCITS globali Xetra, stessi forecast **Ridge annuali originali 16F frozen** dello studio 26 ottobre, stessa eligibility as-of 252/63d, esecuzione next real Open, fee 10bps one-way. Nessun retraining per scegliere i portafogli di questo audit. Il roster di 10 ETF globali è stato identificato retrospettivamente nel 2026, con survivorship bias e concentrazione Nasdaq/tech: l'esperimento **non costituisce verifica out-of-sample affidabile di una nuova strategia**.

## Difetto quantitativo della selezione pooled
Tra **303 posizioni Top3**, il modello 158 sceglie solo **38 globali (12,54%)**. Nella coorte disponibile as-of vi sono mediamente **96,7 EU** e **9,1 globali**. Mean ex post 21d future total return per ticker-month nella coorte EU **+0,601%**, global **+1,377%**, ma il **massimo score** Ridge mensile medio EU **+0,004287**, global **+0,002110**: la classifica unica è sensibile alla numerosità delle alternative e ai punteggi estremi; un possibile effetto di calibrazione/selection noise, non ancora causalmente isolato.

## Stesso Ridge frozen, soltanto politica di allocazione diversa

| Portafoglio Top3 | CAGR netto EUR | MaxDD | Vol annua |
|---|---:|---:|---:|
| Ridge pooled 158 (originale) | **+9,02%** | -30,43% | 22,28% |
| Ridge quota **1 global + 2 EU** | +16,06% | -30,12% | 21,41% |
| Ridge quota **2 global + 1 EU** | **+16,80%** | -32,09% | 21,15% |
| Ridge 2 global+1 EU, max1 tech global | +15,79% | -31,76% | 19,91% |
| Momentum semplice (12–1) pooled 158 | +12,29% | -36,41% | 24,49% |
| **Momentum 12–1, 2 global+1 EU** | **+17,50%** | -35,66% | 22,69% |
| Momentum 63d, 2global+1EU | +18,55% | -31,64% | 20,87% |
| Buy-and-hold EXSA Europe | +8,86% | -35,22% | — |
| Buy-and-hold EUNL MSCI World | +12,58% | -33,20% | — |
| Buy-and-hold SXR8 S&P500 | +14,84% | -33,69% | — |
| Buy-and-hold SXRV Nasdaq100 | +20,69% | -31,21% | — |
| Buy-and-hold QDVE S&P IT | +25,05% | -33,57% | — |

Queste quote **non sono una proposta di allocazione ottimale**; sono controlli controfattuali, definiti dopo vari esperimenti sullo stesso storico. Il +16,80% conserva il **problema dei 10 UCITS selezionati col senno di poi**. Non può essere pubblicizzato come risultato corretto dei 500 panieri o incremento di alpha di Ridge.

Bootstrap 10.000 repliche blocchi 6 mesi, nominale, non corretto per specification-search: Ridge quota 2+1 vs pooled +7,67 pp CAGR CI95 **[+0,43; +15,06]**; Ridge 2+1 vs momentum stessa quota -0,38 pp CI95 **[-8,21; +7,28]**. Nessuna evidenza di superiorità Ridge al momentum nel confronto fair allocazione.

## Factor-matched alpha check
Regressione 101 rendimenti mensili con HAC Newey-West lag6, fattori (EUNL World, SXRV Nasdaq−EUNL, EXSA Europe−EUNL):
- Ridge pooled Top3 alpha annualizzato aritmetico **−0,68%**, IC95 **[−7,56%; +6,19%]**, R²=0,538.
- Ridge 2global1EU Top3 alpha **+0,73%**, IC95 **[−3,98%; +5,45%]**, R²=0,807.
- Momentum 2global1EU alpha **+1,67%**, IC95 **[−4,33%; +7,68%]**.
No factor-adjusted alpha confirmed. L'ultima osservazione di luglio 2026 è un singolo giorno segnato come fine mese, ulteriore limite dell'analisi di fattori.

## Prossima architettura verificabile
1. Universi comparabili e **ampi** di UCITS quotati in UE, centinaia di ISIN con listing/inception point-in-time + delisted, qualità corporate action verificata da feed indipendente. Non 10 ETF selezionati oggi.
2. **Stage 1**: previsione/decisione di allocazione macro tra aree e asset class con esposizioni e rischio controllati, **non** una quota imposta retroattivamente dopo aver visto la tecnologia salire.
3. **Stage 2**: Ridge signed-excess **within-category** sui soli ETF eleggibili con score-risk calibration, group-normalized selection, turnover e rischi.
4. Benchmark: momentum 12–1, passive world, passive US tech, allocazione factor-matched con controllo drawdown e costi/slippage. Il portafoglio deve battere benchmark di rischio comparabile, non solo superare una soglia CAGR.
5. Soltanto dopo ablation selettiva, implementare/verificare il protocollo originale **500 panieri** con trained vintages e test genuinamente nuovi.

**Dati, CSV completi, codice locale ed esecuzioni replicate** sono nel file ZIP consegnato in chat: `V3_158_UNDERPERFORMANCE_ALLOCATION_DIAGNOSTIC_20261027.zip`. Le predizioni e le fonti originali sono archiviate nell'esperimento [EU_GLOBAL_UCITS_BREAKTHROUGH_20261026.md](EU_GLOBAL_UCITS_BREAKTHROUGH_20261026.md); fonte [Actions data Xetra](https://github.com/AM1975MA/Test/actions/runs/40415451722). Nessun codice operativo o branch production modificato.
