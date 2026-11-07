# OLC63 — Native Original Fusion Attribution (7 November 2026)

Research only. No changes to production or to the `main` branch. Retrospective results on previously mined history.

## Contents
- `PROTOCOL_PRE_RESULTS.md` — fixed before original OLC63 outcomes.
- `run_olc63.py` — exact OLC14/16/19 reconstruction, 16 factor configurations, monthly Shapley, heads and Spearman diagnostic.
- `verify_olc63_independent.py` — independent full-score, uniform baseline, per-row Shapley check.
- `analyze_component_interactions.py` — additional *post-result* 4-factor interaction and annual/concentration diagnostics.
- `verify_interactions.py` — independent Möbius/Harsanyi verification of all 1,416 pairwise interaction values.
- `REPORT_OLC63_IT.md` — Italian narrative and interpretation.
- `results/` — original plus additional audited machine-readable outputs.

## Requirements / Re-run
Python 3.10+, NumPy, pandas, SciPy. Original checkpoints from the user Library:

```
python run_olc63.py --olc14 OLC14_Fitting_Risultati_20261101.zip \
  --olc16 OLC16_Input_Code_Checkpoint_20261102.zip \
  --olc19 OLC19_Rischio_Rientro_Checkpoint_20261102.zip \
  --out results
python verify_olc63_independent.py --olc14 OLC14_Fitting_Risultati_20261101.zip \
  --olc16 OLC16_Input_Code_Checkpoint_20261102.zip \
  --olc19 OLC19_Rischio_Rientro_Checkpoint_20261102.zip \
  --out results
python analyze_component_interactions.py
python verify_interactions.py
```

Note: `analyze_component_interactions.py` is post-result diagnostic, not a new pre-registered strategy test. The original 2019–2026 data is not a fresh independent holdout.