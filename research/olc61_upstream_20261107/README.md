# OLC61 — Upstream economic-persistent Top2 research

Solo ricerca, non produzione. Non usa nuove fonti di mercato e non modifica i portafogli operativi.

## Riproduzione

Requisiti Python: numpy 2.3.x, pandas 2.2.x, scikit-learn 1.8.x, LightGBM 4.6.x, joblib.

Ripristinare i due archivi originali già salvati in ChatGPT Library:
- `/ETF_Research/OLC14_Fitting_Ranking_20261101/OLC14_Heads_Checkpoint_20261101.zip`
- `/ETF_Research/OLC14_Fitting_Ranking_20261101/OLC14_Fitting_Risultati_20261101.zip`

Ripristinare anche `OLC60_TOP2_SELECTIONS.csv` dal bundle OLC60, per l'ancoraggio della baseline.

```bash
python run_olc61.py --heads OLC14_Heads_Checkpoint_20261101.zip \
   --results OLC14_Fitting_Risultati_20261101.zip \
   --olc60-selections OLC60_TOP2_SELECTIONS.csv --out results
python analyze_diagnostics.py --results results
python verify_olc61_independent.py results
```

Il runner verifica gli hash dei checkpoint, le 42 feature e i cutoff. I 30 `models/*.txt` vengono ricaricati per verificare la parità; se il run viene ripreso dopo un errore solo di QA, il runner riutilizza gli stessi modelli da `results/models` senza nuovi fit. Per un fit nuovo usare cartella output vuota.

`results/OLC61_QA.json`, `OLC61_INDEPENDENT_QA.json`, `OLC61_SUMMARY.csv`, `OLC61_BLOCK_BOOTSTRAP.csv`, `OLC61_PREDICTIONS.csv.gz` e tutti i modelli costituiscono le evidenze eseguibili. I dati futuri sono **etichette** e valutazioni ex post: il modello prevede dal solo X/XP storico.

**Esito: NO PROMOTION**. L'OLC19 corrente e la fusione originale restano il riferimento.