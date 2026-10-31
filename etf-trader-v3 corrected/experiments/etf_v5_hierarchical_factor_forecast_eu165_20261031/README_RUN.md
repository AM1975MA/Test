# ETF Trader V5 — riproduzione della ricerca EU165

## Dipendenze
Python 3.11+; numpy, pandas, scipy, scikit-learn, lightgbm, matplotlib.

## File disponibili direttamente su GitHub
- prepare_v5.py
- fit_v5.py
- evaluate_v5.py
- replay_v5.py
- diagnose_v5.py (con correzione non funzionale del refuso ROOT → R nel caricamento tassonomia)
- calibrate_v5.py
- results/PORTFOLIO_SCORECARD.csv
- results/PRE2025_PREDICTIVE_SCORECARD.csv
- results/PREQUENTIAL_CALIBRATION_SCORECARD.csv
- results/CLEAN_FACTOR_EXPERT_ABLATION_BLOCK_CI.csv
- results/SCORE_EXPERT_ABLATION_OVERLAP.csv
- results/UNCERTAINTY_DIAGNOSTIC.csv
- results/ANNUAL_LABEL_MATURITY_AUDIT.csv
- VALIDATION_GATE.json e MANIFEST.json

## Dataset, engine e output estesi
Gli input EU165 (165 file di prezzi, score nativi V2/V3, 500 panieri PIT, Open/Close) e l'engine storico originale \`source_v4/run_v4_clean.py\` sono congelati nell'archivio di ricerca \`ETF_TRADER_V5_GERARCHICA_EU165_20261031.zip\` (SHA256: \`333286dc00398f39ebcebec984919b3c0bdb2234024f12595d24b7997048b465\`).

**Il ramo GitHub non contiene i dati OHLCV né le previsioni complete**: per un replay completo estrarre lo ZIP e usare lo script al suo interno. Questi sorgenti sono l'immagine versionata dei principali script dello ZIP; sono riportati separatamente per ispezione, modifica e revisione dei difetti.

Nella cartella estratta dello ZIP eseguire in sequenza:
\`\`\`sh
python prepare_v5.py
python fit_v5.py
python evaluate_v5.py
python replay_v5.py
python diagnose_v5.py
python calibrate_v5.py
\`\`\`

Stress commissioni (convenzione 30 bps per lato):
\`\`\`sh
ONE_WAY_COST=0.003 python replay_v5.py
\`\`\`

Solo ricerca esplorativa, non per trading live. Il dataset è affetto da survivorship bias; dividendi, dati di esecuzione e spread non sono certificati. Lo storico 2018–2026 non è un holdout incontaminato.
