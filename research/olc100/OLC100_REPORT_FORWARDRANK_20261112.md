# OLC100 — Primo risultato di ricostruzione originale e verifica economica luglio–ottobre 2026

**12 novembre 2026 — Solo ricerca retrospettiva. Nessuna validazione prospettica né indicazione di trading.**

## Esito tecnico

**PASS per lo scorer e il ranking originali**: Return125 125/125 feature su entrambi i mercati; Hybrid42 42/42; cluster originali 328/328 EU e 298/298 USA; 60 modelli OLC14 sui cinque orizzonti, più i sei modelli ET/XGB di OLC11 e i tre modelli Return125 per mercato. Riuscita la ricostruzione della memoria 40/30/30, dei pesi contestuali, della FUSION 47,5/52,5 e della selezione Top2. Il replay dei sei mesi storici 2026 per mercato dà score contestuali e Top2 identici agli archivi. Gli errori XGBoost grezzi sono inferiori a 5 × 10⁻⁸; un pareggio XGB a metà graduatoria EU può spostare un percentile di 0,00122, senza cambiare i Top2 storici.

## Nuovi Top2 ottenuti, solo retrospettivi

| Mercato | Segnale | Top1 | Top2 | Peso Top1 MINVAR63 | Score Top1 | Score Top2 |
|---|---|---|---|---:|---:|---:|
| EU | 2026-07-31 | VVSM.DE | IBCJ.DE | 25.00% | 0.924341 | 0.911108 |
| EU | 2026-08-31 | VVSM.DE | EXV3.DE | 25.00% | 0.974992 | 0.958804 |
| EU | 2026-09-30 | VVSM.DE | LBRE.DE | 25.00% | 0.961958 | 0.922684 |
| EU | 2026-10-30 | EXV6.DE | LBRE.DE | 25.00% | 0.978554 | 0.958431 |
| USA | 2026-07-31 | BNO | USO | 69.39% | 0.976616 | 0.956696 |
| USA | 2026-08-31 | PPLT | SLV | 75.00% | 0.942230 | 0.941374 |
| USA | 2026-09-30 | TAN | ICLN | 25.00% | 0.930936 | 0.907934 |
| USA | 2026-10-30 | SLV | URA | 56.63% | 0.927976 | 0.896694 |

**Importante:** sono previsioni generate dopo che i prezzi dei mesi osservati erano noti. I modelli e le formule non sono stati rifittati; la ricostruzione postuma e gli aggiustamenti provider impediscono di presentarle come previsione originariamente pubblicata.

## Risultati economici: prezzo della sola coppia, non NAV OLC19

Rendimenti lordi dei due ETF da apertura ad apertura; tre intervalli luglio→agosto, agosto→settembre, settembre→ottobre maturati. Nessun costo, stop, V6, liquidità, gap di esecuzione o accounting on-policy. DELAY3 = ingresso alla terza apertura utile, uscita alla prima apertura del segnale successivo. Il segnale ottobre non rientra nella sintesi poiché il suo mese non è maturato.

| Mercato | 50/50 immediato | MINVAR immediato | 50/50 DELAY3 | MINVAR DELAY3 |
|---|---:|---:|---:|---:|
| EU | -1.10% | -1.04% | -5.49% | -4.56% |
| USA | +1.80% | +1.73% | +1.72% | +1.52% |

## Ablazione della sola selezione — contesto contro FUSION senza contesto

Quattro eventi per mercato: la rivalutazione contestuale sostituisce almeno uno dei due ETF in 2/4 mesi EU e 2/4 USA. A timing e pesi 50/50 identici, la variazione dei rendimenti *statici* maturati per gli eventi con sostituzione è:

| Mercato | Segnale | Delta contesto − originale, immediato | Delta contesto − originale, DELAY3 |
|---|---|---:|---:|
| EU | 2026-07-31 | — | -4.42% |
| EU | 2026-07-31 | -3.98% | — |
| EU | 2026-09-30 | — | -1.94% |
| EU | 2026-09-30 | -2.80% | — |
| USA | 2026-08-31 | — | +3.73% |
| USA | 2026-08-31 | +3.89% | — |

Le differenze sono marginali di **selezione su prezzi**, non controfattuali di conto con stesso stato. Non indicano alpha generalizzabile.

## Perché la validazione prospettica e il CAGR del portafoglio restano bloccati

1. Gli archivi hanno 79 anomalie di geometria OHLC post-1° luglio (più 4 nella sovrapposizione); anche se non necessariamente nei titoli selezionati, possono contaminare feature e cluster. Non sono state corrette silenziosamente.
2. Il ledger nativo OLC19/OLC67 termina alla prima apertura luglio 2026. Per ottenere NAV, CAGR, drawdown, cash, stop, V6 e FAST_LOCK3 servono **continuazioni certificate del risk state e della policy di esposizione** e prezzi eseguibili; non si deve simulare un conto diverso e chiamarlo OLC67.
3. Il dataset nuovo è stato scaricato il 12 novembre 2026 e può incorporare aggiustamenti corporate action successivi alle date dei segnali; non ci sono record pre-outcome certificati per luglio–ottobre.
4. Tre mesi maturati non forniscono confidenza statistica, nonostante il replay del ranking storico sia accurato.

**Decisione:** mantenere OLC19 baseline e OLC67 candidato shadow non promosso; utilizzare le otto coppie come un test di trasporto dei forecast nel nuovo calendario. Nessun nuovo modello/iperparametro scelto a posteriori.

## Riproducibilità

Gli script e gli output principali sono nel pacchetto ZIP. I modelli originali e il dataset OHLCV rimangono riferimenti a snapshot esterni necessari per la riproduzione; il pacchetto è deliberatamente leggero e **non autonomo**. Lo snapshot di origine dei prezzi è l’artefatto GitHub Action OLC100 source capture del 12 novembre 2026, con anomalie documentate. I notebook non devono utilizzare label futuri per produrre score.
