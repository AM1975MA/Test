"""Exact volume_surprise21 replay of the 48 residual formula-domain cases.
Never changes raw prices, source feature parquet, or any model.
"""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
def main():
 p=argparse.ArgumentParser()
 for x in ("r1","r2","r3","raw1","raw2","raw3","out"):p.add_argument("--"+x,required=True)
 a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 details=[];reports=[]
 for v in (1,2,3):
  d=pd.read_parquet(Path(getattr(a,f"r{v}"))/"TI_COMPACT.parquet")
  d.signal_date=pd.to_datetime(d.signal_date)
  d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  import ast
  t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
  ff=next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(k,ast.Name) and k.id=="F2D_FEATURES" for k in n.targets))
  fin=np.isfinite(d[ff].to_numpy(float));eligible=(fin.sum(axis=1)>=30)&(~fin.all(axis=1))
  subset=d.loc[eligible & d.volume_surprise21.isna(),["signal_date","ticker","volume_surprise21"]]
  root=Path(getattr(a,f"raw{v}"));cache={}
  for ticker in subset.ticker.unique():
   r=pd.read_csv(root/f"{ticker}.csv",parse_dates=["date"]).sort_values("date")
   vv=r.Volume.astype(float)
   lv=np.log(vv.where(vv>0))
   mean=lv.rolling(21,min_periods=15).mean()
   std=lv.rolling(21,min_periods=15).std(ddof=0)
   result=(lv-mean)/std.replace(0,np.nan)
   cache[ticker]=(pd.DatetimeIndex(r.date),vv.to_numpy(),lv.to_numpy(),mean.to_numpy(),std.to_numpy(),result.to_numpy())
  counts={}
  for row in subset.itertuples(index=False):
   idx,vol,lv,mean,std,calc=cache[row.ticker];pos=idx.get_indexer([row.signal_date])[0]
   if pos<0:cause="raw_date_absent"
   elif pos<14:cause="min_periods_15_not_met"
   else:
    window=lv[max(0,pos-20):pos+1]
    count=int(np.isfinite(window).sum())
    if not np.isfinite(lv[pos]):cause="current_session_volume_zero_or_invalid"
    elif count<15:cause="rolling_21_has_fewer_than_15_positive_volume_days"
    elif np.isfinite(std[pos]) and std[pos]==0:cause="exact_zero_rolling_log_volume_std"
    elif not np.isfinite(calc[pos]):cause="unexplained_after_exact_kernel_formula"
    else:cause="formula_produces_finite_but_panel_missing"
   counts[cause]=counts.get(cause,0)+1
   details.append(dict(repeat=v,ticker=row.ticker,date=str(row.signal_date.date()),cause=cause,
      prior_raw_rows=pos,volume=float(vol[pos]) if pos>=0 else None,
      positive_volume_days_21=int(np.isfinite(lv[max(0,pos-20):pos+1]).sum()) if pos>=0 else 0,
      rolling_std=float(std[pos]) if pos>=0 and np.isfinite(std[pos]) else None,
      exact_formula_value=float(calc[pos]) if pos>=0 and np.isfinite(calc[pos]) else None))
  reports.append(dict(repeat=v,missing_volume_surprise_rows=len(subset),causes=counts))
 pd.DataFrame(details).to_csv(out/"VOLUME_SURPRISE_NULL_CAUSES.csv",index=False)
 r=dict(status="EXACT_VOLUME_SURPRISE21_REPLAY",by_repeat=reports,scope="all incomplete eligible rows with missing volume_surprise21",no_training=True,no_imputation=True)
 (out/"RESULT.json").write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps(r,indent=2))
if __name__=="__main__":main()
