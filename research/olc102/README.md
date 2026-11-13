# OLC102: Real frozen ML daily-rank recomputation

Research-only: historical in-sample/retrospective replay. Original OLC19/OLC67 unchanged. Do not send trade orders.

Steps run: build_daily_features.py (EU/USA) -> score_daily_models.py (EU/USA) -> compose_daily_rank.py (EU/USA) -> run_native_daily_rank.py -> analyze_olc102.py -> make_report.py.

Original checkpoints (not included in compact ZIP): OLC19_Rischio_Rientro_Checkpoint_20261102.zip, OLC07_Calendario_Risultati_20261101.zip, OLC08_01_Pannelli_Verificati_20261101.zip, OLC08_02_Riferimenti_Riprodotti_20261101.zip, OLC08_03_RSI_Confronto_Verificato_20261101.zip, OLC11_02_Modelli_Verificati_20261101.zip, OLC14_Heads_Checkpoint_20261101.zip, EU_Original39_RH50_Checkpoint_20261031.zip. Source paths in scripts are session-specific and should be parameterized to run in a different workspace.

Output: 76 native replay rows, 90 monthly decisions per market, 125/125 and 42/42 baseline features, 90/90 original Top2. Uncorrected paired block6 confidence intervals; no prospective proof.

Use base scorer output anchored to original OLC19 monthly score and its as-of changes (EU raw percentiles are not precisely equal due eligible support). Monthly clusters are frozen for +1/+2 closes. Revaluation contextual is updated with same annual coefficient function at as-of time. These are explicit research conventions, not a proven live-production policy.
