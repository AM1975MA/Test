# ETF Trader V3 corrected — Utilità economica attesa e controllo del regret (24 ottobre 2026)

**Status:** nove esperimenti riproducibili completati (4 modelli + aggregazione + 3 replay economici + controllo fine-2025). Nessuna promozione alla strategia operativa. Manteniamo il checkpoint `CORRECTED125 + NESTED_24_TOP1_GUARD`.

## Protocollo e sorgenti esatti

- Originale first stage annuale OOS: [run 40016809498](https://github.com/AM1975MA/Test/actions/runs/40016809498); baseline meta vero: [run 40032282233](https://github.com/AM1975MA/Test/actions/runs/40032282233).
- Dati OHLCV congelati a luglio 2026: [run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691). **Non abbiamo segnali del ranker congelato dopo maggio 2026**; non dichiariamo una prova su un nuovo periodo indipendente.
- [Quattro meta-model hurdle, 8 policy](https://github.com/AM1975MA/Test/actions/runs/40079852872) — tutti PASS.
- [Confronto mensile/anno/per-coppia 8 varianti](https://github.com/AM1975MA/Test/actions/runs/40080236687) — PASS.
- [Replay economico next-open 10 bps, 3 policy diagnostiche](https://github.com/AM1975MA/Test/actions/runs/40080407962) — tre job PASS, 101 mesi × 500 panieri, corrispondenza **esatta** con risultati mensili già validati prima di permettere l'esecuzione e con benchmark economico originale entro 1e-11.
- [Stress per calendario con e senza 2026](https://github.com/AM1975MA/Test/actions/runs/40080774850) — PASS.

Sono *tutte prove di ricerca* sulla storia già utilizzata per altri esperimenti. Bootstrap paired a blocchi di sei mesi per la competenza e 21 sedute condivise per l'alpha dell'equity aggregata; i panieri sono fortemente sovrapposti.

### Funzione di decisione

Per ogni alternativa del Top3 congelato, il modello prevede:
- `p`: probabilità della differenza forward positiva.
- `g`: guadagno atteso condizionato alla differenza positiva.
- `l`: ampiezza della perdita attesa condizionata a una differenza negativa.

L'utilità della sostituzione è `U = p*g - lambda*(1-p)*l - 0.002`, dove `lambda=1.0` oppure `1.5` e la penalità fissa di 20 bps è un *proxy decisionale*, non una stima verificata di slippage. Se nessun `U > 0`, non si cambia il Top1. I target di spread del rendimento a 21 trading day next-open sono limitati a +/-20% nel fitting, e due regressori distinti sono addestrati sulle sole differenze positive/negative. Fitting trimestrale, esclusivamente coppie ETF distinte per mese e osservazioni maturate 60 giorni prima della prima data di ogni trimestre, pari peso totale per mese.

Confronti ex ante: `DT14` (14 feature score precedenti), `DT_REGIME`, `HGB_REGIME`, `RF_REGIME`. Le tre varianti regime aggiungono 13 predittori causali da prezzi adjusted close *con data <= segnale*: momentum a 21/63 sedute, volatilità e drawdown per ETF, breadth/momentum/dispersione cross-section degli ETF, SPY. **Avvertenza point-in-time:** la serie storica dei prezzi adjusted è una fotografia del fornitore posteriore alle date, quindi non è un vero dataset storicamente point-in-time, anche se nessuna riga futura entra nel calcolo delle feature.

## Test di competenza, 101 mesi OOS del meta-level

Medie `basket_top1`, `basket_loss10_top1` e `basket_selected_excess` calcolate su 50.500 paniere-mese dipendenti; il Top3 rimane 35,4713% per costruzione.

| Variante | Hit-rate Top1 | Selected excess a 21D | Downside selected <= -10% | Correzioni / 50.500 | Correzioni migliorative |
|---|---:|---:|---:|---:|---:|
| CORRECTED125 senza meta | 14.5525% | +0.7122% | 9.2614% | 0 | — |
| **NESTED_24_TOP1_GUARD (incumbent)** | **14.5446%** | **+0.8554%** | **8.5743%** | 2,209 | **60.03%** |
| DT14 lambda1.0 | 13.4693% | +0.5679% | 9.0673% | 12,773 | 48.24% |
| **DT14 lambda1.5** | **14.8733%** | +0.8464% | 9.0198% | 1,997 | **61.54%** |
| DT_REGIME lambda1.0 | 13.2396% | +0.6899% | 8.7287% | 14,134 | 48.24% |
| DT_REGIME lambda1.5 | 14.8218% | +0.8299% | 9.2356% | 4,511 | 53.00% |
| HGB_REGIME lambda1.0 | 12.9505% | +0.8541% | 7.7030% | 16,939 | 49.21% |
| HGB_REGIME lambda1.5 | 13.8970% | +0.8745% | 8.4475% | 5,951 | 50.63% |
| **RF_REGIME lambda1.0** | 13.7228% | **+1.0021%** | **7.6752%** | **14,749** | **50.95%** |
| RF_REGIME lambda1.5 | 14.1881% | +0.8159% | 8.8653% | 4,960 | 49.31% |

*Nota*: i nuovi coefficienti di avversione non sono stati ottimizzati sul CAGR. Il modello RF cambia quasi il 30% delle decisioni paniere-mese, e fallisce proprio l'abilità Top1, che il sistema originale intende preservare.

### Confronto statistico rispetto all'incumbent

Differenza mean selected excess in **punti percentuali per orizzonte 21D**. Bootstrap paired circulari sui 101 mesi (3.000 rep, blocchi sei mesi):
- DT14 lambda1.5: **-0.0090 pp**, IC95% **[-0.1302,+0.0920] pp**.
- DT_REGIME lambda1.5: **-0.0255 pp**, IC **[-0.2188,+0.1768] pp**.
- HGB_REGIME lambda1.5: **+0.0191 pp**, IC **[-0.1989,+0.2523] pp**.
- RF_REGIME lambda1.0: **+0.1467 pp**, IC **[-0.1918,+0.5529] pp**. Non significativo.

Se escludiamo 2026, la variante RF perde **-0.0386 pp/21D** contro il checkpoint; se eliminiamo anche i regimi 2022 e 2025, scende a **-0.0562 pp**. Non si tratta di holdout vergini.

Le correzioni DT14 lambda1.5 coinvolgono 1,997 decisioni paniere-mese ma appena **617 eventi coppia ETF/data distinti**; anche i risultati con loss avversa più elevata non sono 1,997 osservazioni statisticamente indipendenti.

## Backtest economico senza cambiare il risk overlay o l'allocazione

Esecuzione alla successiva apertura, 10 bps one-way su notional effettivamente scambiato, allocazione originale Top1 100%, Top2 75/25 o 100/0 quando gap ranker originale >=.12, Top3 50/30/20. Il risk layer rimane *disattivato per questo confronto isolato* e non si tocca il kernel operativo.

### Febbraio 2022 - giugno 2026

| Modello | CAGR aggregato Top1 | CAGR aggregato Top2 | CAGR aggregato Top3 |
|---|---:|---:|---:|
| Base ranker senza meta | 21.21% | 19.82% | 17.96% |
| **Checkpoint V3** | **24.62%** | **21.45%** | **18.54%** |
| DT14 lambda1.5 | 23.59% | 20.89% | 18.35% |
| HGB_REGIME lambda1.5 | 23.77% | 21.08% | 18.47% |
| **RF_REGIME lambda1.0** | **25.55%** | **22.71%** | **19.06%** |

I CAGR riguardano la NAV aritmetica media dei 500 panieri, **non** un singolo portafoglio aggregato negoziabile. Il MaxDD Top2 rimane intorno a -19% per tutte le varianti, con peggioramenti possibili in alcuni panieri.

### Controllo davvero importante: termine dicembre 2025

CAGR Top2 con stessa origine febbraio 2022 e metodo preciso `aggregate_cagr=last_nav**(252/n_trading_days)-1`:

| Modello | Termine 2025-12-31 | Termine 2026-06-30 |
|---|---:|---:|
| Checkpoint | **20.225%** | **21.450%** |
| DT14 lambda1.5 | 19.437% | 20.890% |
| HGB_REGIME lambda1.5 | 18.731% | 21.077% |
| RF_REGIME lambda1.0 | **19.098%** | **22.708%** |

Escludendo il 2026, la RF perde **1.128 punti di CAGR Top2** vs checkpoint; includendolo, passa a +1.257 pp. Anche nel confronto che parte da febbraio 2018 il segno è negativo fino al 2025 (-0.462 pp) e positivo quando include 2026 (+0.655 pp). **La performance 2026 determina l'apparente vantaggio della nuova RF.**

Bootstrap temporale 21-trading-day paired dell'alpha logaritmico annualizzato della RF vs checkpoint sul Top2:
- Periodo 2018-02..2026-06: **+0.565%**, IC95% **[-2.179%,+3.390%]**; include 0.
- Periodo 2022-02..2026-06: **+1.030%**, IC95% **[-4.164%,+6.557%]**; include 0.
- Periodo 2018-02..2025-12: **-0.404%**, IC95% **[-2.753%,+2.069%]**.
- Periodo 2022-02..2025-12: **-0.942%**, IC95% **[-5.962%,+4.085%]**.

## Conclusione e decisione di ricerca

Il nuovo obiettivo `P(win)*E(gain)-risk*P(loss)*E(loss)-switch_cost` fornisce *un'alternativa interessante sulla frontiera Top1 / rendimento / downside*, ma **nessun miglioramento stabile del checkpoint**:
- DT14 lambda1.5 migliora il Top1 senza guadagno di excess rendimento, però peggiora la frequenza di grandi perdite vs checkpoint.
- RF regime aumenta rendimento e riduce downside storico nel sample, ma peggiora Top1, aumenta gli interventi e **deve il suo vantaggio al 2026**.
- HGB regime migliora il downside con Top1 degradato e nessuna conferma robusta.
- Nessun confronto con il checkpoint supera la verifica bootstrap in modo statisticamente convincente.

**Preservare NESTED_24_TOP1_GUARD quale baseline di ricerca**, non promuovere modelli hurdle né ottimizzare lambda su questo storico già studiato. Il prossimo esperimento corretto richiede un dataset congelato davvero successivo alla scadenza dei segnali OOS, con rigenerazione del first-stage senza modificare la finestra di scelta e con protocollo *precommitted*; solo così si può parlare di conferma.

### Archivi

`hurdle_expected_regret.py` script originale, `compare_hurdle_regret.py` confronti, `hurdle_economic_replay.py` trading decision replay, `hurdle_exclude_2026.py` year-omission. Workflow versionati sotto `.github/workflows`. Cartella dei CSV e ZIP `results/utility_regret_20261024/`, manifest con SHA256 su ogni file; produzione V2/V3 invariata.
