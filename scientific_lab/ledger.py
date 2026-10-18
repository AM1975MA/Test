"""Independent fee and cash-aware monthly trading simulator for fixed open-open calendar."""
import math
import numpy as np
import pandas as pd
from scientific_lab.models import POLICIES
FEE=.001

def evaluate(allocs,calendar,open_prices):
    scores={};logs={};rows=[]
    for policy,positions in allocs.items():
        wealth=1.;path=[wealth];prior={};rlogs=[];turns=[];exposures=[]
        for m,(period,(selected,w)) in enumerate(zip(calendar.itertuples(index=False),positions)):
            signal=pd.Timestamp(period.signal_date)
            entry=pd.Timestamp(period.entry_date);end=pd.Timestamp(period.exit_date)
            if not signal<entry<end:raise AssertionError("signal->open->open leakage")
            risk=float(sum(w.values()))
            if not (.49<=risk<=1.00000001):raise AssertionError("invalid exposure")
            buy=open_prices.loc[entry,selected].to_numpy(float)
            sell=open_prices.loc[end,selected].to_numpy(float)
            if not (np.isfinite(buy).all() and np.isfinite(sell).all() and
                    (buy>0).all() and (sell>0).all()):raise AssertionError("untradable open")
            cash=max(0.,1-risk)
            gross=cash+sum(w[t]*float(sell[j]/buy[j]) for j,t in enumerate(selected))
            risky=.5*sum(abs(w.get(t,0)-prior.get(t,0)) for t in set(w)|set(prior))
            # First month reproduces the old research convention: only buys
            # are charged 0.5x risky L1; later cash sleeve changes are counted.
            cash_turn=.5*abs(cash-(1.-sum(prior.values()))) if m else 0.
            turn=risky+cash_turn
            factor=gross*(1-FEE*turn)
            if not np.isfinite(factor) or factor<=0:raise AssertionError("bad ledger")
            wealth*=factor;path.append(wealth)
            rlogs.append(math.log(factor));turns.append(turn);exposures.append(risk)
            rows.append(dict(policy=policy,signal_date=str(signal.date()),
                entry_date=str(entry.date()),exit_date=str(end.date()),
                top1=selected[0],top2=selected[1],w1=w[selected[0]],
                w2=w[selected[1]],cash=cash,gross=gross-1,
                net=factor-1,turnover=turn))
            prior=w.copy()
        r=np.asarray(rlogs,float);rnet=np.expm1(r)
        path=np.asarray(path,float);v=float(np.std(r,ddof=1))
        scores[policy]=dict(months=len(r),cagr=float(wealth**(12/len(r))-1),
            terminal_wealth=float(wealth),
            monthly_maxdd=float(np.min(path/np.maximum.accumulate(path)-1)),
            monthly_sharpe=float(np.mean(r)/v*np.sqrt(12)) if v>0 else 0.,
            annual_turnover=float(np.mean(turns)*12),
            mean_exposure=float(np.mean(exposures)),
            cash_months=int(np.sum(np.asarray(exposures)<.9999)),
            monthly_es5=float(np.mean(np.sort(rnet)[:max(1,math.ceil(.05*len(rnet)))])),
            worst_month=float(np.min(rnet)))
        logs[policy]=r
    ledger=pd.DataFrame(rows)
    baseline=ledger[ledger.policy==POLICIES[0]].reset_index(drop=True)
    for p in POLICIES:
        group=ledger[ledger.policy==p].reset_index(drop=True)
        scores[p]["selection_match_baseline"]=float(np.mean(
            (group.top1.to_numpy()==baseline.top1.to_numpy())&
            (group.top2.to_numpy()==baseline.top2.to_numpy())))
        scores[p]["slices"]={}
        yr=group.signal_date.str[:4].astype(int)
        for label,mask in (("2017_2020",yr<=2020),("2021_2023",yr.between(2021,2023)),
                           ("2024_2026",yr>=2024)):
            x=group.loc[mask,"net"].to_numpy(float)
            scores[p]["slices"][label]=dict(n=len(x),
                cagr=float(np.prod(1+x)**(12/len(x))-1) if len(x) else None)
    return scores,ledger,logs

def circular_block_ci(logs,rep=1200,block=12):
    control=logs[POLICIES[0]];n=len(control)
    rng=np.random.default_rng(20261019)
    result={}
    for policy,values in logs.items():
        if policy==POLICIES[0]:continue
        d=values-control; draws=np.zeros(rep)
        for i in range(rep):
            ix=[]
            while len(ix)<n:
                start=int(rng.integers(0,n))
                ix.extend((start+j)%n for j in range(block))
            draws[i]=float(np.mean(d[np.asarray(ix[:n],int)]))
        result[policy]=dict(mean_monthly_log_difference=float(np.mean(d)),
          ci95=np.quantile(draws,[.025,.975]).tolist(),
          rate_months_positive=float(np.mean(d>0)))
    return result
