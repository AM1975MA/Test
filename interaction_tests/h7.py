#!/usr/bin/env python3
"""A0/A6 isolated post-selection H5 x H3 conditional 0%-yield-cash interaction."""
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
FEE=.001
ARMS=("H0","H5","H3","H7_HYSTERESIS_REGIME","H8_HYSTERESIS_STATIC90")
PARENT={"H0":.09978039091271884,"H5":.14088803144356365,"H3":.09414727156712166}

def replay(parent,flags,base,arm):
    wealth=1.;path=[wealth];prior={};logs=[];exposures=[];turns=[];rows=[]
    for i,p in parent.iterrows():
        scale=(.5 if flags[i] else 1.) if arm in ("H3","H7_HYSTERESIS_REGIME") else (
                .9 if arm=="H8_HYSTERESIS_STATIC90" else 1.)
        selected=[str(p.top1),str(p.top2)]
        weights=dict.fromkeys(selected,.5*scale)
        cash=1.-scale
        gross=1.+scale*float(p.gross)
        if gross<=0:raise AssertionError("invalid return")
        delta=.5*sum(abs(weights.get(t,0)-prior.get(t,0)) for t in set(weights)|set(prior))
        cash_turn=.5*abs(cash-(1-sum(prior.values()))) if i else 0.
        turn=delta+cash_turn
        factor=gross*(1-FEE*turn)
        wealth*=factor
        path.append(wealth);logs.append(math.log(factor))
        turns.append(turn);exposures.append(scale)
        rows.append({"signal_date":str(p.signal_date),"arm":arm,
          "top1":selected[0],"top2":selected[1],
          "exposure":scale,"cash":cash,"turnover":turn,
          "gross":gross-1,"net":factor-1})
        prior=weights
    logs=np.asarray(logs);path=np.asarray(path)
    vol=float(np.std(logs,ddof=1))
    annual={}
    years=pd.to_datetime(parent.signal_date).dt.year
    for title,mask in (("2017_2020",years<=2020),("2021_2023",years.between(2021,2023)),
                      ("2024_2026",years>=2024)):
        v=logs[np.asarray(mask,bool)]
        annual[title]={"months":len(v),"cagr":float(np.exp(12*np.mean(v))-1)}
    out=dict(cagr=float(wealth**(12/len(logs))-1),terminal_wealth=float(wealth),
       monthly_maxdd=float(np.min(path/np.maximum.accumulate(path)-1)),
       monthly_sharpe=float(np.mean(logs)/vol*np.sqrt(12)),
       monthly_es5=float(np.mean(np.sort(np.expm1(logs))[:math.ceil(.05*len(logs))])),
       mean_equity_exposure=float(np.mean(exposures)),cash_months=int(np.sum(np.array(exposures)<1)),
       annualized_turnover=float(12*np.mean(turns)),subperiods=annual)
    return out,logs,rows

def bootstrap(a,b,reps=2000,block=12):
    d=a-b;n=len(d)
    rng=np.random.default_rng(20261021);s=np.empty(reps)
    for r in range(reps):
        ix=[]
        while len(ix)<n:
            start=int(rng.integers(0,n))
            ix.extend((start+j)%n for j in range(block))
        s[r]=float(d[np.asarray(ix[:n],int)].mean())
    return dict(monthly_log_difference=float(d.mean()),
        ci95=np.quantile(s,[.025,.975]).tolist(),
        positive_month_share=float(np.mean(d>0)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--parent",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    src=Path(a.parent)
    previous=pd.read_csv(src/"MONTHLY_LEDGER.csv")
    states=json.loads((src/"MONTHLY_STATES.json").read_text())
    base=previous[previous.policy=="H0_RH_5050"].reset_index(drop=True)
    hyst=previous[previous.policy=="H5_RANK_HYSTERESIS"].reset_index(drop=True)
    flags=[bool(s["market"]["flag"]) for s in states]
    if len(flags)!=len(base)!=len(hyst) or len(flags)!=113:raise AssertionError("calendar")
    if sum(flags)!=16:raise AssertionError("risk flag source changed")
    assert (base.signal_date.to_numpy()==hyst.signal_date.to_numpy()).all()
    assert (base.signal_date.to_numpy()==np.array([s["date"] for s in states])).all()
    metrics={};log={};rows=[]
    for arm in ARMS:
        srcrow=base if arm in ("H0","H3") else hyst
        x,y,r=replay(srcrow,flags,base,arm)
        metrics[arm]=x;log[arm]=y;rows.extend(r)
        if arm in PARENT and abs(x["cagr"]-PARENT[arm])>1e-12:
            raise AssertionError(f"Parent parity fails: {arm}: {x['cagr']}")
    diffs={}
    for arm in ("H7_HYSTERESIS_REGIME","H8_HYSTERESIS_STATIC90"):
        diffs[arm]={"vs_H5":bootstrap(log[arm],log["H5"]),
                    "vs_H0":bootstrap(log[arm],log["H0"])}
    pd.DataFrame(rows).to_csv(out/"MONTHLY_LEDGER.csv",index=False)
    result=dict(status="INTERACTION_EXPLORE_COMPLETED",
        post_selection_hypothesis=True,selection_from_parent_untouched=True,
        parent_run=39089621741,parent_parity=True,months=len(base),
        market_flag_months=sum(flags),metrics=metrics,paired_bootstrap=diffs,
        data_survivorship_bias=True,independent_holdout=False,
        real_money_eligibility=False)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("INTERACTION_H7_RESULT "+json.dumps(result,allow_nan=False),flush=True)

if __name__=="__main__":main()
