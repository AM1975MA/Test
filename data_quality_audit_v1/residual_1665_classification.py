"""Read-only causal-eligibility census of the residual Compact21 missing cells.

Uses six independently materialized candidate panels, never alters price,
training, existing feature values, or fills missing values.
"""
import ast,argparse,json
from pathlib import Path
import pandas as pd,numpy as np

def features():
 t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 for n in t.body:
  if isinstance(n,ast.Assign) and any(isinstance(k,ast.Name) and k.id=="F2D_FEATURES" for k in n.targets):
   return ast.literal_eval(n.value)
 raise RuntimeError("F2D_FEATURES missing")

def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 ff=features();dcols=[x for x in ff if x.endswith("_dev")]
 summary=[];rows=[];causes=[];feature_counts=[]
 key_masks=[]
 for repeat in (1,2,3):
  rpanels={}
  for alpha in ("0.05","1"):
   f=root/f"alpha_{alpha}"/f"repeat_{repeat}"/"TI_COMPACT.parquet"
   if not f.is_file():raise RuntimeError(f"Missing frozen candidate panel: {f}")
   df=pd.read_parquet(f).sort_values(["signal_date","ticker"]).reset_index(drop=True)
   assert df[["signal_date","ticker"]].notna().all().all()
   assert not df.duplicated(["signal_date","ticker"]).any()
   rpanels[alpha]=df
  base=rpanels["0.05"];other=rpanels["1"]
  pd.testing.assert_frame_equal(base[["signal_date","ticker"]],other[["signal_date","ticker"]],check_exact=True)
  assert (base[ff].notna().to_numpy()==other[ff].notna().to_numpy()).all(),"alpha changed missing mask"
  candidate=base
  finite=np.isfinite(candidate[ff].to_numpy(dtype=float))
  eligible=finite.sum(axis=1)>=30
  incomplete=eligible&~finite.all(axis=1)
  assert eligible.sum()==34876 and incomplete.sum()==1665 and int(finite.all(axis=1).sum())==33211,(repeat,eligible.sum(),incomplete.sum())
  key_masks.append(candidate.loc[incomplete,["signal_date","ticker"]].reset_index(drop=True))
  counts=candidate.loc[incomplete,ff].isna().sum(axis=1)
  def family(f):
   if f.endswith("_dev"):return "cross_sectional_dev"
   if f.endswith("_pct"):return "cross_sectional_percentile"
   return "base_or_other"
  nmissing=0
  for f in ff:
   mask=incomplete&candidate[f].isna().to_numpy()
   n=int(mask.sum());nmissing+=n
   if not n:continue
   feature_counts.append({"repeat":repeat,"feature":f,"family":family(f),"missing_cells":n,"missing_rows":n})
   if f.endswith("_dev"):
    b=f[:-4];origin="missing_underlying_base" if b in candidate.columns else "base_column_unavailable"
    # Retain all cases in a per-cell classification, not only counts.
    for idx in np.flatnonzero(mask):
     why=("missing_underlying_base" if b in candidate and pd.isna(candidate.at[idx,b]) else "dev_transform_unresolved")
     causes.append({"repeat":repeat,"signal_date":str(candidate.at[idx,"signal_date"]),"ticker":candidate.at[idx,"ticker"],
         "feature":f,"cause":why,"underlying_feature":b})
   elif f.endswith("_pct"):
    b=f[:-4]
    for idx in np.flatnonzero(mask):
     why=("missing_underlying_base" if b in candidate and pd.isna(candidate.at[idx,b]) else "pct_transform_or_unclassified")
     causes.append({"repeat":repeat,"signal_date":str(candidate.at[idx,"signal_date"]),"ticker":candidate.at[idx,"ticker"],
         "feature":f,"cause":why,"underlying_feature":b})
   else:
    for idx in np.flatnonzero(mask):
     causes.append({"repeat":repeat,"signal_date":str(candidate.at[idx,"signal_date"]),"ticker":candidate.at[idx,"ticker"],
         "feature":f,"cause":"base_missing_unclassified_source_vs_lookback","underlying_feature":f})
  firstgood=candidate.groupby("ticker",sort=False)["signal_date"].min()
  # Observation position in PANEL, NOT verified raw OHLCV inception or full lookback.
  position=candidate.groupby("ticker",sort=False).cumcount()
  for idx in np.flatnonzero(incomplete):
   rows.append({"repeat":repeat,"ticker":candidate.at[idx,"ticker"],"signal_date":str(candidate.at[idx,"signal_date"]),
    "missing_features":int(counts.loc[idx]),"available_features":int(finite[idx].sum()),
    "panel_observation_index":int(position.iloc[idx]),
    "first_panel_date":str(firstgood.loc[candidate.at[idx,"ticker"]])})
  summary.append({"repeat":repeat,"eligible":int(eligible.sum()),"complete":int(finite.all(axis=1).sum()),
    "remaining_incomplete":int(incomplete.sum()),"missing_cells_residual":nmissing,
    "missing_feature_columns":int(sum(x["repeat"]==repeat for x in feature_counts)),
    "missing_cells_per_incomplete_row_mean":float(counts.mean()),"missing_cells_per_incomplete_row_max":int(counts.max())})
 for v in (1,2):
  pd.testing.assert_frame_equal(key_masks[0],key_masks[v],check_exact=True)
 fc=pd.DataFrame(feature_counts)
 cc=pd.DataFrame(causes)
 breakdown=cc.groupby(["repeat","cause"]).size().reset_index(name="missing_cells")
 fc.to_csv(out/"MISSING_FEATURE_COUNTS.csv",index=False)
 cc.to_csv(out/"MISSING_CELL_CAUSES.csv",index=False)
 pd.DataFrame(rows).to_csv(out/"INCOMPLETE_ROWS_WITH_PANEL_AGE.csv",index=False)
 breakdown.to_csv(out/"CAUSE_BREAKDOWN.csv",index=False)
 report={"status":"RESIDUAL_1665_CLASSIFIED_AT_FEATURE_DEPENDENCY_LEVEL",
 "summary":summary,"causes":breakdown.to_dict(orient="records"),
 "all_three_incomplete_row_keys_identical":True,
 "limitations":["A missing base feature is not yet proven to be lookback rather than source hole",
 "Panel index is not ticker raw OHLCV age","Full upstream Tail, MA3, Macro inputs not certified"],
 "no_fill":True,"no_training":True}
 (out/"RESULT.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
