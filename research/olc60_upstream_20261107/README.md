# OLC60 — Riproduzione esperimento a monte (7 novembre 2026)

**Research only; OLC19 e main invariati.** Questa cartella contiene la verifica del primo test su 42 feature native e obiettivi ``NEAR`` vs ``PERSIST``. Non contiene un nuovo backtest di portafoglio.

## Input originali necessari

Recuperare dalla ChatGPT Library:

- `/ETF_Research/OLC14_Fitting_Ranking_20261101/OLC14_Heads_Checkpoint_20261101.zip`. SHA256 `a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458`.
- `OLC14_Fitting_Risultati_20261101.zip` nella stessa cartella. SHA256 `4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1`.

I file **non** sono duplicati nel pacchetto OLC60. Python 3.10+ con `pandas`, `numpy`, `scikit-learn`, `joblib`.

## Comandi

```bash
python run_olc60.py --heads OLC14_Heads_Checkpoint_20261101.zip \
  --results OLC14_Fitting_Risultati_20261101.zip --out results
python verify_olc60.py --original-results OLC14_Fitting_Risultati_20261101.zip
python analyze_retrieval.py --infile results/OLC60_PREDICTIONS.csv.gz \
  --out results/OLC60_RETRIEVAL_ORACLE_DIAGNOSTIC.csv
```

Controlli: hash dei due archivi, date mature, stessi ticker/date per i metodi, nessun futuro nel fit, parità nativa pesi e score Top2, risultati per EU e USA, precisione e rendimenti di lungo orizzonte, bootstrap descrittivo 6 mesi.

`PROTOCOL_PRE_RESULTS.md` fissa l'ipotesi e i parametri prima degli outcome; la correzione metodologica successiva, esclusivamente per i pareggi Top2, è dichiarata nello stesso file. L'oracolo Top10 nell'analisi aggiuntiva **usa i rendimenti futuri** e non è una strategia negoziabile. Il 2025 è retrospettivo e non OOS indipendente.