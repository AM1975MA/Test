"""Classify residual Compact21 base-feature missingness against frozen raw source dates.
No imputation, label changes, training or model/portfolio backtests. Known precise
lookbacks inherited from earlier confirmed PR52; other lookbacks remain unproven.
"""
import json,argparse,ast
from pathlib import Path
import numpy as np,pandas as pd
KNOWN={"mom252":252,"mom252_ex21":252,"breakout_pos252":252,"ma_gap200":199,"mom126":126}
def feat():
 t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 return next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(k,ast.Name) and k.id=="F2D_FEATURES" for k in n.targets))
def run():
 p=argparse.ArgumentParser()
 for x in ("r1","r2","r3","raw1","raw2","raw3","out"):p.add_argument("--"+x,required=True)
 a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 ff=feat();basefeatures=[f for f in ff if not f.endswith(("_dev","_pct"))]
 allrows=[];summ=[];featuretot=[];incompletekeys=[]
 for i in (1,2,3):
  d=pd.read_parquet(Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet")
  d["signal_date"]=pd.to_datetime(d["signal_date"])
  d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  valid=d[ff].notna().to_numpy();elig=valid.sum(axis=1)>=30;bad=elig&~valid.all(axis=1)
  if bad.sum()!=1665:raise RuntimeError(f"unexpected incomplete set {i}: {bad.sum()}")
  incompletekeys.append(d.loc[bad,["signal_date","ticker"]].reset_index(drop=True))
  rawroot=Path(getattr(a,f"raw{i}"));cache={}
  for ticker in d.loc[bad,"ticker"].unique():
   f=rawroot/f"{ticker}.csv"
   if not f.is_file():raise RuntimeError(f"Missing frozen raw ticker: {f}")
   raw=pd.read_csv(f,parse_dates=["date"]).sort_values("date")
   if raw.date.duplicated().any():raise RuntimeError(f"raw duplicate {ticker}")
   cache[ticker]=(pd.DatetimeIndex(raw.date),raw.Close.to_numpy(dtype=float))
  for featname in basefeatures:
   mask=bad&d[featname].isna().to_numpy();n=int(mask.sum())
   if not n:continue
   per={}
   for z in np.flatnonzero(mask):
    t=d.at[z,"ticker"];dt=d.at[z,"signal_date"]
    ix,c=cache[t];pos=int(ix.get_indexer([dt])[0])
    if pos<0:cause="signal_date_missing_in_raw"
    elif not np.isfinite(c[pos]) or c[pos]<=0:cause="invalid_close_at_signal_date"
    elif featname in KNOWN:
     h=KNOWN[featname]
     if pos<h:cause="confirmed_known_lookback_insufficient"
     elif not np.isfinite(c[pos-h:pos+1]).all():cause="raw_close_missing_in_required_lookback"
     else:cause="known_window_present_but_feature_missing"
    else:
     cause="raw_close_present_other_formula_not_verified"
    per[cause]=per.get(cause,0)+1
    allrows.append(dict(repeat=i,signal_date=str(dt.date()),ticker=t,feature=featname,
      cause=cause,raw_history_bars_through_signal=pos+1 if pos>=0 else 0,
      first_raw_date=str(ix[0].date()) if len(ix) else None,
      known_prior_bars_required=KNOWN.get(featname)))
   featuretot.append(dict(repeat=i,feature=featname,missing=n,**per))
  summ.append(dict(repeat=i,eligible=int(elig.sum()),incomplete=int(bad.sum()),
      base_missing_cells=int(sum(v["missing"] for v in featuretot if v["repeat"]==i))))
 for k in (1,2):
  pd.testing.assert_frame_equal(incompletekeys[0],incompletekeys[k],check_exact=True)
 df=pd.DataFrame(allrows);df.to_csv(out/"BASE_MISSING_SOURCE_CAUSES.csv",index=False)
 pd.DataFrame(featuretot).fillna(0).to_csv(out/"FEATURE_SUMMARY.csv",index=False)
 by=df.groupby(["repeat","cause"]).size().reset_index(name="cells")
 by.to_csv(out/"CAUSE_BREAKDOWN.csv",index=False)
 result=dict(status="FROZEN_RAW_BASE_MISSING_DIAGNOSIS",summary=summ,
  classification=by.to_dict("records"),known_exact_lookbacks=KNOWN,
  precise_lookback_unverified_for_other_features=True,
  sources_unchanged=True,no_training=True)
 (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
 print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":run()
