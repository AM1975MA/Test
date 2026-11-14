"""Execute the frozen OLC106 screen without training or parameter search."""
from pathlib import Path
import json,sys,time
import numpy as np,pandas as pd
from core import ARMS,features,simulate,portfolio_metrics
from threadpoolctl import threadpool_limits
SCENARIOS=[("BASE",1.,.0015,0),("ZERO_COST",0.,0.,0),("LOW5",1.,.0005,0),
           ("STRESS30",1.,.003,0),("LAG1",1.,.0015,1),("LAG2",1.,.0015,2)]
def load(path):
 with np.load(path,allow_pickle=False) as f:p={k:f[k] for k in f.files}
 p["dates"]=pd.DatetimeIndex(p["dates"]);p["benchmark"]=int(p["benchmark"])
 return p
def run(root,universe):
 root=Path(root);out=root/"results"/universe;out.mkdir(parents=True,exist_ok=True)
 p=load(root/"data"/(universe+".npz"));f=features(p)
 all_daily=[];all_orders=[];all_alerts=[];score=[];years=[]
 for arm in ARMS:
  for scen,ticket,impact,lag in SCENARIOS:
   r=simulate(p,arm,ticket,impact,lag,f=f)
   d=r["daily"];m=portfolio_metrics(d.nav_close,d.date,10000.,d.nav_open)
   meta=dict(universe=universe,arm=arm,scenario=scen,ticket=ticket,impact_bps=impact*10000,lag_extra=lag,
             currency="USD" if universe=="USA149" else "EUR")
   order=r["orders"]
   row={**meta,**m,"orders":len(order),"execution_days":order.date.nunique() if len(order) else 0,
       "signals":len(r["alerts"]),"costs":float(order.cost.sum()) if len(order) else 0.,
       "turnover":float(order.notional.sum()/10000.) if len(order) else 0.,
       "mean_exposure":float(d.gross.mean()),"mean_positions":float(d.positions.mean()),
       "deferred_sessions":r["deferred_sessions"],"max_self_financing_error":r["max_self_financing_error"]}
   row["target_screen_pass"]=bool(m["cagr"]>=.20 and m["maxdd_sampled"]>=-.25 and m["calmar"]>=1.)
   score.append(row)
   for name,df,collector in [("daily",d,all_daily),("orders",order,all_orders),("alerts",r["alerts"],all_alerts)]:
    if len(df):
     x=df.copy()
     for k in ["universe","arm","scenario"]:x[k]=meta[k]
     collector.append(x)
   dt=pd.to_datetime(d.date)
   for year in sorted(dt.dt.year.unique()):
    inds=np.flatnonzero(dt.dt.year.to_numpy()==year)
    init=10000. if inds[0]==0 else float(d.nav_close.iloc[inds[0]-1])
    mm=portfolio_metrics(d.nav_close.iloc[inds],d.date.iloc[inds],init,d.nav_open.iloc[inds])
    years.append({**meta,"year":int(year),"return":mm["cumulative"],"maxdd_in_year":mm["maxdd_sampled"]})
   print(universe,arm,scen,round(m["cagr"]*100,3),round(m["maxdd_sampled"]*100,3),flush=True)
 pd.DataFrame(score).to_csv(out/"SCORECARD.csv",index=False)
 pd.DataFrame(years).to_csv(out/"ANNUAL_RETURNS.csv",index=False)
 for name,ls in [("DAILY",all_daily),("ORDERS",all_orders),("ALERTS",all_alerts)]:
  pd.concat(ls,ignore_index=True).to_csv(out/(name+".csv.gz"),index=False,compression={"method":"gzip","mtime":0})
 (out/"RUN_QA.json").write_text(json.dumps({"status":"EXECUTED_RESEARCH_ONLY","paths":len(score),
  "max_accounting_error":max(x["max_self_financing_error"] for x in score),"new_training":False,
  "original_models_used":False,"physical_shares":False,"prospective":False},indent=2)+"\n")
if __name__=="__main__":
 import argparse
 a=argparse.ArgumentParser();a.add_argument("--root",required=True);a.add_argument("--universe",required=True)
 x=a.parse_args()
 with threadpool_limits(limits=1):run(x.root,x.universe)
