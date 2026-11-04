#!/usr/bin/env python3
"""OLC44-N4: full native OLC14->OLC16->OLC17->OLC19 dependency gate.

This is a structural provenance and readiness audit. It makes a critical
distinction between (a) source-code checkouts, (b) the large user Library
archives, and (c) actual re-trained live-era scores/portfolios.
"""
from pathlib import Path
import json
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/"results"
OUT.mkdir(exist_ok=True)

SOURCES={
"OLC14.first_stage_training":("source_olc14","research/olc14_fitted_ranking_20261101/src/train_heads.py"),
"OLC14.ranking_fusion":("source_olc14","research/olc14_fitted_ranking_20261101/src/build_scores.py"),
"OLC16.context_model":("source_olc16","research/olc16_contextual_rank_20261102/src/context_model.py"),
"OLC16.reranking":("source_olc16","research/olc16_contextual_rank_20261102/src/revalue_memory.py"),
"OLC17.V6_rebuild":("source_olc17","research/olc17_validation_20261102/src/v6_rebuild.py"),
"OLC19.risk_executor":("source_olc19","research/olc19_combined_risk_20261102/src/combined_engine.py"),
"OLC19.input_contract":("source_olc19","research/olc19_combined_risk_20261102/src/run_experiment.py"),
}

# The original source code is not enough: the original scripts refer to
# large archival binaries absent from the GitHub branch by design.
BINARY_REQUIREMENTS={
"OLC14.prepared_annual_42_feature_panels":"user Library OLC14_Heads_Checkpoint_20261101.zip",
"OLC14.original_horizon_labels_and_outputs":"user Library OLC14_Fitting_Risultati_20261101.zip",
"OLC16.reranking_priors_and_context_states":"user Library OLC16 original context checkpoint",
"OLC17.primary_and_V6_input_states":"user Library OLC17 original checkpoint",
"OLC19.original_risk_and_execution_path":"user Library OLC19_Rischio_Rientro_Checkpoint_20261102.zip",
"EXPANDED.full_42_feature_all_tickers_PIT":"NOT YET GENERATED from raw OHLC and original feature code",
"EXPANDED.target_labels_all_tickers_mature":"NOT YET RECOMPUTED for each signal date",
"EXPANDED.V6_alternative_selected_from_new_universe":"NOT YET REBUILT",
}
rows=[]
for k,(folder,p) in SOURCES.items():
    f=ROOT/folder/p
    rows.append({"kind":"CODE","requirement":k,"status":"AVAILABLE" if f.is_file() else "MISSING", "origin":str(f)})
for k,p in BINARY_REQUIREMENTS.items():
    rows.append({"kind":"BINARY_OR_GENERATED","requirement":k,"status":"NOT_PRESENT_IN_GITHUB_RUNNER","origin":p})
data=pd.DataFrame(rows)
data.to_csv(OUT/"OLC44N_FULLSTACK_DEPENDENCIES.csv",index=False)
available=sum(r["status"]=="AVAILABLE" for r in rows)
status="SOURCE_ONLY_READY_NOT_NATIVE_REFIT" if available==len(SOURCES) else "MISSING_SOURCES"
report={
    "status":status,
    "source_files_verified":available,
    "expected_source_files":len(SOURCES),
    "full_native_OOS_scores_generated":False,
    "extended_V6_rebuilt":False,
    "full_native_OLC19_economics_replayed":False,
    "new_native_CAGR":None,
    "critical_fact":"OLC19 TOP2_CONTEXT_REVALUE depends on OLC16/17 and V6 as well as OLC14 first-stage; a new score for added ETFs alone is not a native expansion.",
    "source_repository":"AM1975MA/Test",
    "expected_time_range":"2019-2026 with 2021-24 primary and untouched prospective signal vintages after frozen research",
    "next_gate":"Restore original Library binary sources in a private trusted computation environment; rebuild all 42 features and percentile targets on dated expanded roster; match original-only scores, then refit all candidates and rerun OLC19 including V6."
}
(OUT/"OLC44N_FULLSTACK_READINESS.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
if available!=len(SOURCES):
    raise RuntimeError("Full stack public source dependencies incomplete")
