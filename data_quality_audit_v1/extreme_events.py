"""List all >20% daily return events in three immutable raw snapshots; no modifications."""
import argparse,collections,json
from pathlib import Path
import pandas as pd
import numpy as np

def main():
 p=argparse.ArgumentParser()
 for n in ("r1","r2","r3","out"):p.add_argument("--"+n,required=True)
 a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 rows=[]
 for i in (1,2,3):
  root=Path(getattr(a,f"r{i}"));u=pd.read_csv(root/"universe.csv")
  for t in u.ticker:
   z=pd.read_csv(root/f"{t}.csv",parse_dates=["date"],float_precision="round_trip").sort_values("date")
   z["ret"]=z.Close.pct_change(fill_method=None)
   ix=np.flatnonzero(z.ret.abs().to_numpy()>0.2)
   for k in ix:
    x=z.iloc[k];prev=z.iloc[k-1]
    rows.append(dict(ticker=t,date=str(x.date.date()),repeat=i,return_pct=float(x.ret*100),
       previous_date=str(prev.date.date()),previous_close=float(prev.Close),
       open=float(x.Open),high=float(x.High),low=float(x.Low),close=float(x.Close),volume=float(x.Volume)))
 df=pd.DataFrame(rows)
 if len(df)!=123:raise ValueError(f"Expected 123 events, found {len(df)}")
 df.sort_values(["ticker","date","repeat"]).to_csv(out/"EVENTS_ALL_SNAPSHOTS.csv",index=False)
 agg=df.groupby(["ticker","date"]).agg(repeats=("repeat","nunique"),
   min_return_pct=("return_pct","min"),max_return_pct=("return_pct","max"),
   prev_close_r1=("previous_close","first"),close_r1=("close","first")).reset_index()
 agg.to_csv(out/"UNIQUE_EVENTS.csv",index=False)
 result={"source_run":37121749852,"all_events":len(df),"unique_events":len(agg),"events_in_three_sources":int(agg.repeats.eq(3).sum()),
   "unique_tickers":int(agg.ticker.nunique()),"status":"EXTREME_RETURN_INVENTORY_COMPLETE",
   "verified_corporate_actions":0,"corrected_rows":0,"model_training":False}
 (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps(result))
 print(agg.to_string(index=False))
if __name__=="__main__":main()
