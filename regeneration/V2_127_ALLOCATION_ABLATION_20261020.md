# ETF Trader V2 — 127 foglie: allocazione e layer score (20 ottobre 2026)

**Verifica completata, nessun risk layer e nessun riaddestramento.** Input: output OOS 127 foglie di [GitHub Actions 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), 149 ETF, 500 panieri canonici di 24, OHLCV fermi al 2026-07-01, prezzi di esecuzione al successivo open, fee 0,1% sul controvalore scambiato, segnali 2018–2026. Fingerprint panieri SHA256: 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e.

La replica numerica esatta del motore originale, prima di qualsiasi cambiamento, ha restituito CAGR medio 9,4370%, MaxDD medio -52,4451%, CAGR della NAV aggregata 12,0470%, MaxDD NAV aggregata -38,1964%. Il simulatore sparso di verifica riproduce la NAV del motore originale a precisione floating point (< 2e-14), sia con allocation originale sia Top3 equal.

## Ablazione isolata delle allocazioni (ranking V2 immutato)

| Pesi | CAGR medio | MaxDD medio | CAGR NAV aggregata | MaxDD NAV aggregata |
|---|---:|---:|---:|---:|
| Legacy Top2 75/25 o 100/0 | 9,44% | -52,45% | 12,05% | -38,20% |
| Top1 solo | 7,81% | -59,09% | 12,06% | -38,65% |
| Top2 50/50 | 10,30% | -48,06% | 12,07% | -37,79% |
| Top2 60/40 | 10,07% | -49,15% | 12,03% | -37,96% |
| Top2 75/25 | 9,49% | -52,02% | 12,02% | -38,22% |
| **Top3 uguali** | **10,49%** | **-43,49%** | 11,64% | -37,77% |
| Top3 50/30/20 | 10,31% | -45,62% | 11,79% | -37,96% |
| Top3 60/25/15 | 10,03% | -47,69% | 11,86% | -38,09% |
| Top3 70/20/10 | 9,65% | -50,22% | 11,92% | -38,22% |
| Top3 50/25/25 | 10,26% | -45,46% | 11,75% | -38,00% |
| Top4 uguali | 10,06% | -41,16% | 10,92% | -37,81% |
| Top5 uguali | 9,79% | -39,65% | 10,37% | -37,69% |

Media CAGR/MaxDD su paniere e metriche NAV aggregata hanno denominatori/semantica diversi. Il rischio sistemico resta elevato per tutti i metodi: il DD aggregato circa -38% è molto meno sensibile all'aumento del numero di ETF per paniere.

Con il nuovo score a 127 foglie il vecchio meccanismo che investe 100% nel Top1 oltre un gap di score pari a 0,12 scatta solo nel 3,65% dei casi: è quasi sempre una strategia Top2 75/25 fissa.

## Ulteriore ablazione ranking XGB puro vs layer score V2

Senza ricalcolare i modelli, confronto il percentile rank dello score XGBoost puro con lo score V2 già composto (Tail + macro). Un'interpolazione post-ranking tra questi due score NON è identica al riaddestramento o alla riscrittura dei coefficienti Tail/macro.

| Score / Allocazione | CAGR medio | MaxDD medio | CAGR NAV aggregata | MaxDD NAV aggregata |
|---|---:|---:|---:|---:|
| V2 completo / Top2 50/50 | 10,30% | -48,06% | 12,07% | -37,79% |
| **XGB puro / Top2 50/50** | **11,27%** | -47,53% | **12,92%** | -39,66% |
| V2 completo / Top3 50/30/20 | 10,31% | -45,62% | 11,79% | -37,96% |
| XGB puro / Top3 50/30/20 | 11,16% | -45,45% | 12,52% | -39,59% |
| V2 completo / Top3 equal | 10,49% | -43,49% | 11,64% | -37,77% |
| XGB puro / Top3 equal | 10,41% | -43,61% | 11,48% | -39,03% |

Sono state valutate anche interpolazioni alpha = 0, 0,25, 0,5, 0,75, 1 tra rank XGBoost puro e punteggio finale V2: CSV nella cartella di ricerca allegata alla conversazione.

## Verifica statistica

Bootstrap a blocchi circolari di 6 mesi su osservazioni *mensili*, dopo aggregazione dei 500 panieri fortemente sovrapposti. Uplift annualizzato log-return Top3 equal vs V2 originale +1,33 punti, 95% intervallo esplorativo da -1,21 a +3,86 punti. Uplift XGB puro Top2 50/50 vs V2 completo Top2 50/50 +0,88 punti, 95% intervallo da -1,64 a +3,49 punti. Entrambi gli intervalli includono 0; nessuna superiorità economica è statisticamente stabilita.

## Decisione tecnica

**Non** attivare il controllo rischio adesso. Conservare tre candidati per verifica OOS indipendente:
1. XGB puro + Top2 50/50: priorità rendimento, ma rischio aggregato più alto.
2. V2 completo + Top3 uguali: miglior drawdown medio dei panieri rispetto alla configurazione legacy.
3. V2 completo + Top2 50/50: compromesso semplice.

Congelare feature, train, target, universo e asset price snapshot. Non promuovere il vincitore scelto retrospettivamente senza ulteriore conferma.
