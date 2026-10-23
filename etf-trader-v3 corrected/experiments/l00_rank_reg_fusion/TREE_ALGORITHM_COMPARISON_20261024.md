# ETF Trader V3 Corrected — approfondimento decision tree, boosting e meta-learning (24 ottobre 2026)

**STATO: COMPLETATO, TEST PASSATI, NESSUN NUOVO MODELLO PROMOSSO.**

Questa campagna parte dal checkpoint del **ranker CORRECTED125 → decision tree selettivo → NESTED_24_TOP1_GUARD**, senza modificarlo. Abbiamo misurato il vero OOS temporale del livello meta su 149 ETF, 500 panieri congelati da 24 ETF, 101 mesi maturati di segnali dal 2018-01 al 2026-05, partendo dagli stessi output annuali del primo modello. L'orologio di fitting include 60 giorni di embargo sui target forward-21D e il refit avviene all'inizio del trimestre. Non vengono ottimizzati i parametri usando il CAGR.

**Importantissimo:** non si tratta di holdout vergine perché questo stesso storico è stato impiegato in molte ricerche ETF precedenti. 500 panieri sovrapposti non sono 50.500 osservazioni indipendenti. I test statistici ricampionano blocchi da sei mesi, non panieri.

## Codice e run di riferimento

- [9 famiglie di algoritmi con obiettivo normale](https://github.com/AM1975MA/Test/actions/runs/40037256111) — tutti i 9 job PASS.
- [Validazione nested fra 9 famiglie e i 36 alberi originali](https://github.com/AM1975MA/Test/actions/runs/40037463931) — PASS, replica perfetta del checkpoint.
- [6 modelli con importanza della perdita/guadagno nella coppia ETF](https://github.com/AM1975MA/Test/actions/runs/40037653615) — tutti PASS.
- [Nested a 15 famiglie](https://github.com/AM1975MA/Test/actions/runs/40037957355) — PASS.
- [4 famiglie con 23 feature invarianti rispetto al paniere](https://github.com/AM1975MA/Test/actions/runs/40037938627) — tutti PASS, identità dei vettori feature per la stessa coppia ETF verificata numericamente.
- [4 famiglie con contesto paniere conservato, ma ogni coppia duplicata pesa 1/k](https://github.com/AM1975MA/Test/actions/runs/40038182585) — tutti PASS, normalizzazione matematica per ogni coppia verificata.
- **[Confronto definitivo fra 23 nuove famiglie, 113 combinazioni e 36 alberi originali](https://github.com/AM1975MA/Test/actions/runs/40038509415)** — PASS. La policy esistente è stata rigenerata e confrontata entro 1e-12, su tutti i 101 mesi.

## Risultati sintetici

Il risultato della singola configurazione a soglia fissa può sembrare buono, ma *non* decide l'esito. I modelli più interessanti a soglia fissa includono:

| Variante fissa (101 mesi) | Basket Top1 | Basket Top3 | Extra rendimento forward 21D vs media paniere | Cambiamenti corretti |
|---|---:|---:|---:|---:|
| Ranker CORRECTED125 (no meta) | 14,5525% | 35,4713% | +0,7122% | — |
| Vecchio albero depth3, leaf100, p>.60 | 14,8099% | 35,4713% | **+0,8496%** | 62,09% |
| DecisionTree con loss pesata per ampiezza, p>.55 | 14,5802% | 35,4713% | +0,8465% | 57,94% |
| HistGradientBoosting p>.60 | 14,4475% | 35,4713% | +0,8358% | 56,18% |
| DT con penalità 1,5x errori sfavorevoli p>.65 | 14,6020% | 35,4713% | +0,8177% | 73,83% (soltanto 596 sostituzioni) |
| RF con contesti corretti e p>.65 | 14,6891% | 35,4713% | +0,8142% | 69,24% (816 sostituzioni) |
| DecisionTree contesti pesati p>.60 | 14,7307% | 35,4713% | +0,8247% | 59,93% |
| CatBoost p>.60 | 14,5723% | 35,4713% | +0,7915% | 61,67% |
| XGBoost p>.60 | 14,3960% | 35,4713% | +0,7648% | 53,96% |

Qui l'extra rendimento è la **media aritmetica di differenze forward a 21 sedute**, non un CAGR e non profitto dopo costi. L'incremento Top1 da meta su singola soglia è OOS nella cronologia di fitting, ma la scelta della migliore soglia sull'intero sample introduce ulteriore bias di selezione.

### Il confronto che vale: modello e soglia scelti *prima* di vedere il mese

Confronto sullo stesso checkpoint `NESTED_24_TOP1_GUARD`, che arriva a Top1 14,5446%, Top3 35,4713% e selezionato 21D extra +0,8554%:

| Policy meta con scelta solo da OOS precedente maturato | Top1 | Top3 | Rendimento selezionato 21D | Delta rendimento vs checkpoint |
|---|---:|---:|---:|---:|
| **Checkpoint NESTED_24_TOP1_GUARD** | **14,5446%** | 35,4713% | **+0,8554%** | 0 |
| Solo 113 nuovi modelli, guard 24 mesi | 13,8119% | 35,4713% | +0,7046% | -0,1508 pp |
| Tutti, 24 mesi guard su Top1 | 13,7525% | 35,4713% | +0,7274% | **-0,1280 pp** |
| Tutti, 36 mesi guard su Top1 | 13,7961% | 35,4713% | +0,7217% | -0,1337 pp |

Per il selettore **ALL/24** vs incumbent, delta Top1 -0,7921 punti percentuali (bootstrap CI 95% -1,636/-0,141 pp); delta selected 21D -0,1280 pp (CI 95% -0,274/-0,0023 pp). I CI sono esplorativi/non corretti per model search e sample reuse, ma suggeriscono una degradazione concreta anziché un miglioramento.

Per il selettore **NEW_ONLY/24** vs incumbent: delta selected -0,1508 pp (CI -0,336/+0,0017 pp), top1 -0,7327 pp (CI -1,606/-0,0415 pp). Nessuno giustifica il rimpiazzo della configurazione corrente.

## Come leggere tecnicamente il risultato

1. Il problema del meta-ranker è *selective decision-making con astensione*, non forecasting di tutto l'universo. La capacità di evitare correzioni sbagliate può prevalere sull'AUC grezza.
2. Boosting più espressivo tende a intervenire più frequentemente senza sufficiente precisione; le probabilità non sono comparabili allo stesso threshold senza calibratura precedente e l'insieme di iperparametri selezionati su storia riusata produce altro bias.
3. La loss ponderata per \(|r_{alt}-r_{base}|\) consente più precisione sulle rare correzioni ad alta confidenza, ma perde o compensa troppo poco nel rendimento totale.
4. Il modello 23-feature invariante per coppia è corretto matematicamente ma elimina il contesto del paniere che pare utile. Il contesto mantenuto con pesi inversi delle duplicazioni è una variante di ricerca rigorosa, ma non ha mostrato miglioramento.
5. Il vecchio DecisionTree depth3/leaf100 ha un compromesso interessante tra bias e varianza sull'attuale dataset. Aggiungere capacità semplicemente aumenta il rischio di modellare rumore.

## Prossima ricerca, **senza moltiplicare inutilmente i test sullo stesso calendario**

- Bloccare il vecchio policy model e salvare gli sfidanti come ablation negative. NON cambiare il modello attivo né promuovere uno dei nuovi.
- Per un miglioramento credibile, raccogliere osservazioni in nuovi periodi realmente successivi/indipendenti, verificando eventuale sopravvivenza dell'alpha dopo costi, regime, esposizioni, slippage e numero effettivo di coppie ETF indipendenti.
- Per una eventuale nuova linea di modellazione, registrare ex ante un solo obiettivo di **expected regret risparmiato, perdita evitata e astensione**, soglie fisse sul primo holdout, features causali nuove (regimi macro/dispersione/volatilità) e calibrazione che impieghi esclusivamente dati cronologicamente maturi. CatBoost, LightGBM e XGBoost sono validi candidati *per un problema meglio specificato*, non come aggiunta cieca al vecchio meta-tree.

## Archiviazione e versioni

Sorgenti in `etf-trader-v3 corrected/experiments/l00_rank_reg_fusion/`, workflow dedicati sotto `.github/workflows/`. Tutti i 26 artifact completi devono essere archiviatati in `results/tree_algorithms_20261024/archives/` con tabelle direttamente consultabili e SHA256 dei file. Il checkpoint del 24 ottobre precedente, la V2 e i componenti trading `src` non sono modificati. Ogni cambio futuro richiederà commit e nuovo protocollo.
