"""Root-cause census for *eligible* rows missing features after downvol cleaning. No fit."""
import argparse,ast,json
from pathlib import Path
import numpy as np,pandas as pd

def main():
 p=argparse.ArgumentParser()
 for s in ("r1","r2","r3","out"):p.add_argument("--"+s,required=True)
 a=p.parse_args(); out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 source=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 feat=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="F2D_FEATURES" for t in n.targets))
 features=[];years=[];ticker=[];signatures=[];rows=[]
 for i in (1,2,3):
  d=pd.read_parquet(Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet")
  d.signal_date=pd.to_datetime(d.signal_date)
  d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  x=d[feat].astype(float)
  valid=np.isfinite(x.to_numpy(float))
  eligible=valid.sum(axis=1)>=30
  incomplete=eligible&(~valid.all(axis=1))
  signatures.append(d[["signal_date","ticker"]].assign(incomplete=incomplete,eligible=eligible))
  for j,f in enumerate(feat):
   mask=incomplete&(~valid[:,j])
   features.append(dict(repeat=i,feature=f,missing_on_eligible_incomplete=int(mask.sum()),
      missing_on_all_eligible=int((eligible&~valid[:,j]).sum()),missing_on_all_rows=int((~valid[:,j]).sum())))
  z=d[["signal_date","ticker"]].copy()
  z["incomplete"]=incomplete;z["eligible"]=eligible
  z["missing_count"]=(~valid).sum(axis=1)
  z["missing_base_count"]=(~valid[:,[j for j,f in enumerate(feat) if not f.endswith(("_pct","_dev"))]]).sum(axis=1)
  z["year"]=z.signal_date.dt.year
  z["repeat"]=i
  rows.append(z)
  for y,g in z.groupby("year"):
   years.append(dict(repeat=i,year=int(y),eligible=int(g.eligible.sum()),
      eligible_incomplete=int(g.incomplete.sum()),missing_count_sum=int(g.loc[g.incomplete,"missing_count"].sum()),
      median_missing_features=float(g.loc[g.incomplete,"missing_count"].median()) if g.incomplete.any() else 0))
  for t,g in z.groupby("ticker"):
   ticker.append(dict(repeat=i,ticker=t,eligible=int(g.eligible.sum()),
      eligible_incomplete=int(g.incomplete.sum()),first_date=str(g.signal_date.min().date()),
      first_complete_date=str(g.loc[g.eligible&~g.incomplete,"signal_date"].min().date()) if (g.eligible&~g.incomplete).any() else None))
 f=pd.DataFrame(features); y=pd.DataFrame(years);t=pd.DataFrame(ticker);r=pd.concat(rows,ignore_index=True)
 f.to_csv(out/"ELIGIBLE_INCOMPLETE_BY_FEATURE.csv",index=False)
 y.to_csv(out/"ELIGIBLE_INCOMPLETE_BY_YEAR.csv",index=False)
 t.to_csv(out/"ELIGIBLE_INCOMPLETE_BY_TICKER.csv",index=False)
 r.to_csv(out/"ROW_MISSINGNESS.csv",index=False)
 base=f[f.repeat.eq(1)].sort_values("missing_on_all_eligible",ascending=False)
 pair={}
 for ia,ib in ((0,1),(0,2),(1,2)):
  aa=signatures[ia];bb=signatures[ib]
  pd.testing.assert_frame_equal(aa[["signal_date","ticker"]],bb[["signal_date","ticker"]])
  pair[f"{ia+1}-{ib+1}"]=int((aa.incomplete.to_numpy()!=bb.incomplete.to_numpy()).sum())
 report=dict(status="RESIDUAL_NAN_ROOTCAUSE_PROFILE_COMPLETE",source_run=37936573578,
   counts=[dict(repeat=i,eligible=int(x.eligible.sum()),incomplete=int(x.incomplete.sum()),
      full_complete=int((x.eligible&~x.incomplete).sum()),
      missing_feature_values_on_incomplete=int(rows[i-1].loc[rows[i-1].incomplete,"missing_count"].sum())) for i,x in enumerate(signatures,1)],
   pairwise_incomplete_mask_changes=pair,
   worst_features=base.head(30).to_dict("records"),
   unresolved_not_yet_classified_as_broken=True,trained=False,changed_raw=False)
 (out/"RESULT.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
