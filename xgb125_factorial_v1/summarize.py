"""Independently verify source-linked 2x2 economic factorial from canonical V2 equity paths."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v2.summarize_replay import metrics,checked_leaders,selections,dispersion
from xgb125_factorial_v1.core import ALL_VARIANTS,NEW_VARIANTS

def yearly_returns(path):
    with np.load(path,allow_pickle=False) as z:
        eq=np.asarray(z['equity'],float).ravel()
        dates=pd.to_datetime(z['dates'])
    if len(eq)!=len(dates) or (eq<=0).any():raise ValueError("Malformed equity")
    log=np.diff(np.log(np.concatenate([[1.],eq])))
    frame=pd.DataFrame(dict(date=dates,logret=log))
    return {str(year):float(np.expm1(g.logret.sum())) for year,g in frame.groupby(frame.date.dt.year)}

def read_variant(folder,scope,variant,repeat):
    source=folder/"RESULT.json"
    result=json.loads(source.read_text())
    if result["status"]!="PAPER_LTR_V2_CACHE_REPLAY_COMPLETE" or result["repeat"]!=repeat:
        raise ValueError("Replay incomplete: "+str(folder))
    if result["audit"]["baseline_replay"]["PASS"] is not True or result["audit"]["input_linkage"]["PASS"] is not True:
        raise ValueError("Replay baseline parity/semantic linkage failure")
    expected=result[scope]["v2_full_universe"]
    path=folder/("candidate" if scope=="candidate" else "baseline_control")/"FULL_UNIVERSE_PATH.npz"
    independently,dates=metrics(path)
    for key in independently:
        if abs(float(expected[key])-independently[key])>1e-12:
            raise ValueError(f"Recomputed metric differs: {variant} {repeat} {key}")
    leaders=checked_leaders(path.parent/"DAILY_LEADERS.csv",dates)
    return independently,leaders,yearly_returns(path),dates

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fresh",required=True);ap.add_argument("--previous",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();fresh=Path(a.fresh);previous=Path(a.previous)
    results={};final_calendar=None
    for variant in ALL_VARIANTS:
        rows=[];frames=[];years={}
        for i in (1,2,3):
            if variant=="BASE":
                path=fresh/f"v2replay-XGB_FULL_PREP-r{i}"
                scope="baseline"
            elif variant=="XGB125_MATCHED":
                path=previous/f"v2replay-XGB125_MATCHED-r{i}"
                scope="candidate"
            else:
                path=fresh/f"v2replay-{variant}-r{i}"
                scope="candidate"
            if variant!="BASE":
                reported=json.loads((path/"RESULT.json").read_text())
                if reported["variant"]!=variant:raise ValueError("Wrong variant replay")
            met,leaders,annual,dates=read_variant(path,scope,variant,i)
            if final_calendar is None:final_calendar=dates
            if not final_calendar.equals(dates):raise ValueError("Different economic calendars")
            frames.append(leaders)
            rows.append(dict(source=i,**met))
            years[str(i)]=annual
        disp=dispersion(rows);sel=selections(frames)
        annual_means={str(y):float(np.mean([years[str(i)][str(y)] for i in (1,2,3)]))
                      for y in range(2017,2027)}
        results[variant]=dict(source_metrics=rows,aggregate=disp,leader_agreement=sel,
            annual=years,annual_mean=annual_means)
    values={v:results[v]["aggregate"] for v in ALL_VARIANTS}
    effects={}
    # Scalar interactions in space of the *metric*, not in log wealth.
    for metric in ("mean_cagr","mean_maxdd","mean_sharpe","cagr_span_pp"):
        A=values["BASE"][metric];B=values["XGB_FULL_PREP"][metric]
        C=values["XGB_REDUCED_NATIVE"][metric];D=values["XGB125_MATCHED"][metric]
        effects[metric]=dict(prep_full=B-A,prep_reduced=D-C,
            train_reduced_native=C-A,train_reduced_processed=D-B,
            interaction=(D-C)-(B-A))
    output=dict(status="XGB125_FACTORIAL_ECONOMIC_COMPLETE",variants=results,
        factor_effects=effects,all_four_arms_verified=True,
        replay_full_universe_and_BASE_parity_PASS=True,
        no_new_fits_for_archived_BASE_MATCHED=True,
        independent_equity_metric_check_tolerance=1e-12,
        vintages_not_independent=True,historical_development_not_prospective=True,
        production_adoption=False)
    Path(a.out).write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=output["status"],summary={
        v:dict(**d["aggregate"],top1_disagreement=d["leader_agreement"]["top1_any_fraction"],
               year2021=d["annual_mean"]["2021"],year2023=d["annual_mean"]["2023"])
        for v,d in results.items()},factor_effects=effects),indent=2),flush=True)

if __name__=="__main__":main()
