"""Recompute economic paths and BASE parity for one unmodified V2 stacked replay."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from compact21_econ_layer_v1.core import VARIANT
from paper_ltr_v2.summarize_replay import metrics,checked_leaders,selections,dispersion

def annual_returns(path):
    with np.load(path,allow_pickle=False) as z:
        e=np.asarray(z["equity"],float).reshape(-1);dt=pd.to_datetime(z["dates"])
    if len(e)!=len(dt) or not np.isfinite(e).all() or (e<=0).any():
        raise ValueError("Broken equity path")
    ret=np.diff(np.log(np.r_[1.,e]))
    frame=pd.DataFrame(dict(year=dt.year,logret=ret))
    return {str(y):float(np.expm1(g.logret.sum())) for y,g in frame.groupby("year")}

def main():
    p=argparse.ArgumentParser();p.add_argument("--replays",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();root=Path(a.replays)
    metrics_by={v:[] for v in ("BASE",VARIANT)}
    leaders={v:[] for v in ("BASE",VARIANT)}
    years={v:{} for v in ("BASE",VARIANT)}
    reference_dates=None;audits=[]
    for i in (1,2,3):
        d=root/f"v2replay-{VARIANT}-r{i}"
        result=json.loads((d/"RESULT.json").read_text())
        if result.get("status")!="PAPER_LTR_V2_CACHE_REPLAY_COMPLETE" or result.get("variant")!=VARIANT or result.get("repeat")!=i:
            raise ValueError("Incomplete canonical replay")
        if result["audit"]["baseline_replay"]["PASS"] is not True or result["audit"]["input_linkage"]["PASS"] is not True:
            raise ValueError("Baseline parity or raw linkage failure")
        for name,scope,folder in [("BASE","baseline","baseline_control"),(VARIANT,"candidate","candidate")]:
            file=d/folder/"FULL_UNIVERSE_PATH.npz"
            metric,dates=metrics(file)
            if reference_dates is None:reference_dates=dates
            if not reference_dates.equals(dates):raise ValueError("Replay calendars differ")
            expected=result[scope]["v2_full_universe"]
            error=max(abs(metric[key]-float(expected[key])) for key in metric)
            if error>1e-12:raise ValueError("Nonreproducible equity metric")
            daily=checked_leaders(d/folder/"DAILY_LEADERS.csv",dates)
            leaders[name].append(daily);metrics_by[name].append(dict(vintage=i,**metric))
            years[name][str(i)]=annual_returns(file)
            audits.append(dict(vintage=i,variant=name,recomputed_abs_max_error=error,
                source_raw_parity_PASS=True,dates=len(dates)))
    summary={}
    for name in metrics_by:
        yr={str(y):float(np.mean([years[name][str(i)][str(y)] for i in (1,2,3)]))
            for y in range(2017,2027)}
        summary[name]=dict(aggregate=dispersion(metrics_by[name]),
            daily_decision_stability=selections(leaders[name]),
            per_source=metrics_by[name],yearly=years[name],year_mean=yr)
    report=dict(status="ECON_LAYER_ECONOMIC_COMPLETE",
        variant=VARIANT,results=summary,recalculation_audit=audits,
        all_three_base_parities_PASS=True,full_original149_replay=True,
        same_daily_calendar=True,original_calendar_sessions=len(reference_dates),
        source_vintages_are_correlated=True,no_production_adoption=True)
    Path(a.out).write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({name:dict(**r["aggregate"],
        top1_disagreement=r["daily_decision_stability"]["top1_any_fraction"],
        year2021=r["year_mean"]["2021"],year2023=r["year_mean"]["2023"])
        for name,r in summary.items()},indent=2),flush=True)
if __name__=="__main__":main()
