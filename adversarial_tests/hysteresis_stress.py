#!/usr/bin/env python3
"""A7 adversarial validation: fee stress, year dominance, frozen-score perturbation."""
import argparse,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src"),str(ROOT/"europe120/eu120_retrain")]
from etf_trader.source_only.raw_io import load_ticker_csv_folder

FEE=.001
SEED=20261020

def top5(x):
    v=np.asarray(x,float)
    if np.isfinite(v).sum()<5:raise AssertionError("less than 5 eligible")
    return np.argsort(-np.where(np.isfinite(v),v,-1e20),kind="stable")[:5]

def play(scores,cal,names,opens,hyst,fee=FEE):
    wealth=1.;prior={};held=[];deltas=[]
    for i,p in enumerate(cal.itertuples(index=False)):
        rank=[names[z] for z in top5(scores[i])]
        if hyst and held:
            old=[t for t in held if t in rank]
            selected=(old+[t for t in rank if t not in old])[:2]
        else:selected=rank[:2]
        buy=opens.loc[p.entry_date,selected].to_numpy(float)
        sell=opens.loc[p.exit_date,selected].to_numpy(float)
        if not (np.isfinite(buy).all() and np.isfinite(sell).all()
          and (buy>0).all() and (sell>0).all()):raise AssertionError("bad open")
        w={selected[0]:.5,selected[1]:.5}
        turn=.5*sum(abs(w.get(t,0)-prior.get(t,0)) for t in set(w)|set(prior))
        f=float(np.mean(sell/buy))*(1-fee*turn)
        if f<=0:raise AssertionError("bad factor")
        wealth*=f;deltas.append(math.log(f))
        prior=w;held=selected
    return float(wealth**(12/len(cal))-1),np.asarray(deltas,float)

def costs(ledger):
    baseline=ledger.loc[ledger.policy=="H0_RH_5050"].reset_index(drop=True)
    hyst=ledger.loc[ledger.policy=="H5_RANK_HYSTERESIS"].reset_index(drop=True)
    if len(baseline)!=len(hyst):raise AssertionError("calendar misalignment")
    out={}
    for fee in (0.,.001,.005,.01):
        metrics={}
        for tag,g in (("base",baseline),("hyst",hyst)):
            factors=(1+g.gross.to_numpy(float))*(1-fee*g.turnover.to_numpy(float))
            metrics[tag]=float(np.prod(factors)**(12/len(factors))-1)
        metrics["cagr_gap_percentage_points"]=100*(metrics["hyst"]-metrics["base"])
        out[str(fee)]=metrics
    ln=np.log1p(hyst.net.to_numpy(float))-np.log1p(baseline.net.to_numpy(float))
    years=pd.to_datetime(hyst.signal_date).dt.year.to_numpy()
    annual={}
    for y in sorted(set(years)):
        d=ln[years==y]
        annual[str(y)]={"months":len(d),"monthly_log_delta_sum":float(d.sum()),
            "annualized_relative_growth":float(np.exp(12*d.mean())-1)}
    loo={}
    for y in sorted(set(years)):
        d=ln[years!=y]
        loo[str(y)]=float(np.exp(12*d.mean())-1)
    highest=np.sort(ln)[::-1]
    negative=np.sort(ln)
    return {"fee_sensitivity":out,"annual_attribution":annual,
        "leave_one_year_out_ann_relative_advantage":loo,
        "months_benefiting":int(np.sum(ln>0)),"months_hurt":int(np.sum(ln<0)),
        "zero_effect_months":int(np.sum(np.isclose(ln,0,atol=1e-15))),
        "top3_month_positive_log_gains":float(highest[:3].sum()),
        "total_log_gains":float(ln.sum()),
        "worst3_month_negative_log_deltas":float(negative[:3].sum()),
        "month_log_delta_std":float(np.std(ln,ddof=1))}

def perturb(scores,cal,names,opens):
    original_base,_=play(scores,cal,names,opens,False)
    original_hyst,_=play(scores,cal,names,opens,True)
    levels={}
    for frac in (.001,.01):
        rnd=np.random.default_rng(SEED)
        rows=[]
        for trial in range(30):
            x=scores.copy()
            for i in range(x.shape[0]):
                sel=np.isfinite(x[i])
                sigma=float(np.std(x[i,sel]))
                x[i,sel]+=frac*max(sigma,1e-12)*rnd.normal(size=sel.sum())
            b,_=play(x,cal,names,opens,False)
            h,_=play(x,cal,names,opens,True)
            rows.append((b,h,h-b))
        y=np.array(rows,float)
        levels[str(frac)]={"n":len(y),
            "hysteresis_cagr_median":float(np.median(y[:,1])),
            "hysteresis_cagr_min":float(np.min(y[:,1])),
            "hysteresis_cagr_max":float(np.max(y[:,1])),
            "gap_pp_p05_p50_p95":(100*np.quantile(y[:,2],[.05,.5,.95])).tolist(),
            "fraction_hysteresis_beats_perturbed_base":float(np.mean(y[:,2]>0))}
    return {"unperturbed_base_cagr":original_base,
            "unperturbed_hysteresis_cagr":original_hyst,
            "perturbation_fraction_score_std":levels,
            "scope":"score-jitter-only; NOT Yahoo vintage/OHLC data revisions"}

def main():
    parser=argparse.ArgumentParser()
    for name in ("ledger","stoch","oracle","out"):parser.add_argument("--"+name,required=True)
    a=parser.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    ledger=pd.read_csv(Path(a.ledger)/"MONTHLY_LEDGER.csv")
    assert len(ledger)==113*7
    c=costs(ledger)
    roster=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    names=roster.ticker.astype(str).tolist()
    cal=pd.read_csv(Path(a.oracle)/"MONTHLY_ORACLE_113.csv",
        parse_dates=["signal_date","entry_date","exit_date"])[
        ["signal_date","entry_date","exit_date"]]
    data=pd.read_csv(Path(a.stoch)/"MONTHLY_SCORES.csv")
    score=data.pivot(index="signal_date",columns="ticker",
        values="R_H_REFERENCE").reindex(index=cal.signal_date.dt.strftime(
        "%Y-%m-%d"),columns=names).to_numpy(float)
    temp=out/"temp";temp.mkdir()
    roster.to_csv(temp/"universe.csv",index=False)
    for t in names:shutil.copyfile(
        ROOT/"data/eu120/raw_ticker_csv"/(t+".csv"),temp/(t+".csv"))
    mats,_,_=load_ticker_csv_folder(temp)
    opens=mats["Open"].reindex(columns=names)
    p=perturb(score,cal,names,opens)
    if not (abs(p["unperturbed_base_cagr"]-.09978039091271884)<1e-12 and
            abs(p["unperturbed_hysteresis_cagr"]-.14088803144356365)<1e-12):
        raise AssertionError("adversarial simulator fails frozen parity")
    result=dict(status="ADVERSARIAL_A7_FINISHED",source_run=39089621741,
       fee_cost_stress=c,score_jitter_robustness=p,
       hindsight_selected_universe=True,untouched_forward_holdout=False,
       deployable_edge_proven=False)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("HYSTERESIS_ADVERSARIAL_RESULT "+json.dumps(result,allow_nan=False),flush=True)

if __name__=="__main__":main()
