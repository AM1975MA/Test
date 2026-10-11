"""Read-only economic attribution of frozen V2 executed equity paths.
Partitions exact pairwise log terminal wealth gaps by contemporaneous leader
disagreement. This is association, NOT causal counterfactual attribution.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def read_run(root,alpha,repeat):
 folder=root/f"alpha-{alpha}-repeat-{repeat}"
 eqs=list(folder.rglob("FULL_UNIVERSE_PATH.npz"))
 leads=list(folder.rglob("DAILY_LEADERS.csv"))
 metrics=list(folder.rglob("RESULT.json"))
 if len(eqs)!=1 or len(leads)!=1 or len(metrics)!=1:raise RuntimeError(f"Missing replay output for {folder}")
 with np.load(eqs[0],allow_pickle=False) as z:
  dates=pd.to_datetime(z["dates"]).normalize()
  E=np.asarray(z["equity"],float).reshape(-1)
  d1=np.asarray(z["d1"]).reshape(-1);d2=np.asarray(z["d2"]).reshape(-1)
  weights=np.asarray(z["weight1"]).reshape(-1)
 l=pd.read_csv(leads[0],parse_dates=["date"]).sort_values("date").reset_index(drop=True)
 if len(dates)!=len(E) or len(dates)!=len(l):raise RuntimeError("Date or return shape mismatch")
 if not np.array_equal(dates.values.astype("datetime64[ns]"),l.date.values.astype("datetime64[ns]")):raise RuntimeError("Decision/calendar mismatch")
 if not np.isfinite(E).all() or np.any(E<=0):raise RuntimeError("Invalid portfolio path")
 j=json.loads(metrics[0].read_text())["v2_full_universe"]
 if not np.isclose(E[-1],j["terminal_equity"],rtol=1e-9):raise RuntimeError("Final capital does not match certified CAGR result")
 return dict(dates=dates,equity=E,top1=l.top1.to_numpy(str),top2=l.top2.to_numpy(str),
             weights=weights,d1=d1,d2=d2,cagr=j["cagr"],maxdd=j["maxdd"],sharpe=j["sharpe"])

def run(root,out):
 out.mkdir(parents=True,exist_ok=False)
 allpair=[];details=[];by_month=[];run_metrics=[]
 for alpha in ("0.05","1.0"):
  cache={n:read_run(root,alpha,n) for n in (1,2,3)}
  for n,r in cache.items():run_metrics.append(dict(alpha=alpha,repeat=n,cagr=r["cagr"],maxdd=r["maxdd"],sharpe=r["sharpe"],terminal_equity=float(r["equity"][-1])))
  for i,j in ((1,2),(1,3),(2,3)):
   a,b=cache[i],cache[j]
   if not a["dates"].equals(b["dates"]):raise RuntimeError(f"Different calendars alpha={alpha}, pair {i}/{j}")
   ra=np.diff(np.log(a["equity"]));rb=np.diff(np.log(b["equity"]))
   delta=ra-rb
   top1=a["top1"]!=b["top1"]
   top2=a["top2"]!=b["top2"]
   # Label the session at t by allocations at t and at previous observation.
   t1=top1[1:]|top1[:-1]
   t2=top2[1:]|top2[:-1]
   both=t1&t2
   cat=np.where(t1&~t2,"top1_only",np.where(t2&~t1,"top2_only",np.where(both,"both","neither")))
   n_sessions=len(delta)
   exactgap=float(np.log(a["equity"][-1]/b["equity"][-1])-np.log(a["equity"][0]/b["equity"][0]))
   if not np.isclose(delta.sum(),exactgap,rtol=1e-9,atol=1e-9):raise RuntimeError("Log-return telescoping failure")
   annualized_log_gap_pp=100*252*exactgap/n_sessions
   row=dict(alpha=alpha,pair=f"{i}-{j}",sessions=n_sessions,
     cagr_i=float(a["cagr"]),cagr_j=float(b["cagr"]),cagr_diff_pp=100*(a["cagr"]-b["cagr"]),
     exact_terminal_log_gap=exactgap,annualized_log_gap_pp=annualized_log_gap_pp,
     any_top1_discordant_sessions=int(t1.sum()),any_top2_discordant_sessions=int(t2.sum()),
     any_leader_discordant_sessions=int((t1|t2).sum()),
     log_gap_on_discordant=float(delta[t1|t2].sum()),
     log_gap_on_agreeing=float(delta[~(t1|t2)].sum()),
     total_abs_log_drift=float(np.abs(delta).sum()),
     abs_log_drift_discordant=float(np.abs(delta[t1|t2]).sum()),
     largest_one_session_abs_log_gap=float(np.abs(delta).max()))
   if not np.isclose(row["log_gap_on_discordant"]+row["log_gap_on_agreeing"],exactgap,atol=1e-9):raise RuntimeError("Partition closure failure")
   allpair.append(row)
   for k,(when,d,c) in enumerate(zip(a["dates"][1:],delta,cat)):
    details.append(dict(alpha=alpha,pair=f"{i}-{j}",date=str(when.date()),
      log_return_i=float(ra[k]),log_return_j=float(rb[k]),difference=float(d),
      abs_difference=float(abs(d)),decision_disagreement=c,
      top1_i=a["top1"][k+1],top1_j=b["top1"][k+1],
      top2_i=a["top2"][k+1],top2_j=b["top2"][k+1],
      weight1_i=float(a["weights"][k+1]),weight1_j=float(b["weights"][k+1])))
   df=pd.DataFrame({"month":a["dates"][1:].strftime("%Y-%m"),"gap":delta,"abs_gap":np.abs(delta),"discordant":t1|t2})
   for month,g in df.groupby("month"):
    by_month.append(dict(alpha=alpha,pair=f"{i}-{j}",month=month,days=len(g),
      net_log_gap=float(g.gap.sum()),sum_abs_log_gap=float(g.abs_gap.sum()),
      discordant_days=int(g.discordant.sum())))
 pairs=pd.DataFrame(allpair);detail=pd.DataFrame(details);months=pd.DataFrame(by_month)
 pairs.to_csv(out/"PAIRWISE_EQUITY_LOG_ATTRIBUTION.csv",index=False)
 detail.to_csv(out/"SESSION_EQUITY_LEADER_ASSOCIATION.csv",index=False)
 months.to_csv(out/"MONTHLY_EQUITY_GAP.csv",index=False)
 pd.DataFrame(run_metrics).to_csv(out/"REPLAY_METRICS_VERIFIED.csv",index=False)
 detail.sort_values("abs_difference",ascending=False).head(100).to_csv(out/"TOP_100_SESSION_GAPS.csv",index=False)
 report={"status":"SIX_FROZEN_EQUITY_PATHS_ATTRIBUTED",
  "pairwise":allpair,
  "no_causal_claim":True,
  "no_retraining":True,"source_data_unchanged":True}
 (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
 print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();run(Path(a.root),Path(a.out))
