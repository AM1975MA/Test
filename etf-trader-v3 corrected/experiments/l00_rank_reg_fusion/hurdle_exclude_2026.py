#!/usr/bin/env python3
"""Forward calendar year exclusion stress on matched simulated next-open NAV.

Runs on immutable job output, without recomputing or selecting models.
Past regression/calibration and policy selection used the 2018-2026 timeline,
so removing 2026 is a diagnostic, NOT a truly untouched holdout.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
POLICIES=("TOP1","TOP2","TOP3")
MODELS=("DT14_L15","HGB_REGIME_L15","RF_REGIME_L10")
def nav(df,w,arm,end):
    s=df[(df.window==w)&(df.arm==arm)&(df.date<=end)].sort_values("date")
    assert len(s)>600 and not s.date.duplicated().any()
    return s.date.to_numpy("datetime64[ns]"),s.aggregate_nav.to_numpy(float)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--incumbent",required=True)
    parser.add_argument("--candidates",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    with_confidence=[];rows=[];yearly=[]
    data={}
    data["INCUMBENT"]=pd.read_csv(Path(a.incumbent)/"DAILY_ENSEMBLE_NAV.csv",parse_dates=["date"])
    for model in MODELS:
        data[model]=pd.read_csv(Path(a.candidates)/model/"DAILY_ENSEMBLE_NAV.csv",parse_dates=["date"])
    for window in ("FULL101","MATCHED_2022"):
        for end in ("2025-12-31","2026-06-30"):
            for policy in POLICIES:
                dt,base=nav(data["INCUMBENT"],window,"TREE__"+policy,end)
                assert (dt<=np.datetime64(end)).all()
                n=len(dt)
                # Same CAGR definition as V3 source_only.statistics.metrics:
                # initial self-financing reference equity = 1.
                baseline_cagr=float(base[-1]**(252/n)-1)
                for m in MODELS:
                    d,curve=nav(data[m],window,"UTILITY__"+policy,end)
                    assert np.array_equal(dt,d),(m,window,policy,end)
                    cagr=float(curve[-1]**(252/n)-1)
                    diff=np.diff(np.log(np.r_[1.,curve]))-np.diff(np.log(np.r_[1.,base]))
                    assert len(diff)==n
                    rng=np.random.default_rng(20261024)
                    B=3000;bl=21
                    indexes=((rng.integers(0,n,size=(B,(n+bl-1)//bl))[:,:,None]
                               +np.arange(bl))%n).reshape(B,-1)[:,:n]
                    boot=diff[indexes].mean(axis=1)*252
                    alpha=float(diff.mean()*252)
                    low,high=np.quantile(boot,[.025,.975])
                    rows.append(dict(window=window,end_date=end,policy=policy,
                       model=m,n_days=n,incumbent_cagr=baseline_cagr,
                       candidate_cagr=cagr,delta_cagr=float(cagr-baseline_cagr),
                       annual_log_alpha=alpha,ci95_low=float(low),ci95_high=float(high),
                       bootstrap_day_block=bl,bootstrap_reps=B))
                for m in ["INCUMBENT"]+list(MODELS):
                    d,curve=(dt,base) if m=="INCUMBENT" else nav(data[m],window,"UTILITY__"+policy,end)
                    before=1.
                    for year,g in pd.DataFrame({"date":d,"nav":curve}).groupby(
                        pd.DatetimeIndex(d).year,sort=True):
                        close=float(g.nav.iloc[-1])
                        yearly.append(dict(window=window,end_date=end,policy=policy,
                            model=m,year=int(year),year_return=float(close/before-1)))
                        before=close
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    z=pd.DataFrame(rows)
    assert len(z)==36
    z.to_csv(out/"THROUGH_2025_VS_FULL2026.csv",index=False)
    pd.DataFrame(yearly).to_csv(out/"YEAR_BY_YEAR_PATHS.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
      evaluation_only_no_new_model=True,incumbent_run=40032693599,
      utility_economic_run=40080407962,includes_2026_vs_excludes_2026=True,
      budget_constraint=10,exact_next_open=True,
      estimator="aggregate_500_basket_NAV_with_21_trading_day_block_bootstrap",
      calendar_not_independent_holdout=True,production_changed=False),indent=2))
    print("ECONOMIC_TIME_EXCLUSION_PASS",flush=True)
    print(z[z.policy.eq("TOP2")].to_string(index=False),flush=True)
if __name__=="__main__":main()
