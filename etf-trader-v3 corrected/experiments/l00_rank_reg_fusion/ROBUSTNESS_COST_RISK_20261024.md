# V3 Corrected — Stress test meta-ranker, costi e controllo rischio (24 ottobre 2026)

**Stato:** test sperimentali COMPLETATI, non promossi in produzione. Modelli, dati e 500 panieri sono esattamente quelli del checkpoint salvato. Non abbiamo scelto nessun nuovo iperparametro sulla base del CAGR di questa campagna.

## Reproducibilità

- [Sensibilità costi da 0 a 100 bps](https://github.com/AM1975MA/Test/actions/runs/40035961810): 5 job riusciti.
- [Tree come trigger e secondo ETF originale](https://github.com/AM1975MA/Test/actions/runs/40036167353): 2 job riusciti.
- [Risk overlay originale](https://github.com/AM1975MA/Test/actions/runs/40036464750): test riuscito, con verifica numerica della NAV senza rischio contro l'esecuzione precedente entro 1e-10.
- [Robustezza strutturale OOS](https://github.com/AM1975MA/Test/actions/runs/40036590743): riuscito; stesso modello, 101 mesi, 149 ETF, 500 panieri originali da 24.
- Originali OOS ranker+regressori: Actions 40016809498. Decisioni Meta 50.500: Actions 40032693599. Scelta cronologica dei parametri: Actions 40032282233.
- Alcune esecuzioni preparatorie sono fallite per errori CLI e sono state corrette prima del test riuscito: le conclusioni si basano esclusivamente sui job finali con esito PASS.
- **Cronologia 2018–2026 storicamente studiata**, NON holdout indipendente. I bootstrap sono esplorativi e non correggono l'effetto di aver valutato molte configurazioni.

## 1. Sensibilità economica ai costi, periodo 2022-02–2026-06

CAGR su media NAV dei 500 portafogli di paniere, esecuzione next-open con costo per notional scambiato unidirezionale. NON CAGR di un singolo portafoglio implementabile.

| Fee bps | Base ranker Top1 | Ranker + tree Top1 | Vantaggio tree pp | Base Top2 | Tree Top2 | Base Top3 | Tree Top3 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 23.39% | 26.94% | +3.55 | 21.82% | 23.53% | 19.67% | 20.28% |
| 10 | 21.21% | 24.62% | +3.41 | 19.82% | 21.45% | 17.96% | 18.54% |
| 25 | 18.03% | 21.22% | +3.19 | 16.88% | 18.40% | 15.44% | 15.99% |
| 50 | 12.91% | 15.76% | +2.85 | 12.13% | 13.49% | 11.37% | 11.85% |
| 100 | 3.36% | 5.60% | +2.23 | 3.24% | 4.28% | 3.66% | 4.04% |

Il vantaggio relativo esiste in tutte le ipotesi di costo simulate ma il CAGR assoluto crolla a costi estremi; non sono simulate politiche realistiche di market impact dinamico, spread intraday o capacità di esecuzione.

## 2. Tree solo per sapere *quando* intervenire

50.500 decisioni paniere-mese **dipendenti**, ma 2.209 correzioni (41 mesi attivi, solo 786 diverse coppie ETF+data). Il tree completo cambia in meglio il rendimento futuro in 60.03% dei casi. Se mantiene il segnale del tree ma sceglie sempre il secondo ETF originale, è migliorativo nel 60.25% dei casi.

- Incremento medio su tutte le 50.500 decisioni a 21 sedute: tree completo +0.14320 punti percentuali; tree trigger + ranker secondo +0.14550 punti.
- Con 3.000 bootstrap a blocchi di 6 mesi, differenza tree completo minus semplice runner-up `-0.00230 pp`, IC 95% `[-0.0417,+0.0273] pp`. Nessuna evidenza solida a favore di uno dei due.
- Tuttavia il **backtest economico** con 10 bps nel 2022–26 Top1 dà ranker semplice 21.21%, tree-trigger/secondo 24.27%, tree completo **24.62%**. Top2: ranker 19.82%, tree-trigger/secondo 21.18%, tree completo 21.45%. Top3: 17.96%, 18.43%, 18.54%. La sequenza dei guadagni e la composizione contano, non soltanto la media non capitalizzata del target.
- Perciò non sostituire ancora l'albero completo con una regola di sostituzione fissa.

## 3. Quanto pesano eventi estremi e sovrapposizione dei panieri?

- Le 2.209 correzioni corrispondono a **786 distinti eventi coppia ETF+data**. La percentuale di correzioni positive scende al **54.20%** se diamo lo stesso peso a ogni evento distinto invece che al numero di panieri in cui si ripete.
- **5 gruppi fissi di 100 panieri**, separati per ID modulo 5: miglioramento +0.1563, +0.1610, +0.1274, +0.1474 e +0.1240 pp a 21D. Questi gruppi rimangono altamente sovrapposti in termini di ETF, non sono 5 holdout indipendenti.
- Il miglioramento medio complessivo a 21D **+0.1432 pp** scende a **+0.0758 pp** se il differenziale del rendimento fra ETF scelto e baseline è limitato a ±10%; scende a **+0.0404 pp** a ±5%. Quest'ultimo rimane positivo nel bootstrap temporale (IC 95% circa `[+0.0014,+0.0845] pp`), ma è molto più piccolo.
- Escludendo 2026: +0.1108 pp; escludendo 2022 e 2025: +0.0695 pp; escludendo **insieme 2022, 2025 e 2026: +0.0212 pp**, una forte concentrazione di regime. Nessun omesso anno può costituire un vero holdout dopo la ricerca condotta su tutto il periodo.
- Le correzioni puntano spesso a ETF tematici e strumenti sulle commodity, inclusi TUR, USL, UNG, HACK e XBI. La potenziale influenza degli shock e della scarsa diversificazione va trattata separatamente.

## 4. Integrazione congelata col controllo rischio già esistente

Risk layer del sorgente `etf_trader_v3.source_only.execution.replay(...risk=True)`: penalizzazione risk-on a 25% e 75% verso BIL/SHV se sono soddisfatte le soglie originali su distress e market breadth, cooldown originale 3 giorni; nessuna nuova ottimizzazione. Il test senza rischio riproduce esattamente la NAV a 10bps già convalidata, differenza massima inferiore a 1e-10.

| Periodo | Modello | Rischio OFF CAGR / MaxDD aggregato | Rischio ON CAGR / MaxDD aggregato |
|---|---|---|---|
| 2022–2026 | Ranker solo Top2 | 19.82% / -19.17% | 16.23% / -18.67% |
| 2022–2026 | Ranker + tree Top2 | 21.45% / -19.16% | 17.62% / -18.80% |
| 2018–2026 | Ranker solo Top2 | 14.82% / -39.08% | 14.42% / -24.00% |
| 2018–2026 | Ranker + tree Top2 | 15.68% / -39.08% | 15.21% / -24.00% |

- Il tree migliora la baseline anche a risk ON: +1.39 punti CAGR 2022–26, +0.79 punti CAGR 2018–26.
- **Il controllo rischio non va accettato sulla sola base della riduzione MaxDD sul campione 2018–26**: nel 2022–26 riduce di circa 3.6–3.8 punti il CAGR, accresce il turnover annuo Top2 da ~16.5–16.9 volte a ~20.5–20.8 e migliora solo marginalmente il MaxDD aggregato.
- Il bootstrap 21-day dell'alpha economico del tree sotto risk ON 2022–26 è `+1.317%/anno`, IC 95% `[-0.162%, +2.909%]`: include zero. Anche la differenza positiva storica non è confermata statisticamente.
- Il modello di rischio valutato è **la logica source-only esistente**, non una prova che tutti i layer della V3 full-stack siano già integrati correttamente.

## Decisione

**Conservare il checkpoint V3 NESTED_24_TOP1_GUARD quale ipotesi promettente ma sperimentale.** Nessuna promozione in produzione. Non cancellare i precedenti risultati. Il prossimo collo di bottiglia è verificare la robustezza su dati/periodi realmente non utilizzati in nessun tuning della ricerca, la stabilità sotto cambiamento dell'universo e gli effetti delle esposizioni a commodity/ETF tematici. Ridurre la focalizzazione sul CAGR e aumentare attenzione alla validità del segnale e al rischio di regime.
