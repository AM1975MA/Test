"""Classify missing long-lookback features against each vintage's actual raw ticker close history."""
import argparse,json
from pathlib import Path
import pandas as pd
import numpy as np
KEY=["signal_date","ticker"]
H={"mom252":252,"mom252_ex21":252,"breakout_pos252":252,"ma_gap200":200,"mom126":126}
def run(args):
 out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
 per=[];details=[]
 for vintage in (1,2,3):
  root=Path(getattr(args,f"r{vintage}"));raw=Path(getattr(args,f"raw{vintage}"))
  d=pd.read_parquet(root/"TI_COMPACT.parquet")
  d.signal_date=pd.to_datetime(d.signal_date)
  features=[x for x in d.columns if x not in KEY and x not in ("entry_date","exit_date") and (x in H or x.endswith(("_pct","_dev")))]
  rawrows={}
  for ticker in d.ticker.unique():
   x=pd.read_csv(raw/f"{ticker}.csv",parse_dates=["date"]).sort_values("date")
   idx=pd.DatetimeIndex(x.date)
   c=x.Close.astype(float).to_numpy()
   rawrows[ticker]=(idx,c)
  for f,h in H.items():
   sel=d.loc[d[f].isna(),["signal_date","ticker",f]]
   # restrict to rows current >=30 contract
   fcols=[c for c in d.columns if c in ["mom5","mom10","mom21","mom42","mom63","mom126","mom252","vol21","downvol21"] or c.endswith(("_pct","_dev"))]
   # Eligibility must be same source-based 125 count, not selected subset
   # Load canonical contract from kernel's AST to avoid inference mistakes
   import ast
   tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
   full=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="F2D_FEATURES" for t in n.targets))
   eligible=d[full].notna().sum(axis=1)>=30
   sel=d.loc[eligible & d[f].isna(),KEY]
   counts={"insufficient_prior_observations":0,"source_price_missing_in_required_window":0,"historical_coverage_but_feature_null":0,"signal_date_not_in_raw":0}
   for r in sel.itertuples(index=False):
    ix,c=rawrows[r.ticker]
    pos=ix.get_indexer([r.signal_date])[0]
    if pos<0: category="signal_date_not_in_raw"
    elif pos<h: category="insufficient_prior_observations"
    elif not np.isfinite(c[pos-h:pos+1]).all(): category="source_price_missing_in_required_window"
    else: category="historical_coverage_but_feature_null"
    counts[category]+=1
    details.append({"repeat":vintage,"feature":f,"signal_date":str(r.signal_date.date()),"ticker":r.ticker,"category":category})
   per.append({"repeat":vintage,"feature":f,"horizon":h,"total_missing_eligible":len(sel),**counts})
 pd.DataFrame(per).to_csv(out/"LONG_LOOKBACK_CAUSES.csv",index=False)
 pd.DataFrame(details).to_csv(out/"LONG_LOOKBACK_EXCEPTIONS.csv",index=False)
 z={"status":"RAW_WINDOW_ROOT_CAUSE_COMPLETE","lookbacks":H,"rows":per,"raw_original_snapshots_mutated":False,"model_fit":False}
 (out/"RESULT.json").write_text(json.dumps(z,indent=2)+"\n")
 for row in per:print(row)
if __name__=="__main__":
 p=argparse.ArgumentParser()
 for x in ("r1","r2","r3","raw1","raw2","raw3","out"):p.add_argument("--"+x,required=True)
 run(p.parse_args())
