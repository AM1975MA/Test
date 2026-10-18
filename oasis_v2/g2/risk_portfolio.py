#!/usr/bin/env python3
"""OASIS V2 G2 risk-only intervention: seven matched next-OPEN wealth paths.

Uses frozen OASIS *unchanged* score, never failed G1 pair forecasts.
Concentrated 2 vs 6, group diversification, fixed cash and daily
STUDENT-T portfolio expected-shortfall allocation (predeclared).
"""
from __future__ import annotations
import argparse,json,hashlib,math
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from oasis.observers import prepare,ranks
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"oasis150/results/frozen"
FEE=.001;SEED=20261018
ARMS=("R0_TWO_REFERENCE","R1_TOP6_EQUAL","R2_ONE_PER_GROUP_EQUAL",
      "R3_GROUP_INV_VOL","R4_GROUP_INV_VOL_STATIC75",
      "R5_GROUP_INV_VOL_T5ES","R6_TWO_T5ES")
GROUPS=("C01_US_BROAD_STYLE","C02_US_SECTOR_THEME","C03_DEVELOPED_GLOBAL",
        "C04_EMERGING","C05_BONDS_CASH_CREDIT","C06_REAL_ASSETS")

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def source():
    universe=pd.read_csv(BASE/"OASIS_TOP150.csv")
    a={};b={}
    for rec in universe.itertuples(index=False):
        path=ROOT/rec.source_path
        if digest(path)!=rec.source_sha256:raise AssertionError("source drift "+rec.ticker)
        z=pd.read_csv(path,parse_dates=["date"]).set_index("date").sort_index()
        a[rec.ticker]=z.Open
        b[rec.ticker]=z.Close
    op=pd.concat(a,axis=1).reindex(columns=universe.ticker.tolist())
    close=pd.concat(b,axis=1).reindex(columns=universe.ticker.tolist())
    reference=pd.read_csv(BASE/"P0_MONTHLY_GREEDY.csv",parse_dates=["day","signal_date"])
    assert len(reference)==2366 and (reference.signal_date<reference.day).all()
    assert op.loc[reference.day].notna().all().all()
    return universe,op,close,reference

def limited_weights(values,cap=.25):
    """Simple positive capped simplex: exactly 6 positive 25% max positions."""
    names=list(values)
    x=np.array([values[n] for n in names],float)
    assert (x>=0).all() and np.isfinite(x).all() and len(x)*cap>=1.
    x=x/np.sum(x)
    for _ in range(100):
        clipped=x>=cap
        if not clipped.any():break
        y=x.copy()
        y[clipped]=cap
        free=~clipped
        if not free.any():break
        remainder=1.-float(y[clipped].sum())
        y[free]=remainder*x[free]/np.sum(x[free])
        x=y
        if max(x)<=cap+1e-12:break
    if abs(sum(x)-1.)>1e-9 or max(x)>cap+1e-9:
        raise AssertionError("6-asset capped simplex failed")
    return {n:float(v) for n,v in zip(names,x)}

def risk_weights(s,score,universe,close):
    line=score.loc[s]
    ordered=sorted(line.dropna().index,key=lambda t:(-float(line[t]),str(t)))
    if len(ordered)<12:raise AssertionError("Unexpectedly insufficient history-eligible ETFs")
    topsix=ordered[:6]
    unique=[]
    for group in GROUPS:
        membership=set(universe.loc[universe.macro_category==group,"ticker"])
        match=next((t for t in ordered if t in membership),None)
        if match is None:raise AssertionError("missing ETF asset group "+group)
        unique.append(match)
    if len(set(unique))!=6:raise AssertionError("not six unique asset categories")
    hist=np.log(close[unique]/close[unique].shift(1)).loc[:s].tail(70)
    std=hist.tail(63).std(ddof=1).clip(lower=.001)
    if not np.isfinite(std).all():raise AssertionError("invalid historical vol")
    v=limited_weights({t:1/max(float(std[t]),.001) for t in unique},cap=.25)
    return {"two":dict.fromkeys(ordered[:2],.5),
        "six":dict.fromkeys(topsix,1./6.),
        "group_equal":dict.fromkeys(unique,1./6.),
        "group_invvol":v}

def student_risk_loss(ret,weights,day_index):
    """As-of conditional 10% worst scenario log loss over ~21 trading sessions."""
    names=list(weights)
    hist=ret[names].tail(126).copy()
    if len(hist)<120 or not hist.notna().all().all():
        raise AssertionError("Not enough as-of observations for ES stress")
    data=hist.to_numpy(float)
    cov=np.cov(data,rowvar=False)
    shr=.65*cov+.35*np.diag(np.diag(cov))
    chol=np.linalg.cholesky(shr+np.eye(len(names))*1e-10)
    rng=np.random.default_rng(SEED+day_index)
    Z=rng.normal(size=(384,len(names)))
    chi=rng.chisquare(5,size=384)
    # Scale variance of t5 to match empirical covariance.
    t_factor=np.sqrt(3./np.maximum(chi[:,None],1e-9))
    latent=math.sqrt(21.)*(Z*t_factor)@chol.T
    gross=np.exp(np.clip(latent,-1.5,1.5))
    w=np.array([weights[t] for t in names],float)
    loggain=np.log(np.maximum(gross@w,1e-9))
    n=max(1,math.ceil(.10*len(loggain)))
    return max(0.,-float(np.sort(loggain)[:n].mean()))

def execute_targets(shares,cash,targets,quotes):
    # Replicates audited P0 economic convention when targets={two:.5}.
    current=cash+sum(q*float(quotes[t]) for t,q in shares.items())
    if not math.isfinite(current) or current<=0:raise AssertionError("invalid wealth")
    budget=current/(1.+3*FEE)
    want={t:budget*w for t,w in targets.items()}
    turnover=0.;norders=0
    for t,q in list(shares.items()):
        px=float(quotes[t])
        if not np.isfinite(px) or px<=0:raise AssertionError("missing price on active")
        target_qty=want.get(t,0.)/px
        if q>target_qty+1e-12:
            delta=q-target_qty;val=delta*px
            cash+=val*(1-FEE);turnover+=val;norders+=1
            if target_qty<=1e-12:shares.pop(t,None)
            else:shares[t]=target_qty
    for t in targets:
        px=float(quotes[t])
        if not np.isfinite(px) or px<=0:raise AssertionError("unfillable new ETF")
        current_q=shares.get(t,0.)
        qty=want[t]/px
        if qty<=current_q+1e-12:continue
        delta=min(qty-current_q,max(cash,0.)/(px*(1+FEE)))
        if delta<=1e-12:continue
        cost=delta*px
        cash-=cost*(1+FEE);turnover+=cost;norders+=1
        shares[t]=current_q+delta
    if cash< -1e-9:raise AssertionError("leverage")
    end=cash+sum(q*float(quotes[t]) for t,q in shares.items())
    if end>current+1e-9:raise AssertionError("free money")
    return shares,max(cash,0.),turnover,current-end,norders

def summarize(table):
    w=table.wealth.to_numpy(float)
    log=np.diff(np.log(w))
    d=pd.to_datetime(table.day)
    years=(d.iloc[-1]-d.iloc[0]).days/365.25
    v=float(np.std(log,ddof=1))
    dd=float(np.min(w/np.maximum.accumulate(w)-1))
    neg=np.expm1(log)
    return dict(cagr=float((w[-1]/w[0])**(1/years)-1),
      end_wealth=float(w[-1]),daily_maxdd=dd,
      daily_sharpe=float(np.mean(log)/v*np.sqrt(252)) if v>0 else None,
      daily_es5=float(np.mean(np.sort(neg)[:math.ceil(.05*len(neg))])),
      daily_worst=float(neg.min()),
      exposure_mean=float(table.exposure.mean()),
      days_20pct_or_less=int(sum(table.exposure<=.25)),
      annual_traded_notional=float(252*np.mean(table.turnover/table.wealth)),
      fee_paid_initial_units=float(table.fee.sum()),
      n_action_days=int(table.rebalanced.sum()),
      n_risk_interventions=int(table.risk_intervention.sum()),
      holdings_count_avg=float(table.positions.mean()),
      actual_risk_series_21d_loss_max=float(table.estimated_full_ES.max()))

def simulate(arm,roster,opens,close,reference,f):
    shares={};cash=1.;last_weights={};last_exposure=None
    date_rows=[];month=None;precomputed_ret=np.log(close/close.shift(1))
    universe=roster
    for j,row in enumerate(reference.itertuples(index=False)):
        s=row.signal_date;d=row.day
        if not s<d:raise AssertionError("lookahead date")
        new_month=(month!=(d.year,d.month))
        month=(d.year,d.month)
        if new_month or not last_weights:
            candidates=risk_weights(s,f["score"],universe,close)
            if arm in ("R0_TWO_REFERENCE","R6_TWO_T5ES"):
                last_weights=candidates["two"]
            elif arm=="R1_TOP6_EQUAL":
                last_weights=candidates["six"]
            elif arm=="R2_ONE_PER_GROUP_EQUAL":
                last_weights=candidates["group_equal"]
            else:
                last_weights=candidates["group_invvol"]
        scale=1.
        full_es=0.
        intervention=False
        if arm=="R4_GROUP_INV_VOL_STATIC75":scale=.75
        elif arm in ("R5_GROUP_INV_VOL_T5ES","R6_TWO_T5ES"):
            asof_return=precomputed_ret.loc[:s]
            full_es=student_risk_loss(asof_return,last_weights,j)
            desired=float(np.clip(.08/max(.01,full_es),.20,1.))
            if new_month or last_exposure is None:
                scale=desired
            elif abs(desired-last_exposure)>=.03 or full_es*last_exposure>.12:
                scale=desired
                intervention=True
            else:scale=last_exposure
        elif arm=="R0_TWO_REFERENCE":
            scale=1.
        target={t:v*scale for t,v in last_weights.items()}
        trade=(new_month or not shares or intervention)
        quote=opens.loc[d]
        turning=0.;fee=0.;orders=0
        if trade:
            shares,cash,turning,fee,orders=execute_targets(shares,cash,target,quote)
        if new_month or intervention:last_exposure=scale
        wealth=cash+sum(q*float(quote[t]) for t,q in shares.items())
        if wealth<=0 or not math.isfinite(wealth):raise AssertionError("bad wealth")
        exposure=(wealth-cash)/wealth
        positions=len(shares)
        date_rows.append(dict(day=str(d.date()),signal_date=str(s.date()),
          arm=arm,wealth=wealth,exposure=exposure,
          actual_cash=cash/wealth,
          n_orders=orders,rebalanced=int(turning>1e-10),
          risk_intervention=int(intervention and turning>1e-10),
          turnover=turning,fee=fee,estimated_full_ES=full_es,
          positions=positions,names=";".join(shares)))
    return pd.DataFrame(date_rows)

def paired_month_bootstraps(tables,baseline="R0_TWO_REFERENCE"):
    per={}
    for arm,data in tables.items():
        g=data.copy();g["month"]=pd.to_datetime(g.day).dt.to_period("M")
        values=g.groupby("month").wealth.last().to_numpy(float)
        per[arm]=np.diff(np.log(np.r_[data.wealth.iloc[0],values]))
    n=len(per[baseline]);rng=np.random.default_rng(SEED+42)
    output={}
    for arm,r in per.items():
        if arm==baseline:continue
        delta=r-per[baseline];sims=[]
        for _ in range(1000):
            ix=[]
            while len(ix)<n:
                start=int(rng.integers(0,n))
                ix.extend((start+k)%n for k in range(12))
            sims.append(float(np.mean(delta[np.asarray(ix[:n],int)])))
        output[arm]={"mean_monthly_log_excess":float(delta.mean()),
           "ci95":np.quantile(sims,[.025,.975]).tolist(),"n_months":n}
    return output

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);arg=parser.parse_args()
    out=Path(arg.out);out.mkdir(parents=True,exist_ok=False)
    roster,op,C,reference=source()
    f=prepare(C)
    tables={}
    metrics={}
    for arm in ARMS:
        d=simulate(arm,roster,op,C,reference,f)
        d.to_csv(out/(arm+".csv"),index=False)
        tables[arm]=d
        metrics[arm]=summarize(d)
        print("G2_ARM "+arm+" "+json.dumps(metrics[arm]),flush=True)
    baseline=reference
    new=tables["R0_TWO_REFERENCE"]
    old=baseline.wealth.to_numpy(float)
    repl=new.wealth.to_numpy(float)
    parity=float(np.max(np.abs(old-repl)))
    if parity>1e-8:
        raise AssertionError(f"BASELINE R0 ECONOMIC PARITY FAILED max abs deviation={parity}")
    # Enforce exact calendar across all policy arms
    if any(len(x)!=2366 or list(x.day)!=list(new.day) for x in tables.values()):
        raise AssertionError("nonmatching calendars")
    # Gate is conservative and predeclared. No claims about FUTURE returns.
    r5=metrics["R5_GROUP_INV_VOL_T5ES"]
    r3=metrics["R3_GROUP_INV_VOL"]
    r4=metrics["R4_GROUP_INV_VOL_STATIC75"]
    tailgate=(r5["daily_maxdd"]>r3["daily_maxdd"] and
        (r5["daily_es5"]>r3["daily_es5"] or r5["daily_worst"]>r3["daily_worst"])
        and r5["cagr"]>r4["cagr"]-.025)
    result=dict(status="G2_PORTFOLIO_SPECIFIC_RISK_COMPLETED",
        G1_information_gate="FAIL_DO_NOT_TRADE_PAIRED_MODEL",
        G2_survival_exploratory_pass=bool(tailgate),
        strict_R0_daily_parity_max_error=parity,
        G2_after_observing_V1_failure=True,
        did_not_read_old_ML_predictions=True,
        model_alpha_score_unmodified=True,
        original_source_reference_run=39132785483,
        n_study_days=2366,number_of_funds=150,
        cohort_point_in_time_verified=False,
        metrics=metrics,
        monthly_paired_bootstrap=paired_month_bootstraps(tables),
        full_source_manifest_sha256=digest(BASE/"OASIS_TOP150.csv"),
        caveats=["conditional risk Student-t is a stylized scenario, not a certified safety guarantee",
            "no independent PIT holdout","0 percent zero-yield EUR cash is hypothetical",
            "underlying quote currency, fee/spread/market impact not verified"])
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("OASIS_G2_RESULT "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
