#!/usr/bin/env python3
"""OLC44-NATIVE mandatory input preflight.

Run against a separate checkout of research/olc14-fitted-ranking-20261101.
This MUST NOT claim model reproduction with only code and historical quotes:
the 42-feature panels, targets, original fitted models, and model-scale
composition baselines are required for a faithful OLC19 native extension.
"""
from __future__ import annotations
from pathlib import Path
import json, datetime
import pandas as pd
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parents[1]/"olc14_source"
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
B=OLD/"research"
S11=B/"olc11_selection_20261101"
S14=B/"olc14_fitted_ranking_20261101"
checks={
 "olc14_train_heads_code":S14/"src/train_heads.py",
 "olc14_build_scores_code":S14/"src/build_scores.py",
 "olc14_portfolio_replay_code":S14/"src/replay.py",
 "olc11_original_model_parameters":S11/"inputs/PARENT_PARAMETERS.json",
 "olc11_eu_2021_features_42_input":S11/"inputs/annual/EU_2021.joblib",
 "olc11_us_2021_features_42_input":S11/"inputs/annual/USA_2021.joblib",
 "olc11_eu_layer_labels":S11/"inputs/EU_LAYER_LABELS.csv.gz",
 "olc11_us_layer_labels":S11/"inputs/USA_LAYER_LABELS.csv.gz",
 "olc14_EU_native_parity_original_scores":S14/"results/EU_MEAN3_SCORES.csv.gz",
 "olc14_USA_native_parity_original_scores":S14/"results/USA_MEAN3_SCORES.csv.gz",
}
rows=[{"name":k,"present_in_git_checkout":v.is_file(),"relative":str(v.relative_to(ROOT.parents[1]))} for k,v in checks.items()]
df=pd.DataFrame(rows)
df.to_csv(OUT/"olc44_native_prerequisites.csv",index=False)
mandatory=["olc11_eu_2021_features_42_input",
           "olc11_us_2021_features_42_input",
           "olc11_eu_layer_labels","olc11_us_layer_labels",
           "olc14_EU_native_parity_original_scores",
           "olc14_USA_native_parity_original_scores"]
ready=all(dict(zip(df.name,df.present_in_git_checkout))[k] for k in mandatory)
result={
 "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_branch":"research/olc14-fitted-ranking-20261101",
 "input_status":"READY_FOR_REPRODUCIBLE_NATIVE_REFIT" if ready else "BLOCKED_MISSING_PREPARED_INPUTS",
 "full_native_CAGR_available":False,
 "inputs_from_persistent_library_not_automatically_in_GHA":True,
 "found_code_files":int(df.present_in_git_checkout.sum()),
 "expected_code_and_data":len(checks),
 "missing_inputs":[k for k in mandatory if not dict(zip(df.name,df.present_in_git_checkout))[k]],
 "bridge_requirement":"restore OLC14 Heads + Results archives in a private trusted runtime, then regenerate 42 inputs for the added ETFs as-of, retrain original annual heads, assert exact score parity on old tickers, then replay unchanged OLC19",
 "note":"A green CI execution denotes a successful audit, not successful native model training."
}
(OUT/"olc44_native_preflight.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
# Audit must record blocked prerequisites but not fail the archive job.
if not (S14/"src/train_heads.py").is_file():
    raise RuntimeError("Missing expected OLC14 source; preflight itself cannot be trusted")
