#!/usr/bin/env python3
"""V3 future-return regret utility: quarterly mature-only hurdle tree evaluation.

Precommitted 4 predictors x 2 aversion levels, no parameter tuning on 2018-26
results. Target is the loss/benefit of switching ETF within original rank Top3.
The user-visible evaluation calendar has been researched; THIS IS NOT A VIRGIN
OOS HOLDOUT. Frozen first-stage OOS predictions, canonical 500 overlapping
baskets and original next-open 21 trading-day realized targets.

Hurdle model: classifier p(win) and separate strictly-positive and negative
conditional payoff models. Predict *utility* =
      p(win)*E[positive spread] - risk_penalty*(1-p(win))*E[loss] - switch_cost
No switch unless utility > 0. Model refits quarterly on <= t-60d monthly
signals; unique ordered ETF pair per month with equal total calendar-month
sample weight. Runtime price features from OHLCV CLOSE prices <= signal date.
"""
from __future__ import annotations
import argparse, json, hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier,DecisionTreeRegressor
from sklearn.ensemble import (
    HistGradientBoostingClassifier,HistGradientBoostingRegressor,
    RandomForestClassifier,RandomForestRegressor)
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[1]/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder
from parallel_meta import load,pair_features,REGS,METRICS
from aggregate import read_shards,metric_for_order

FAMILIES=("DT14","DT_REGIME","HGB_REGIME","RF_REGIME")
RISK=(1.,1.5)
EXTRA_SWITCH_COST=.002  # Fixed economic penalty: NOT actual portfolio fees.
TARGET_CLIP=.20
SOURCE_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def make_models(family):
    core=family.split("_")[0]
    if core=="DT":
        kw=dict(max_depth=3,min_samples_leaf=100,random_state=20261024)
        return (DecisionTreeClassifier(criterion="log_loss",**kw),
                DecisionTreeRegressor(**kw),DecisionTreeRegressor(**kw))
    if core=="HGB":
        kw=dict(max_iter=100,learning_rate=.045,max_leaf_nodes=7,min_samples_leaf=100,
                l2_regularization=20,early_stopping=False,random_state=20261024)
        return (HistGradientBoostingClassifier(**kw),
                HistGradientBoostingRegressor(**kw),
                HistGradientBoostingRegressor(**kw))
    if core=="RF":
        kw=dict(n_estimators=100,max_depth=6,min_samples_leaf=65,
                max_features=.8,n_jobs=2,random_state=20261024)
        return (RandomForestClassifier(**kw),
                RandomForestRegressor(**kw),RandomForestRegressor(**kw))
    raise ValueError(family)

def source_tickers(scores,dates):
    wide=scores.pivot(index=["signal_date","ticker"],columns="variant",values="pred")
    y=scores[scores.variant.eq("CORRECTED")].set_index(["signal_date","ticker"]).fwd_ret_21
    wide=wide.join(y)
    out={}
    for dt in dates:
        g=wide.loc[dt].dropna(subset=["CORRECTED","fwd_ret_21"]+list(REGS)).sort_index()
        out[dt]=list(g.index)
    return out

def trailing(close,dates,tickers):
    res={}
    for dt in dates:
        historical=close.loc[close.index<=dt]
        assert len(historical)>=75 and historical.index.max()<=dt
        # Use the same price lookback for every ticker and explicitly avoid
        # future rows; stale price treatment only forward fills from past.
        x=historical.ffill()
        now=x.iloc[-1];p21=x.iloc[-22];p63=x.iloc[-64]
        r21=(now/p21-1).replace([np.inf,-np.inf],np.nan)
        r63=(now/p63-1).replace([np.inf,-np.inf],np.nan)
        vol=(x.pct_change(fill_method=None).iloc[-21:].std()*np.sqrt(252))
        dd=(now/x.iloc[-63:].max()-1)
        spy21=float(r21["SPY"]);spy63=float(r63["SPY"])
        assert np.isfinite([spy21,spy63]).all()
        allr21=r21.dropna();allr63=r63.dropna()
        b21=float((allr21>0).mean());b63=float((allr63>0).mean())
        disp21=float(allr21.std());disp63=float(allr63.std())
        vglobal=float(vol.dropna().median())
        fields={}
        for name in tickers[dt]:
            a=[r21.get(name,np.nan),r63.get(name,np.nan),
               vol.get(name,np.nan),dd.get(name,np.nan)]
            if not np.isfinite(a).all():
                raise RuntimeError(f"Missing AS-OF 21/63d price feature for {name} {dt}: {a}")
            fields[name]=np.array(a,float)
        glob=np.array([b21,b63,disp21,disp63,vglobal,spy21,spy63],float)
        assert np.isfinite(glob).all()
        res[dt]=(fields,glob,historical.index.max())
    return res

def enrich(base,v,idx,orig,alt,local,names,with_regime):
    core=pair_features(v,idx,orig,alt)
    if not with_regime:return core
    fields,glob,asof_date=local
    ticker0=names[int(idx[orig[0]])];tickera=names[int(idx[alt])]
    x0=fields[ticker0];xa=fields[tickera]
    # Four exact rolling price contrasts, two recent alternative levels, and
    # seven market-wide regime signals, totaling 13 additional features.
    return core+list(xa-x0)+[float(xa[0]),float(xa[1])]+list(glob)

def training(months,tickers,causal):
    allmonth=[]
    for dt,v,baskets in months:
        seen={}
        names=tickers[dt]
        for idx,orig in baskets:
            first=int(idx[orig[0]])
            for alt in orig[1:3]:
                target=int(idx[alt])
                pair=(first,target)
                if pair not in seen:
                    delta=float(v["fwd"][target]-v["fwd"][first])
                    f14=enrich(None,v,idx,orig,alt,causal[dt],names,False)
                    f27=enrich(None,v,idx,orig,alt,causal[dt],names,True)
                    seen[pair]=(f14,f27,float(np.clip(delta,-TARGET_CLIP,TARGET_CLIP)))
        x14=np.array([row[0] for row in seen.values()],float)
        x27=np.array([row[1] for row in seen.values()],float)
        y=np.array([row[2] for row in seen.values()],float)
        assert x14.shape[1]==14 and x27.shape[1]==27 and len(y)>100
        assert np.isfinite(x27).all() and np.isfinite(y).all()
        allmonth.append((dt,x14,x27,y))
    return allmonth

def make_metrics(v,baskets,tickers,causal,dt):
    features14=[];features27=[];triples=[];keypairs=[];origin=[]
    names=tickers[dt]
    for basketid,(idx,orig) in enumerate(baskets):
        outcomes=v["fwd"][idx]
        baseline=metric_for_order(orig,outcomes)[:6]
        row=[baseline]
        for alt in orig[1:3]:
            neworder=np.concatenate(([alt],orig[orig!=alt]))
            row.append(metric_for_order(neworder,outcomes)[:6])
            features14.append(enrich(None,v,idx,orig,alt,causal[dt],names,False))
            features27.append(enrich(None,v,idx,orig,alt,causal[dt],names,True))
            keypairs.append((names[int(idx[orig[0]])],names[int(idx[alt])]))
        origin.append(names[int(idx[orig[0]])])
        triples.append(row)
    x14=np.asarray(features14,float);x27=np.asarray(features27,float)
    zz=np.asarray(triples,float)
    assert x14.shape==(1000,14) and x27.shape==(1000,27) and zz.shape==(500,3,6)
    return x14,x27,zz,keypairs,origin

def train_hurdle(family,history):
    X=np.concatenate([r[1 if family=="DT14" else 2] for r in history])
    delta=np.concatenate([r[3] for r in history])
    # Unit weight per distinct ETF pair within a given signal month; each
    # mature calendar month has identical *aggregate* training weight.
    w=np.concatenate([np.full(len(r[3]),1./len(r[3])) for r in history])
    w=w*len(w)/len(history)
    pos=delta>0
    assert pos.sum()>200 and (~pos).sum()>200
    pmodel,gmodel,lmodel=make_models(family)
    pmodel.fit(X,pos.astype(int),sample_weight=w)
    gmodel.fit(X[pos],delta[pos],sample_weight=w[pos])
    lmodel.fit(X[~pos],-delta[~pos],sample_weight=w[~pos])
    return pmodel,gmodel,lmodel,len(X),float(pos.mean())

def infer(models,x):
    if models is None:return np.full((len(x),3),np.nan)
    prob,gm,lm=models[:3]
    classes=list(prob.classes_)
    assert 1 in classes
    p=np.clip(prob.predict_proba(x)[:,classes.index(1)],0,1)
    pos=np.clip(gm.predict(x),0,TARGET_CLIP)
    neg=np.clip(lm.predict(x),0,TARGET_CLIP)
    assert np.isfinite([p,pos,neg]).all()
    return np.column_stack([p,pos,neg])

def bootstrap_by_month(monthly,comparison,seed=20261024,reps=3000):
    dates=sorted(monthly.signal_date.unique());n=len(dates)
    idx=((np.random.default_rng(seed).integers(0,n,size=(reps,(n+5)//6))[:,:,None]
          +np.arange(6))%n).reshape(reps,-1)[:,:n]
    lines=[]
    for arm in sorted(set(monthly.variant)-{"CORRECTED"}):
        panel=monthly[monthly.variant.eq(arm)].sort_values("signal_date")
        assert list(panel.signal_date)==dates
        for refname,ref in comparison.items():
            rr=ref.sort_values("signal_date")
            assert list(rr.signal_date)==dates
            for k in ("basket_selected_excess","basket_top1","basket_loss10_top1"):
                dx=(panel[k].to_numpy()-rr[k].to_numpy())
                bt=dx[idx].mean(axis=1)
                lines.append(dict(variant=arm,reference=refname,metric=k,
                    mean_delta=float(dx.mean()),ci025=float(np.quantile(bt,.025)),
                    ci975=float(np.quantile(bt,.975)),replicates=reps,calendar_block=6))
    return pd.DataFrame(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=FAMILIES,required=True)
    p.add_argument("--shards",required=True)
    p.add_argument("--raw",required=True)
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--incumbent",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SOURCE_SHA
    months,ref=load(a.shards,a.baskets)
    scores,_,_=read_shards(a.shards,"regression")
    dates=[dt for dt,_,_ in months]
    names=source_tickers(scores,dates)
    assert len(set(name for v in names.values() for name in v))==149
    assert all(len(x)==149 for x in names.values())
    price,categories,_=load_ticker_csv_folder(a.raw)
    assert len(categories)==149 and set(names[dates[0]])==set(categories)
    close=price["Close"]
    causal=trailing(close,dates,names)
    prepared=training(months,names,causal)
    incumbent=pd.read_csv(Path(a.incumbent)/"NESTED_MONTHLY.csv",parse_dates=["signal_date"])
    incumbent=incumbent[incumbent.strategy.eq("NESTED_24_TOP1_GUARD")].sort_values("signal_date").reset_index(drop=True)
    assert len(incumbent)==101 and list(incumbent.signal_date)==dates
    original=ref[ref.variant.eq("CORRECTED")].sort_values("signal_date").reset_index(drop=True)
    assert list(original.signal_date)==dates
    arms=[f"UTILITY_{a.family}_L{r:g}" for r in RISK]
    output=[];corrections=[];audit=[];events=[]
    current_quarter=None; fitted=None
    for i,(dt,v,baskets) in enumerate(months):
        quarter=(dt.year,(dt.month-1)//3)
        if quarter!=current_quarter:
            eligible=[row for row in prepared if row[0]<dt-pd.Timedelta(days=60)]
            if len(eligible)>=24:
                fitted=train_hurdle(a.family,eligible)
                audit.append(dict(first_signal=str(dt.date()),family=a.family,
                    trained_from=str(eligible[0][0].date()),
                    trained_until=str(eligible[-1][0].date()),
                    mature_history_months=len(eligible),distinct_pair_months=fitted[3],
                    positive_event_rate=fitted[4],asof_cutoff=str((dt-pd.Timedelta(days=60)).date())))
            else:fitted=None
            current_quarter=quarter
        x14,x27,choices,pairs,base_symbols=make_metrics(v,baskets,names,causal,dt)
        x=x14 if a.family=="DT14" else x27
        pp=infer(fitted,x).reshape(500,2,3)
        assert np.isfinite(choices).all()
        if i==0:
            print("CAUSAL_FEATURE_TEST",str(dt.date()),
              "latest_close",str(causal[dt][2].date()),"n_features",x.shape[1],flush=True)
        baseline=choices[:,0,:]
        baseline_row=dict(variant="CORRECTED",signal_date=dt,year=dt.year,n_baskets=500)
        baseline_row.update({k:float(baseline[:,j].mean()) for j,k in enumerate(METRICS)})
        output.append(baseline_row)
        for risk,arm in zip(RISK,arms):
            if fitted is None:option=np.zeros(500,dtype=int);utilities=np.full((500,2),-np.inf)
            else:
                utilities=(pp[:,:,0]*pp[:,:,1]
                  -risk*(1-pp[:,:,0])*pp[:,:,2]-EXTRA_SWITCH_COST)
                best=utilities.argmax(axis=1)
                switch=utilities[np.arange(500),best]>0
                option=np.where(switch,best+1,0)
            selected=choices[np.arange(500),option,:]
            assert selected.shape==(500,6)
            row=dict(variant=arm,signal_date=dt,year=dt.year,n_baskets=500)
            row.update({k:float(selected[:,j].mean()) for j,k in enumerate(METRICS)})
            output.append(row)
            delta=selected[:,4]-baseline[:,4]
            changed=option>0
            corrections.append(dict(variant=arm,signal_date=dt,n_baskets=500,
               changed=int(changed.sum()),changes_better=int((delta>0).sum()),
               changes_worse=int((delta<0).sum()),
               mean_delta=float(delta.mean()),mean_loss10_delta=float((selected[:,5]-baseline[:,5]).mean())))
            for bidx in np.flatnonzero(changed):
                pidx=bidx*2+int(option[bidx])-1
                events.append(dict(variant=arm,signal_date=dt,basket=int(bidx),
                    original=base_symbols[bidx],alternative=pairs[pidx][1],
                    realized_delta=float(delta[bidx]),
                    utility_pred=float(utilities[bidx,option[bidx]-1]),
                    win_prob=float(pp[bidx,option[bidx]-1,0]),
                    conditional_win=float(pp[bidx,option[bidx]-1,1]),
                    conditional_loss=float(pp[bidx,option[bidx]-1,2])))
        print("UTILITY_EVAL",a.family,str(dt.date()),"training",0 if fitted is None else fitted[3],
              "changes",corrections[-2]["changed"],corrections[-1]["changed"],flush=True)
    m=pd.DataFrame(output)
    rr=m[m.variant.eq("CORRECTED")].sort_values("signal_date").reset_index(drop=True)
    assert rr.signal_date.equals(original.signal_date)
    np.testing.assert_allclose(rr[list(METRICS)].to_numpy(),original[list(METRICS)].to_numpy(),
        atol=1e-12,rtol=0,err_msg="BASELINE MATCH MUST HOLD EXACT")
    assert m.groupby("variant").size().eq(101).all()
    assert m.n_baskets.eq(500).all()
    for arm in arms:
        z=m[m.variant.eq(arm)].sort_values("signal_date")
        np.testing.assert_allclose(z.basket_top3.to_numpy(),original.basket_top3.to_numpy(),
            rtol=0,atol=1e-12)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    changes=pd.DataFrame(corrections)
    summ=m.groupby("variant")[list(METRICS)].mean()
    total=changes.groupby("variant")[["changed","changes_better","changes_worse"]].sum()
    summ=summ.join(total)
    summ["correct_rate"]=summ.changes_better/(summ.changes_better+summ.changes_worse)
    summ["change_fraction"]=summ.changed/(101*500)
    summ["delta_vs_incumbent_selected_excess"]=summ.basket_selected_excess-incumbent.basket_selected_excess.mean()
    summ.to_csv(out/"SUMMARY.csv")
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    changes.to_csv(out/"CORRECTIONS.csv",index=False)
    pd.DataFrame(audit).to_csv(out/"FIT_AUDIT.csv",index=False)
    e=pd.DataFrame(events)
    if len(e):
        e.to_csv(out/"CHANGED_DECISIONS.csv",index=False)
        g=e.groupby(["variant","signal_date","original","alternative"]).agg(
            delta=("realized_delta","first"),repetitions=("basket","size"))
        g.reset_index().to_csv(out/"UNIQUE_PAIR_EVENTS.csv",index=False)
    else:
        pd.DataFrame().to_csv(out/"CHANGED_DECISIONS.csv",index=False)
        pd.DataFrame().to_csv(out/"UNIQUE_PAIR_EVENTS.csv",index=False)
    m.groupby(["variant","year"])[list(METRICS)].mean().to_csv(out/"YEARLY.csv")
    bootstrap_by_month(m,{"CORRECTED":rr,"NESTED_24_TOP1_GUARD":incumbent}).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(family=a.family,
      models="hurdle_p_positive_gain_negative_loss",
      risk_multipliers=RISK,switch_cost_proxy=EXTRA_SWITCH_COST,
      per_pair_label_clip=TARGET_CLIP,price_lookback_trading_days=[21,63],
      raw_price_features_only_pre_signal=True,frozen_raw_run=39482809691,
      frozen_first_stage_run=40016809498,frozen_incumbent_run=40032282233,
      quarterly_meta_refit=True,maturity_lag_calendar_days=60,
      distinct_pair_month_training=True,equal_month_training_weight=True,
      original_etfs=149,canonical_baskets=500,mature_months=101,
      expected_gain_not_portfolio_CAGR=True,historical_reused_not_holdout=True,
      production_strategy_changed=False),indent=2))
    print("UTILITY_RESEARCH_SUCCESS",a.family,flush=True)
    print(summ.to_string(),flush=True)
    print("CONFIDENCE_INTERVALS",flush=True)
    ci=pd.read_csv(out/"PAIRED_BOOTSTRAP.csv")
    print(ci[ci.metric.eq("basket_selected_excess")].to_string(index=False),flush=True)
if __name__=="__main__":main()
