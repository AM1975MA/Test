#!/usr/bin/env python3
"""Research-only causal European ETF state-space vs momentum, frozen monthly opens."""
from __future__ import annotations
import argparse, hashlib, json, math, shutil, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src"),str(ROOT/"europe120/eu120_retrain")]
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from eu120_compact_return_tail_v1.run import calculate_scores
from europe_only75.refit import fixed_5050_common_open
from paper_ltr_v2.replay import sha

FEE=0.001
SEED=20261018
ARMS=("MOM_12_6_SKIP1","ROBUST_KALMAN","HALF_RANK","R_H_REFERENCE")
NAMES=ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"
RAW=ROOT/"data/eu120/raw_ticker_csv"

def momentum_score(close:pd.Series, sd:pd.Timestamp)->float:
    h=close.loc[:sd].dropna()
    h=h[h>0]
    if len(h)<253: return float("nan")
    p=h.to_numpy(float)
    z=np.diff(np.log(p[-127:]))
    vol=np.std(z,ddof=1)*np.sqrt(21.)
    if not np.isfinite(vol) or vol<0.002: return float("nan")
    # Use 6-1 and 12-1 month effects; most recent 21 closes skipped
    return float((.5*np.log(p[-22]/p[-127])+.5*np.log(p[-22]/p[-253]))/vol)

def robust_kalman_score(close:pd.Series,sd:pd.Timestamp)->tuple[float,float,float]:
    """Approximate Student-t(5) predictive filter with fixed slow/fast state diffusion."""
    h=close.loc[:sd].dropna()
    h=h[h>0]
    if len(h)<253: return (float("nan"),)*3
    mon=h.resample("ME").last().dropna()
    rr=np.diff(np.log(mon.to_numpy(float)))
    rr=rr[np.isfinite(rr)][-60:]
    if len(rr)<36: return (float("nan"),)*3
    loc=float(np.median(rr))
    # Lower variance bound avoids infinite Sharpe on near-flat stale data.
    scale=1.4826*float(np.median(np.abs(rr-loc)))
    obs_var=max(scale*scale,0.015**2)
    outputs=[]
    for ratio in (1./36.,1./9.):
        q=ratio*obs_var
        mu=0.; variance=obs_var
        loglike=0.
        for x in rr:
            predvar=variance+q
            innovation=float(x-mu)
            S=predvar+obs_var
            # t5 likelihood controls the update following price shocks.
            u=innovation*innovation/max(S,1e-12)
            weight=float(np.clip(6./(5.+u),.15,1.))
            gain=predvar/(predvar+obs_var/weight)
            mu+=gain*innovation
            variance=max((1.-gain)*predvar,1e-12)
            loglike+=-.5*np.log(S)-3.*np.log1p(u/5.)
        outputs.append((loglike,mu,variance+q))
    ll=np.array([v[0] for v in outputs])
    probs=np.exp(ll-np.max(ll));probs/=probs.sum()
    mu=float(sum(probs[i]*outputs[i][1] for i in range(2)))
    posterior_var=float(sum(probs[i]*(outputs[i][2]+(outputs[i][1]-mu)**2) for i in range(2)))
    return (mu,posterior_var,obs_var)

def stochastic_scores(close:pd.DataFrame, sd:pd.Timestamp,
                      tickers:list[str],cats:dict[str,str])->np.ndarray:
    raw=np.array([robust_kalman_score(close[t],sd) for t in tickers],float)
    mus,pvs,ovs=raw.T
    # Hierarchical within-category shrinkage: the category median is
    # an as-of cross-sectional empirical prior, not a supervised return label.
    sm=mus.copy()
    for category in sorted(set(cats.values())):
        ix=np.array([i for i,t in enumerate(tickers) if cats[t]==category and np.isfinite(mus[i])],int)
        if len(ix)<3:continue
        med=float(np.median(mus[ix]))
        disp=max((1.4826*np.median(np.abs(mus[ix]-med)))**2,0.003**2)
        w=disp/(disp+np.maximum(pvs[ix],1e-12))
        sm[ix]=w*mus[ix]+(1-w)*med
    denom=np.sqrt(np.maximum(pvs+ovs,0.015**2))
    sc=sm/denom
    sc[~np.isfinite(sc)]=np.nan
    return sc

def rank01(v:np.ndarray)->np.ndarray:
    s=pd.Series(v,dtype=float)
    return s.rank(method="average",pct=True).to_numpy(float)

def predictions(close:pd.DataFrame,cal:pd.DataFrame,tickers:list[str],
                cats:dict[str,str])->dict[str,np.ndarray]:
    scores={s:np.full((len(cal),len(tickers)),np.nan,float) for s in ARMS[:3]}
    for k,sd in enumerate(pd.to_datetime(cal.signal_date)):
        mom=np.array([momentum_score(close[t],sd) for t in tickers])
        state=stochastic_scores(close,sd,tickers,cats)
        a,b=rank01(mom),rank01(state)
        both=np.isfinite(a)&np.isfinite(b)
        mix=np.full(len(tickers),np.nan)
        mix[both]=.5*a[both]+.5*b[both]
        scores["MOM_12_6_SKIP1"][k]=a
        scores["ROBUST_KALMAN"][k]=b
        scores["HALF_RANK"][k]=mix
    return scores

def selection(score:np.ndarray,tickers:list[str],month:int,k:int=2)->list[int]:
    valid=np.isfinite(score[month])
    if valid.sum()<max(10,k):raise RuntimeError("Too few history-eligible names")
    return np.argsort(-np.where(valid,score[month],-1e12),kind="stable")[:k].tolist()

def evaluate(scores:dict[str,np.ndarray],cal:pd.DataFrame,
             tickers:list[str],op:pd.DataFrame):
    metrics=[];month_rows=[];trade_sets=[]
    monthly_log={}
    for name,score in scores.items():
        wealth=1.;prev={};path=[1.];rets=[];turns=[];sel=[]
        for m,row in enumerate(cal.itertuples(index=False)):
            ix=selection(score,tickers,m)
            names=[tickers[j] for j in ix]
            entry=pd.Timestamp(row.entry_date);exit_=pd.Timestamp(row.exit_date)
            if not (pd.Timestamp(row.signal_date)<entry<exit_):
                raise RuntimeError("Signal/trade timeline violates as-of contract")
            buy=op.loc[entry,names].to_numpy(float)
            sell=op.loc[exit_,names].to_numpy(float)
            if not (np.isfinite(buy).all() and np.isfinite(sell).all() and
                    np.all(buy>0) and np.all(sell>0)):
                raise RuntimeError(f"Missing future tradable open: {name}/{row.signal_date}")
            w=dict.fromkeys(names,.5)
            turnover=.5*sum(abs(w.get(t,0)-prev.get(t,0)) for t in set(w)|set(prev))
            gross=float(np.mean(sell/buy))
            factor=gross*(1.-FEE*turnover)
            if factor<=0:raise RuntimeError("Bad monthly economic factor")
            wealth*=factor;path.append(wealth);rets.append(np.log(factor));turns.append(turnover)
            prev=w;sel.append(tuple(names))
            valid=(np.isfinite(op.loc[entry,tickers].to_numpy(float))&
                   np.isfinite(op.loc[exit_,tickers].to_numpy(float)))
            r=op.loc[exit_,tickers].to_numpy(float)/op.loc[entry,tickers].to_numpy(float)-1.
            # Ex-post winners are ONLY used after fixed picks; never to choose.
            eligible=np.flatnonzero(valid & np.isfinite(r))
            if len(eligible)<20:raise RuntimeError("Insufficient ex-post evaluation sample")
            opportunity=float(np.max(r[eligible]))
            monthly_top1=float(r[ix[0]])
            month_rows.append(dict(policy=name,signal_date=str(pd.Timestamp(row.signal_date).date()),
                entry_date=str(entry.date()),exit_date=str(exit_.date()),top1=names[0],top2=names[1],
                gross_return=gross-1.,net_return=factor-1.,turnover=turnover,
                chosen_top1_return=monthly_top1,regret_vs_observed_expost_best=opportunity-monthly_top1,
                hit_best=int(ix[0]==int(eligible[np.argmax(r[eligible])])),
                all_eligible=int(len(eligible))))
        path=np.asarray(path);rets=np.asarray(rets);turns=np.asarray(turns)
        dd=path/np.maximum.accumulate(path)-1.
        sharpe=(rets.mean()/rets.std(ddof=1)*np.sqrt(12.)) if rets.std(ddof=1)>0 else float("nan")
        metrics.append(dict(policy=name,periods=len(rets),terminal_wealth=float(wealth),
            cagr=float(wealth**(12./len(rets))-1.),monthly_maxdd=float(dd.min()),
            monthly_sharpe=float(sharpe),mean_monthly_log_return=float(rets.mean()),
            monthly_median_net_return=float(np.median(np.expm1(rets))),
            mean_monthly_turnover=float(turns.mean()),annualized_turnover=float(turns.mean()*12),
            top1_stability=float(np.mean([sel[i][0]==sel[i-1][0] for i in range(1,len(sel))]))))
        monthly_log[name]=rets
        trade_sets.append(sel)
    return metrics,pd.DataFrame(month_rows),monthly_log

def random_reference(cal,op,tickers,scores,runs=1000):
    rng=np.random.default_rng(SEED)
    cagr=np.zeros(runs)
    for i in range(runs):
        eq=1.;prev=set()
        for m,row in enumerate(cal.itertuples(index=False)):
            # Candidate pool is defined from historical Close eligibility, not future outcomes.
            pool=np.flatnonzero(np.isfinite(scores["HALF_RANK"][m]))
            if len(pool)<10: raise RuntimeError("Null universe too small")
            k=rng.choice(pool,size=2,replace=False)
            names=[tickers[int(j)] for j in k]
            buy=op.loc[row.entry_date,names].to_numpy(float)
            sell=op.loc[row.exit_date,names].to_numpy(float)
            if not (np.isfinite(buy).all() and np.isfinite(sell).all() and
                    np.all(buy>0) and np.all(sell>0)):
                # A random sample includes untradable delisted/other names:
                # no ex-post outcome-dependent resampling allowed.
                raise RuntimeError("Null random selection lacks valid open: enforce source QA")
            overlap=len(prev & set(names))
            turn=.5 if m==0 else 1.-.5*overlap
            eq*=float(np.mean(sell/buy))*(1.-FEE*turn)
            prev=set(names)
        cagr[i]=eq**(12./len(cal))-1.
    return cagr

def bootstrap_diffs(monthly_log,rep=2000,block=12)->dict:
    rng=np.random.default_rng(SEED+1);control=monthly_log["R_H_REFERENCE"]
    n=len(control);out={}
    for name,rets in monthly_log.items():
        if name=="R_H_REFERENCE":continue
        delta=rets-control
        dist=[]
        for _ in range(rep):
            idx=[]
            while len(idx)<n:
                start=int(rng.integers(0,n))
                idx.extend([(start+j)%n for j in range(block)])
            dist.append(float(np.mean(delta[idx[:n]])))
        out[name]=dict(mean_monthly_log_excess=float(np.mean(delta)),
           ci95_monthly_log_excess=np.quantile(dist,[.025,.975]).tolist(),
           beats_model_months=int(np.count_nonzero(delta>0)),n=n)
    return out

def self_test():
    idx=pd.bdate_range("2005-01-03",periods=1600)
    sd=idx[1300]; v=np.exp(np.cumsum(np.sin(np.arange(1600)/22.)*.003+.0002))
    p=pd.Series(v,index=idx)
    a=momentum_score(p,sd); b=robust_kalman_score(p,sd)
    after=p.copy(); after.loc[after.index>sd]*=100000.
    assert np.isclose(a,momentum_score(after,sd),rtol=0,atol=0)
    assert np.allclose(b,robust_kalman_score(after,sd),rtol=0,atol=0)
    assert np.isfinite(a) and all(np.isfinite(b))
    assert len(rank01(np.array([1.,2.,np.nan])))==3
    # No future closes; no fees in the model scores.
    assert np.isnan(momentum_score(p.iloc[:40],idx[39]))
    print("STOCHASTIC_SYNTHETIC_NO_LOOKAHEAD_PASS",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--refit",required=True);p.add_argument("--oracle",required=True)
    p.add_argument("--out",required=True);a=p.parse_args()
    self_test()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    target=pd.read_csv(NAMES);tickers=target.ticker.astype(str).tolist()
    cats=dict(zip(target.ticker,target.macro_category))
    if len(tickers)!=60 or len(set(tickers))!=60:raise RuntimeError("EUR60 cohort changed")
    oracle=json.loads((Path(a.oracle)/"RESULT.json").read_text())
    ref=json.loads((Path(a.refit)/"RESULT.json").read_text())
    if (oracle["compared_months"]!=113 or oracle["source_refit_run"]!=39071370480 or
        ref["universe_count"]!=60 or not ref["training_guard_ALL_PASS"] or
        oracle["source_60_EUR_names_sha256"]!=sha(NAMES)):
        raise RuntimeError("Uncertified EU60 source")
    cal=pd.read_csv(Path(a.oracle)/"MONTHLY_ORACLE_113.csv",parse_dates=["signal_date","entry_date","exit_date"])[["signal_date","entry_date","exit_date"]]
    if len(cal)!=113 or cal.duplicated("signal_date").any():raise RuntimeError("Calendar changed")
    temp=out/"working_raw"
    temp.mkdir()
    target.to_csv(temp/"universe.csv",index=False)
    for t in tickers:shutil.copyfile(RAW/(t+".csv"),temp/(t+".csv"))
    mats,_,_=load_ticker_csv_folder(temp)
    close=mats["Close"].reindex(columns=tickers);op=mats["Open"].reindex(columns=tickers)
    if not close.index.is_monotonic_increasing:raise RuntimeError("Price order error")
    local=predictions(close,cal,tickers,cats)
    cp=pd.read_parquet(Path(a.refit)/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(Path(a.refit)/"HYBRID_REFITTED.parquet")
    for d in (cp,hp):d["signal_date"]=pd.to_datetime(d.signal_date)
    official_scores,_=calculate_scores(cp[cp.signal_date.isin(cal.signal_date)],hp[hp.signal_date.isin(cal.signal_date)],cal,tickers)
    reference=official_scores["R_H"]
    expected=float(next(z["cagr"] for z in ref["fixed_5050"] if z["variant"]=="R_H"))
    reproduced=fixed_5050_common_open(reference,cal,tickers,op)
    if abs(reproduced["cagr"]-expected)>1e-12:
        raise RuntimeError(f"Frozen baseline parity FAIL {reproduced['cagr']} != {expected}")
    print("EUR60_REFERENCE_5050_PARITY_PASS",json.dumps(reproduced),flush=True)
    local["R_H_REFERENCE"]=reference
    metrics,monthly,logs=evaluate(local,cal,tickers,op)
    random_cagr=random_reference(cal,op,tickers,local)
    random_stats=dict(n=len(random_cagr),mean_cagr=float(random_cagr.mean()),
        q05_q50_q95=np.quantile(random_cagr,[.05,.5,.95]).tolist(),
        percentile_of_candidate={m["policy"]:float(np.mean(random_cagr<m["cagr"])) for m in metrics})
    bootstrap=bootstrap_diffs(logs)
    for m in metrics:
        r=monthly[monthly.policy==m["policy"]]
        m["mean_chosen_top1_forward_return"]=float(r.chosen_top1_return.mean())
        m["mean_regret_to_expost_best"]=float(r.regret_vs_observed_expost_best.mean())
        m["hit_exact_best_rate"]=float(r.hit_best.mean())
    scores=pd.DataFrame([dict(signal_date=str(row.signal_date.date()),ticker=t,
         **{n:float(local[n][i,j]) for n in ARMS})
         for i,row in enumerate(cal.itertuples(index=False))
         for j,t in enumerate(tickers)])
    scores.to_csv(out/"MONTHLY_SCORES.csv",index=False)
    monthly.to_csv(out/"MONTHLY_TRADES.csv",index=False)
    pd.DataFrame(metrics).to_csv(out/"STRATEGY_SUMMARY.csv",index=False)
    result=dict(status="STOCHASTIC_EUR60_COMPLETED",source_pr="europe-only75",months=len(cal),
        universe_size=len(tickers),no_new_download=True,no_xgb_fit=True,
        reference_parity=True,reference_cagr=expected,
        retrospective_lookahead_universe_bias=True,
        no_production_change=True,metrics=metrics,random_null=random_stats,
        paired_12m_bootstrap=bootstrap,source_manifest_sha256=sha(ROOT/"data/eu120/manifest.json"),
        source_refit_run=39071370480,source_oracle_run=39084898663,
        model="Student-t(5) robust approximate 2-speed Kalman, category shrink, no tuning")
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("STOCHASTIC_EU60_RESULT "+json.dumps(result,allow_nan=False),flush=True)

if __name__=="__main__":main()
