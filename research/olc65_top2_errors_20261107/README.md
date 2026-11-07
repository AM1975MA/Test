# OLC65 — Diagnosi degli errori Top2

**Solo ricerca, nessuna modifica al modello operativo.** Il protocollo congelato è nel repository: [OLC65 preregistrazione](https://github.com/AM1975MA/Test/blob/research/olc65-top2-error-taxonomy-20261107/research/olc65_top2_errors_20261107/PROTOCOL_PRE_RESULTS.md).

## Risultati
- `REPORT_OLC65_IT.md`: interpretazione e caveat.
- `results/OLC65_SUMMARY.csv`: confronto aggregato, MAIN 2021–2024 e LATE 2025.
- `results/OLC65_MONTHLY_GAPS.csv`: dettagli 21/42 sedute, selezione reale vs due benchmark *oracle*.
- `results/OLC65_ORACLE_TOP2_CLASSIFICATION.csv`: classificazione esclusiva di ciascun futuro leader: discovery, ordering o già selezionato.
- `results/OLC65_FROZEN_SCORE_AND_OUTCOMES.csv.gz`: panel originale con score/ranghi ex ante e soli outcome ex post per l'audit.
- `results/OLC65_SELECTED_PERSISTENCE.csv`: leadership e persistenza della coppia selezionata.
- `results/OLC65_EXPERT_VISIBILITY.csv`: visibilità nei singoli componenti e sensitivity all'ablation.
- `results/OLC65_EXANTE_ASSOCIATIONS.csv`: associazioni preliminari, non adatte a un gate.
- `results/OLC65_ORDERING_SHARE_BLOCK_BOOTSTRAP.csv`: bootstrap descrittivo a blocchi (post-risultato).
- `results/OLC65_QA.json` e `results/OLC65_INDEPENDENT_QA.json`: verifiche.

## Riproduzione
Recuperare i quattro input *originari* dai percorsi della Library del progetto ETF:

- `/ETF_Research/OLC14_Fitting_Ranking_20261101/OLC14_Fitting_Risultati_20261101.zip`
- `/ETF_Research/OLC16_Contextual_Ranking_20261102/OLC16_Input_Code_Checkpoint_20261102.zip`
- `/ETF_Research/OLC19_Rischio_Rientro_20261102/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`
- `/ETF_Research/OLC61_Upstream_20261107/OLC61_PREDICTIONS.csv.gz` (compreso nel pacchetto OLC61, path `results/`)

Dipendenze: Python >=3.10, `numpy`, `pandas`, `scipy`.

```bash
python run_olc65.py --olc14 OLC14_Fitting_Risultati_20261101.zip \
 --olc16 OLC16_Input_Code_Checkpoint_20261102.zip \
 --olc19 OLC19_Rischio_Rientro_Checkpoint_20261102.zip \
 --olc61 OLC61_PREDICTIONS.csv.gz --out results
python verify_olc65_independent.py
python analyze_robustness.py
```

Il ricostruttore `reference_run_olc63.py` è una copia SHA256-identica di quello originario. Il file `reference_OLC63_MONTHLY_FACTORIAL.csv` serve come controllo contabile indipendente. Tutti gli input sono verificati con digest prima di ogni calcolo. **Non** leggere alcuna metrica oracle come segnale disponibile alla data dell'investimento.