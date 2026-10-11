# Decisione tecnica: mantenere lo storico originale

Verifica conclusa su tutti e tre i download Yahoo congelati Original149: [Actions 38175552177](https://github.com/AM1975MA/Test/actions/runs/38175552177), tre audit e aggregazione **SUCCESS**. Branch `research/v2-history-2011-2012-20261011`, [PR #71](https://github.com/AM1975MA/Test/pull/71). Il confronto completo di performance 2017–2026 **non è stato eseguito** perché la nuova finestra non soddisfa il requisito originale per il primo fit annuale. Questo è un esito negativo di fattibilità, non un risultato di performance della variante.

## Vincolo numerico verificato

OHLCV derivati dal 2011-01-01; nessuna osservazione precedente negli input di calcolo. Il 2011 è solo riscaldamento; segnali di training dal 2012-01-01, con uscita dell'etichetta strettamente precedente al 1° gennaio dell'anno di fit.

| Componente | Mesi di training maturi al fit 2017, per ciascun download | Righe, per ciascun download |
|---|---:|---:|
| Compact21 | 58 | 8.422 |
| Compact63 | 56 | 8.124 |
| Tail | 56 | 8.124 |
| Macro | 56 | 336 |
| MA3 | 56 | 8.028 |
| Opportunity, percorso separato | 58 | 464 |

Il produttore originale `source_only.models.fit_predict` richiede **60 mesi maturi Compact21**. L'invocazione effettiva per il 2017, su tutti e tre i download, restituisce `SKIP_INSUFFICIENT_MATURE_HISTORY`, `train_signal_dates=58`, `required=60` e rifiuta di generare predizioni. Al fit 2018 sono disponibili 70 mesi Compact21; questo non giustifica presentare un eventuale backtest dal 2018 come confronto sul 2017–2026.

Non sono stati ridotti i 60 mesi, ammessi esempi del 2011, utilizzate etichette immature, inseriti punteggi storici o sostituito il 2017 con liquidità. Nessun modello della baseline è stato nuovamente addestrato.

## Baseline originale recuperata e verificata

Risultati da [run originale 37195399755](https://github.com/AM1975MA/Test/actions/runs/37195399755), verificati dalla [PR #48 / run 37934815636](https://github.com/AM1975MA/Test/actions/runs/37934815636) e nuovamente confrontati con il JSON canonico già presente in Test. Nessuna correzione downvol/MAD e nessuno scambio Ridge/LambdaRank sono inclusi.

Periodo congelato: **2017-02-01 – 2026-07-01**, 2.366 sedute; il 2026 non è un anno completo.

| Download | CAGR | MaxDD | Sharpe |
|---|---:|---:|---:|
| 1 | 29,7534% | −34,8621% | 1,0461 |
| 2 | 30,8437% | −25,6896% | 1,0870 |
| 3 | 34,6771% | −36,0975% | 1,1829 |

CAGR medio **31,7581%**, dispersione massimo–minimo **4,9236 punti percentuali**, deviazione standard della popolazione dei tre CAGR **2,1115 punti percentuali**.

Disaccordo giornaliero fra almeno due dei tre download: **Top1 1.018/2.366 = 43,0262%**; **coppia Top1/Top2 ordinata 1.812/2.366 = 76,5850%**; **insieme non ordinato dei due ETF 1.585/2.366 = 66,9907%**.

| Coppia download | Top1 | Coppia Top1/Top2 ordinata | Insieme Top2 non ordinato |
|---|---:|---:|---:|
| 1–2 | 33,2629% | 61,3271% | 49,0279% |
| 1–3 | 30,7692% | 66,1031% | 53,9307% |
| 2–3 | 30,0930% | 57,5232% | 48,7320% |

Il disaccordo medio pairwise del solo ETF in seconda posizione è 56,5793% (artefatto verificato PR #48); il disaccordo medio pairwise Top1 è 31,3750%. Queste definizioni differiscono dalla frazione di date con almeno una divergenza nei tre download. Le tre acquisizioni non costituiscono campioni statistici indipendenti.

**Variante 2011/2012:** CAGR, MaxDD, Sharpe, dispersione e disaccordo Top1/Top2 sul periodo completo sono **non disponibili**, rappresentati da `null` negli artefatti; non sono zero. Nessuna affermazione di miglioramento o peggioramento relativo è giustificata da questo esito.

## Causalità e conservazione degli input

I tre originali sono preservati e verificati con SHA256. Copie separate eliminano le righe pre-2011 conservando esattamente i byte dei valori OHLCV e universo. Tutti i produttori diagnostici ricevono queste copie, anche i riferimenti di mercato e gli input per i cluster MA3.

Su ciascuna acquisizione, ricalcolo da un prefisso terminante il 2016-12-30: uguaglianza esatta sulle date comuni per 125 feature Compact (8.791 righe), 60 Tail (8.791), 18 Extra (8.791), 18 Macro (354), 120 predittori Opportunity non-target (472), 42 MA3 (8.475) e membership MA3 (8.475). Le etichette forward sono escluse dal confronto delle feature e sottoposte separatamente ai limiti di maturazione. Questo test finito non certifica ogni data, corporate action o assenza di survivorship bias.

**Difetto esistente Opportunity:** `kernel.build_opp_panel` include `target_excess_max` e `target_excess_max_rank` tra i predittori selezionati per suffisso. Dipendono da etichette future; la configurazione completa Opportunity è esplicitamente **non certificata come causale**. Il controllo iniziale ha rilevato la dipendenza dal futuro. Il replay canonico verificato `build_tit_r_source_only -> source_only.models -> MA3 Hybrid -> Stage19` non usa questo router. Non è stato corretto o attivato durante l'esperimento, perché cambierebbe algoritmi/feature oltre alla finestra storica.

## Decisione e limiti

**Mantenere lo storico originale per il contratto operativo richiesto.** La finestra 2011/2012 non permette il fit iniziale 2017 con i requisiti V2 invariati. Non viene promossa per un CAGR medio e non esiste un risultato numerico della variante da confrontare. Lo storico originale conserva instabilità significativa: la decisione non afferma che l'abbia risolta.

Per verificare empiricamente l'effetto della storia ridotta sarebbe necessario autorizzare un esperimento diverso: ad esempio valutazione dal 2018, con baseline esattamente riallineata e medesimi costi/stato iniziale, oppure training precedente al 2012. Nessuno di questi cambiamenti è stato introdotto qui.

Ricerca esclusivamente su `AM1975MA/Test`; repository produttivo `AM1975MA/Etf_trader` non modificato, nessun merge o adozione.

Evidenza persistita: `results/SUMMARY.json`, `results/BASELINE_METRICS.csv`, `results/repeat1–3/{RESULT.json,TRAINING_ELIGIBILITY.csv,RAW_WINDOW_MANIFEST.csv}`; `BASELINE_VERIFIED.json`, `PR_RESEARCH_LEDGER.json`, `PREREGISTRATION.md`. Le prove di confine/inclusività, maturazione stretta e allineamento del disaccordo sono passate; revisione indipendente del codice completata.
