#!/usr/bin/env python3
"""Causal Bayesian volatility regimes / multivariate Student-t tail-budget controller."""
from __future__ import annotations
import argparse,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src"),str(ROOT/"europe120/eu120_retrain")]
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from scientific_lab.models import daily_asof

FEE=.001
EXPECTED_D1=.09185988173014192
ARMS=("C0_D1_FULL","C1_D1_STATIC90","C2_D1_HMM","C3_D1_T5_CVAR","C4_D1_HMM_T5")

def filtered_hmm(daily):
    z=daily.mean(axis=1).where(daily.count(axis=1)>=10).dropna().tail(252).to_numpy(float)
    if len(z)<225:return .2
    scale=max(float(np.std(z,ddof=1)),.001)
    s0=max(.75*scale,1e-5)
    s1=max(2.25*scale,1e-5)
    prob=.2
    for x in z:
        pred=.02*(1-prob)+.91*prob
        # fixed Gaussian emissions (model simplification, not an exact financial law)
        a=(1-pred)/s0*np.exp(-.5*(x/s0)**2)
        b=pred/s1*np.exp(-.5*(x/s1)**2)
        if a+b>0:prob=float(b/(a+b))
    return prob

def predictive_cvar(daily,holdings,period_idx):
    names=list(holdings)
    a=daily[names].tail(252).to_numpy(float)
    if a.shape[0]<225:return .10
    means=np.nanmean(a,axis=0)
    if not np.isfinite(means).all():return .10
    for j in range(a.shape[1]):a[~np.isfinite(a[:,j]),j]=means[j]
    a=np.clip(a,-.08,.08)
    cov=np.cov(a,rowvar=False)
    cov=.65*cov+.35*np.diag(np.diag(cov))
    l=np.linalg.cholesky(cov+np.eye(len(names))*1e-9)
    # Scenario prediction from purely past data with mild belief shrinkage to zero.
    mu=.5*np.mean(a,axis=0)
    rng=np.random.default_rng(20261022+period_idx)
    z=rng.normal(size=(384,len(names)))
    chi=rng.chisquare(5,size=384)
    simulated=21*mu+math.sqrt(21.)*(z*np.sqrt(3/np.maximum(chi[:,None],1e-10)))@l.T
    gross=np.exp(np.clip(simulated,-1.,1.))
    w=np.array([holdings[t] for t in names],float)
    if abs(w.sum()-1)>1e-7:raise AssertionError("D1 full-weight source")
    logwealth=np.log(np.maximum(gross@w,1e-9))
    loss=-float(np.mean(np.sort(logwealth)[:max(1,math.ceil(.10*len(logwealth)))]))
    return max(loss,0.)

def economic_replay(df,scales):
    byarm={};rows={};logs={}
    for arm in ARMS:
        wealth=1.;path=[1.];prev={};log=[];turns=[];exposure=[];out=[]
        for i,p in df.iterrows():
            original=json.loads(p.holdings)
            scale=scales[arm][i]
            w={t:float(v*scale) for t,v in original.items()}
            turn=.5*sum(abs(w.get(t,0)-prev.get(t,0)) for t in set(w)|set(prev))
            if i:turn+=.5*abs((1-sum(w.values()))-(1-sum(prev.values())))
            gross=1.+scale*float(p.gross_return)
            fac=gross*(1-FEE*turn)
            if fac<=0:raise AssertionError("invalid wealth")
            wealth*=fac;path.append(wealth);log.append(math.log(fac))
            turns.append(turn);exposure.append(scale)
            out.append(dict(signal_date=p.signal_date,arm=arm,equity_exposure=scale,
                 cash=1-scale,turnover=turn,net=fac-1,holdings=json.dumps(w,sort_keys=True)))
            prev=w
        r=np.asarray(log);v=float(np.std(r,ddof=1));ret=np.expm1(r)
        eq=np.asarray(path,float)
        byarm[arm]=dict(cagr=float(wealth**(12/len(r))-1),
          terminal_wealth=float(wealth),
          monthly_maxdd=float(np.min(eq/np.maximum.accumulate(eq)-1)),
          monthly_sharpe=float(np.mean(r)/v*np.sqrt(12)) if v>0 else 0.,
          monthly_es5=float(np.mean(np.sort(ret)[:math.ceil(.05*len(ret))])),
          annual_turnover=float(np.mean(turns)*12),mean_equity_exposure=float(np.mean(exposure)),
          cash_months=int(np.sum(np.asarray(exposure)<.9999)))
        dates=pd.to_datetime(df.signal_date).dt.year
        byarm[arm]["slices"]={}
        for label,m in (("2017_2020",dates<=2020),("2021_2023",dates.between(2021,2023)),
                        ("2024_2026",dates>=2024)):
            rv=r[m.to_numpy()]
            byarm[arm]["slices"][label]=dict(n=len(rv),cagr=float(np.exp(12*np.mean(rv))-1))
        rows[arm]=out;logs[arm]=r
    return byarm,rows,logs

def bootstrap(logs,rep=1000):
    base=logs[ARMS[0]]
    n=len(base);rng=np.random.default_rng(20261024)
    results={}
    for arm in ARMS[1:]:
        delta=logs[arm]-base;draw=[]
        for _ in range(rep):
            ix=[]
            while len(ix)<n:
                t=int(rng.integers(0,n));ix.extend([(t+j)%n for j in range(12)])
            draw.append(float(np.mean(delta[np.asarray(ix[:n],int)])))
        results[arm]=dict(monthly_log_excess=float(delta.mean()),
            ci95=np.quantile(draw,[.025,.975]).tolist())
    return results

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--independent",required=True);ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    root=Path(args.independent)
    parent=json.loads((root/"RESULT.json").read_text())
    assert parent["status"]=="INDEPENDENT_STOCHASTIC_COMPLETED"
    assert parent["old_model_scores_read"] is False
    ledger=pd.read_csv(root/"MONTHLY_LEDGER.csv")
    df=ledger[ledger.policy=="D1_ROBUST_STATE"].reset_index(drop=True)
    assert len(df)==113
    roster=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    tickers=roster.ticker.astype(str).tolist()
    tmp=out/"source_temp";tmp.mkdir()
    roster.to_csv(tmp/"universe.csv",index=False)
    for t in tickers:
        shutil.copyfile(ROOT/"data/eu120/raw_ticker_csv"/(t+".csv"),tmp/(t+".csv"))
    mats,_,_=load_ticker_csv_folder(tmp)
    close=mats["Close"].reindex(columns=tickers)
    scales={arm:[] for arm in ARMS};details=[]
    for i,p in df.iterrows():
        signal=pd.Timestamp(p.signal_date)
        if not signal<pd.Timestamp(p.entry_date)<pd.Timestamp(p.exit_date):
            raise AssertionError("future timeline")
        daily=daily_asof(close,signal)
        port=json.loads(p.holdings)
        hmm=filtered_hmm(daily)
        es=predictive_cvar(daily,port,i)
        hmm_scale=.5 if hmm>.6 else 1.
        es_scale=float(np.clip(.10/max(es,.01),.5,1.))
        actions=[1.,.9,hmm_scale,es_scale,min(hmm_scale,es_scale)]
        for arm,s in zip(ARMS,actions):scales[arm].append(s)
        details.append(dict(signal_date=str(signal.date()),p_high=hmm,
             student_t_10pct_conditional_log_loss=es,
             hmm_exposure=hmm_scale,tail_budget_exposure=es_scale))
    metrics,rows,logs=economic_replay(df,scales)
    if abs(metrics["C0_D1_FULL"]["cagr"]-EXPECTED_D1)>1e-12:
        raise AssertionError(f"independent baseline parity FAIL {metrics['C0_D1_FULL']['cagr']}")
    table=pd.DataFrame([x for arm in ARMS for x in rows[arm]])
    table.to_csv(out/"MONTHLY_LEDGER.csv",index=False)
    pd.DataFrame(details).to_csv(out/"PROBABILITY_AND_TAIL_RISK.csv",index=False)
    results=dict(status="BAYESIAN_REGIME_AND_T5_TAIL_COMPLETED",
       post_selection=True, source_run=39119879600,
       uses_old_ml_predictions=False,
       causal_asof=True,months=113,
       baseline_parity=True,metrics=metrics,paired_ci=bootstrap(logs),
       high_regime_months=int(sum(x["hmm_exposure"]<1 for x in details)),
       tail_risk_reduction_months=int(sum(x["tail_budget_exposure"]<.9999 for x in details)),
       point_in_time_universe=False,independent_forward_validation=False)
    (out/"RESULT.json").write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    print("BAYESIAN_STOCHASTIC_RISK_RESULT "+json.dumps(results,allow_nan=False),flush=True)

if __name__=="__main__":main()
