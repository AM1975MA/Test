"""Independent order-level reconstruction. Does not call the strategy or its rebalance/metric helpers."""
from pathlib import Path
import json
import numpy as np,pandas as pd

def verify(root):
 root=Path(root);results=[];global_nav=0.;global_cost=0.;global_metric=0.;chronology=0
 for uni in ["EU165","USA149","TR29","EU194"]:
  with np.load(root/"data"/(uni+".npz"),allow_pickle=False) as z:p={k:z[k] for k in z.files}
  dates=pd.DatetimeIndex(p["dates"]);date_to_idx={str(x.date()):i for i,x in enumerate(dates)};names=list(map(str,p["names"]));lookup={n:i for i,n in enumerate(names)}
  seen=p["observed"].astype(bool)
  C=pd.DataFrame(np.where(seen,p["C"],np.nan)).ffill().to_numpy()
  path=root/"results"/uni
  sc=pd.read_csv(path/"SCORECARD.csv")
  daily=pd.read_csv(path/"DAILY.csv.gz")
  orders=pd.read_csv(path/"ORDERS.csv.gz")
  for row in sc.to_dict("records"):
   arm=row["arm"];scenario=row["scenario"]
   d=daily[(daily.arm==arm)&(daily.scenario==scenario)].copy()
   o=orders[(orders.arm==arm)&(orders.scenario==scenario)].copy()
   grouped={k:g.to_dict("records") for k,g in o.groupby("date",sort=False)}
   u=np.zeros(len(names));cash=10000.;calc=[];opens=[];peak=10000.;dd=0.;costsum=0.
   for bar in d.to_dict("records"):
    day=bar["date"];k=date_to_idx[day]
    op=np.where(seen[k],p["O"][k],np.nan)
    mark=np.where(np.isfinite(op),op,C[k-1])
    before=cash+np.nansum(u*mark)
    global_nav=max(global_nav,abs(before-bar["nav_open"]))
    opens.append(before)
    for trade in grouped.get(day,[]):
     j=lookup[trade["ticker"]];q=trade["quantity"];px=trade["price"]
     assert seen[k,j] and np.isfinite(p["O"][k,j]) and p["O"][k,j]>0
     assert abs(px-p["O"][k,j])<max(1e-8,abs(px)*1e-10)
     signal_k=date_to_idx[trade["signal_date"]]
     assert k>=signal_k+1+int(row["lag_extra"])
     chronology+=1
     cost=float(row["ticket"])+q*px*float(row["impact_bps"])/10000.
     global_cost=max(global_cost,abs(cost-trade["cost"]))
     costsum+=cost
     if trade["side"]=="BUY":u[j]+=q;cash-=q*px+cost
     else:u[j]-=q;cash+=q*px-cost
    assert cash> -1e-6 and u.min()> -1e-8
    value=cash+np.nansum(u*C[k]);calc.append(value)
    global_nav=max(global_nav,abs(value-bar["nav_close"]),abs(cash-bar["cash"]))
   a=np.array(calc);dc=pd.to_datetime(d.date)
   days=(dc.iloc[-1]-dc.iloc[0]).days+1
   cg=np.exp(np.log(a[-1]/10000.)*365.2425/days)-1
   sample=np.r_[10000.,np.column_stack([opens,a]).ravel()]
   running=np.maximum.accumulate(sample);md=float(np.min(sample/running-1))
   global_metric=max(global_metric,abs(cg-row["cagr"]),abs(md-row["maxdd_sampled"]))
   assert abs(costsum-row["costs"])<1e-5
   # Independent benchmark proof: one purchase at actual filled Open, then marked at final Close.
   if arm=="PASSIVE":
    assert len(o)==1 and o.iloc[0]["side"]=="BUY"
    j=lookup[o.iloc[0].ticker];expected=(10000.-row["ticket"])/(1+row["impact_bps"]/10000.)/o.iloc[0].price*C[dates.get_loc(dc.iloc[-1]),j]
    assert abs(expected-a[-1])<1e-5
   results.append(dict(universe=uni,arm=arm,scenario=scenario,nav_verified=True,costs_verified=True,
                       chronology_verified=True,independent_cagr=float(cg),independent_dd=float(md)))
 assert len(results)==120
 assert global_nav<1e-5 and global_cost<1e-7 and global_metric<1e-9
 pd.DataFrame(results).to_csv(root/"results/INDEPENDENT_RECALCULATIONS.csv",index=False)
 out=dict(status="PASS_120_ORDER_LEVEL_RECONSTRUCTIONS_RESEARCH_ONLY",paths=len(results),order_timestamps_checked=chronology,
          max_nav_cash_error=global_nav,max_per_order_cost_error=global_cost,max_metric_error=global_metric,
          generalisation_proven=False,broker_execution_certified=False,whole_shares_tested=False)
 (root/"results/INDEPENDENT_QA.json").write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps(out,indent=2))
if __name__=="__main__":
 import sys
 verify(sys.argv[1])
