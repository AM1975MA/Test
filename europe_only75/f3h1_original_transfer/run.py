#!/usr/bin/env python3
"""Genuine EUROPE60-from-scratch F3/H1/H3 from original149 algorithms.

19+6 feature F3, original 10-factor 126-close betas, maturity-embargo quarterly
refit, euro FX-adjusted one-previous-US-day-only factors; all 60 European
tickers portfolio eligible. Precommitted preregistration; NOT PIT OOS validation.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from research_reset.predict149.tournament import precompute,FEATS
from europe_only75.risk_ablation.run import (
    read_prices,construct_calendar,frozen_rh_scores,selections,
    verify_archived_fixed,rebalance,execute
)

ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT
ROSTER=ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"
ORIGINAL120=ROOT/"data/eu120/raw_ticker_csv"
ARCHIVED=ROOT/"europe_only75/risk_ablation/results/DAILY_COMMON_OPEN_COSTED_NAV.csv"
FACTORS=("SPY","QQQ","IWM","VEA","EEM","TLT","HYG","GLD","USO","IEF")
REF=FACTORS+("AGG",)
COLUMNS=tuple(FEATS)+tuple("g"+str(i) for i in range(6))
INPUT=COLUMNS+tuple("beta_"+t for t in FACTORS)+("resid_momentum21","resid_momentum63")
QUANTILES=(.10,.50,.90)
M=("RH_EUROPE_CONTROL","F3_EUROPE_REFIT","H1_EUROPE_REFIT",
   "H3_EUROPE_REFIT","F3_H1_50_EUROPE")
TRAIN_MIN=40
SEED=20261019
CLIP=.20

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def join_eur_prices(candidate, reference, fx):
    """Dollar factor previous US date, no US same-day close leakage to EU signal."""
    dates=candidate["Close"].index
    f=pd.read_csv(fx,parse_dates=["date"]).set_index("date").sort_index()["Close"].astype(float)
    if f.empty or not f.index.is_unique:raise AssertionError("FX invalid")
    prev=pd.DatetimeIndex(dates-pd.Timedelta(days=1))
    refs=reference["Close"][list(REF)].sort_index()
    # Most recent US Close <= prior CALENDAR date, conservative for all EU closes.
    joined=refs.reindex(refs.index.union(prev)).sort_index().ffill().reindex(prev)
    fxprev=f.reindex(f.index.union(prev)).sort_index().ffill().reindex(prev)
    assert len(joined)==len(fxprev)==len(dates)
    joined.index=dates
    fxprev.index=dates
    eur=joined.div(fxprev,axis=0)
    eur=eur.where((eur>0)&np.isfinite(eur))
    close=pd.concat([candidate["Close"],eur],axis=1).dropna().sort_index()
    if len(close)<2300:
        raise AssertionError("Not enough fully synchronous historical euro close observations "+str(len(close)))
    if (close<=0).any().any() or close.columns.duplicated().any():
        raise AssertionError("Duplicate tickers or invalid USD/EUR conversion")
    return close,eur

def betas(C,names,asof):
    """UNCHANGED H1 beta centering, ridge .005; 126 actual past common Close rows."""
    z=np.log(C.loc[:asof,list(names)+list(REF)].tail(200))
    d=z.diff().tail(126)
    if len(d)!=126 or not np.isfinite(d.to_numpy(float)).all():
        raise AssertionError("Missing earlier EU/USA synchronized 126 beta returns")
    benchmark=.6*d["SPY"].to_numpy()+.4*d["AGG"].to_numpy()
    x=d[list(FACTORS)].to_numpy(float)-benchmark[:,None]
    y=d[names].to_numpy(float)-benchmark[:,None]
    x=x-x.mean(axis=0);y=y-y.mean(axis=0)
    beta=np.linalg.solve(x.T@x+.005*np.eye(10),x.T@y).T
    if beta.shape!=(60,10) or not np.isfinite(beta).all() or np.abs(beta).max()>20:
        raise AssertionError("Beta invalid")
    context=[];eps=[]
    for horizon in (5,21,63):
        r=z.iloc[-1]-z.iloc[-horizon-1]
        proxy=r[list(FACTORS)].to_numpy(float)-.6*float(r["SPY"])-.4*float(r["AGG"])
        etf=r[names].to_numpy(float)-.6*float(r["SPY"])-.4*float(r["AGG"])
        context.extend(proxy.tolist())
        if horizon in (21,63):eps.append(etf-beta@proxy)
    assert len(context)==30 and len(eps)==2
    return beta,np.column_stack(eps),np.array(context,float)


def original_feature_formulas_for_60(C,roster):
    """Exact original149 19 maths, with 60 portfolio names distinguished from
    11 explanatory nontradeable factor proxies (the 149 helper assumed otherwise).
    """
    names=list(roster.ticker)
    log=np.log(C.where(C>0))
    ret=log.diff()
    r={w:log-log.shift(w) for w in (5,21,63,126)}
    vol={w:ret.rolling(w,min_periods=w).std() for w in (21,63,126)}
    draw={w:log-log.rolling(w,min_periods=w).max() for w in (63,126)}
    down=ret.clip(upper=0).pow(2).rolling(63,min_periods=63).mean().pow(.5)
    sp=ret["SPY"]
    beta=ret.rolling(126,min_periods=126).cov(sp).div(
         sp.rolling(126,min_periods=126).var(),axis=0)
    groups=roster.set_index("ticker").macro_category.to_dict()
    factors={}
    pct=pd.DataFrame(index=C.index,columns=names,dtype=float)
    for w in (21,63):
        f=pd.DataFrame(index=C.index,columns=names,dtype=float)
        for group in sorted(set(groups.values())):
            mem=[t for t in names if groups[t]==group]
            f.loc[:,mem]=np.repeat(r[w][mem].mean(axis=1).to_numpy()[:,None],
                                   len(mem),axis=1)
            if w==63:pct.loc[:,mem]=r[w][mem].rank(axis=1,pct=True)
        factors[w]=f.astype(float)
    d={
      "r5":r[5],"r21":r[21],"r63":r[63],"r126":r[126],
      "v21":vol[21],"v63":vol[63],"v126":vol[126],
      "down63":down,"draw63":draw[63],"draw126":draw[126],
      "beta126":beta,
      "res21":r[21][names]-factors[21],
      "res63":r[63][names]-factors[63],
      "grp21":factors[21],"grp63":factors[63],
      "volshock":vol[21]/vol[63].clip(lower=1e-5),
      "accel":r[5]-r[21]/4.2,
      "rank63":pct,
      "trendrisk":(r[21]+r[63]/3)/(vol[63].clip(lower=.001)*math.sqrt(21))}
    assert tuple(d)==FEATS and len(d)==19
    return d,groups

def create_labels_and_asof_features(roster,candidate,C,cal,eur):
    """Historical 113 monthly blocks with actual labels only for later matured fit."""
    names=list(roster.ticker)
    fs,groups=original_feature_formulas_for_60(C,roster)
    category={x:i for i,x in enumerate(sorted(set(roster.macro_category)))}
    assert len(category)==6
    rows=[];factor_z=[];factor_context=[]
    for block,r in cal.iterrows():
        signal=pd.Timestamp(r.signal_date)
        eligible=C.index[C.index<=signal]
        if len(eligible)==0:raise AssertionError("no previous price close")
        asof=eligible[-1]
        if (signal-asof).days>8:raise AssertionError("as-of close stale")
        # Europe60 has a late starting common historical panel. Original
        # H1 requires 126 PRE-signal joint closes. This is an as-of source
        # eligibility test, not ex-post performance-based ticker selection.
        if int(C.index.searchsorted(asof,side="right")) < 127:
            print("EU60_SKIP_EARLY_WARMUP_INSUFFICIENT_PRIOR_126",block,str(signal.date()),flush=True)
            # Retain exact original MONTH INDEX for factor training and
            # future asof contexts; these NaNs are NEVER fitted or predicted.
            factor_z.append(np.full(10,np.nan))
            factor_context.append(np.full(30,np.nan))
            continue
        start=pd.Timestamp(r.entry_date);stop=pd.Timestamp(r.exit_date)
        assert asof<=signal<start<stop
        market_start=eur.loc[start,list(REF)].to_numpy(float)
        market_stop=eur.loc[stop,list(REF)].to_numpy(float)
        if not (np.isfinite(market_start).all() and np.isfinite(market_stop).all()):
            raise AssertionError("Reference FX lag missing on entry/exit")
        fwd_factor=np.log(market_stop/market_start)
        fwd_benchmark=float(np.log(.6*np.exp(fwd_factor[0])+
                                    .4*np.exp(fwd_factor[-1])))
        z=fwd_factor[:10]-fwd_benchmark
        future=np.log(candidate["Open"].loc[stop,names].to_numpy(float)/
                      candidate["Open"].loc[start,names].to_numpy(float))
        bx,eps,context=betas(C,names,asof)
        x=np.stack([fs[f].loc[asof,names].to_numpy(float) for f in FEATS],axis=1)
        classx=np.zeros((60,6),float)
        for j,t in enumerate(names):
            classx[j,category[groups[t]]]=1.
        resid=future-fwd_benchmark-bx@z
        if not (np.isfinite(x).all() and np.isfinite(resid).all()):
            raise AssertionError("Incomplete as-of source feature history "+str(block))
        for i,t in enumerate(names):
            record=dict(block=int(block),ticker=t,signal=str(signal.date()),
                        asof_close=str(asof.date()),entry=str(start.date()),
                        maturity=str(stop.date()),category=groups[t],
                        future_nominal_log=float(future[i]),
                        future_excess=float(future[i]-fwd_benchmark),
                        clipped_future_excess=float(np.clip(future[i]-fwd_benchmark,-CLIP,CLIP)),
                        future_idio_residual=float(resid[i]),
                        clipped_future_idio_residual=float(np.clip(resid[i],-CLIP,CLIP)))
            record.update({k:float(x[i,j]) for j,k in enumerate(FEATS)})
            record.update({f"g{j}":float(classx[i,j]) for j in range(6)})
            record.update({"beta_"+fact:float(bx[i,j]) for j,fact in enumerate(FACTORS)})
            record.update(resid_momentum21=float(eps[i,0]),
                          resid_momentum63=float(eps[i,1]))
            rows.append(record)
        factor_z.append(z)
        factor_context.append(context)
    frame=pd.DataFrame(rows)
    if (len(frame)!=60*frame.block.nunique() or
        frame.block.nunique()<len(cal)-10 or frame.groupby("block").size().ne(60).any()
        or not np.isfinite(frame[list(INPUT)].to_numpy(float)).all()):
        raise AssertionError("EU60 panel incomplete")
    assert len(factor_z)==len(cal) and len(factor_context)==len(cal)
    return frame,np.array(factor_z),np.array(factor_context)

def qmodel(q):
    return LGBMRegressor(objective="quantile",alpha=q,n_estimators=80,
      learning_rate=.04,num_leaves=9,max_depth=4,min_child_samples=100,
      reg_lambda=25.,random_state=SEED,n_jobs=1,verbosity=-1)

def fit_predict(frame,Z,contexts,cal):
    """Strict maturity embargo (last block ending at entry not yet seen at prior Close)."""
    testidx=[i for i,r in cal.iterrows() if r.signal_date>=pd.Timestamp("2021-01-01")]
    assert 55<=len(testidx)<=70
    prediction=[];factor_diag=[]
    models=None
    for j,idx in enumerate(testidx):
        signal=pd.Timestamp(cal.loc[idx,"signal_date"])
        past=frame[pd.to_datetime(frame.maturity)<signal].copy()
        last=int(past.block.max())
        usable=sorted(past.block.unique())
        assert len(usable)>=TRAIN_MIN and (last<=idx-2)
        assert (pd.to_datetime(past.maturity)<signal).all()
        now=frame[frame.block==idx].copy()
        assert len(now)==60 and np.isfinite(contexts[idx]).all()
        if models is None or j%3==0:
            trainx=past[list(COLUMNS)].to_numpy(float)
            trainfull=past[list(INPUT)].to_numpy(float)
            y=past.clipped_future_excess.to_numpy(float)
            r=past.clipped_future_idio_residual.to_numpy(float)
            F3={q:qmodel(q).fit(trainx,y) for q in QUANTILES}
            H2={q:qmodel(q).fit(trainfull,r) for q in QUANTILES}
            assert np.isfinite(contexts[usable]).all() and np.isfinite(Z[usable]).all()
            sc=StandardScaler().fit(contexts[usable])
            h=Ridge(alpha=60.,fit_intercept=True).fit(
                sc.transform(contexts[usable]),Z[usable])
            models=dict(f3=F3,h2=H2,scaler=sc,forecaster=h,
                        factor_null=Z[usable].mean(axis=0))
            print("EU_F3H1_H3_CHRONOLOGICAL_REFIT",j,idx,"train_blocks",len(usable),
                  "last_maturity",str(past.maturity.max()),flush=True)
        A=now[list(COLUMNS)].to_numpy(float)
        B=now[list(INPUT)].to_numpy(float)
        f3=np.sort(np.column_stack([models["f3"][q].predict(A)
                                  for q in QUANTILES]),axis=1)
        h2=np.sort(np.column_stack([models["h2"][q].predict(B)
                                  for q in QUANTILES]),axis=1)
        bet=now[["beta_"+t for t in FACTORS]].to_numpy(float)
        factor_pred=models["forecaster"].predict(
                        models["scaler"].transform(contexts[idx:idx+1]))[0]
        h1=bet@factor_pred
        now["F3_EUROPE_REFIT"]=(f3[:,0]+2*f3[:,1]+f3[:,2])/4
        now["H1_EUROPE_REFIT"]=h1
        now["H2_RESIDUAL_FORECAST"]=(h2[:,0]+2*h2[:,1]+h2[:,2])/4
        now["H3_EUROPE_REFIT"]=now["H1_EUROPE_REFIT"]+now["H2_RESIDUAL_FORECAST"]
        now["F3_NULL_Q10"]=float(past.clipped_future_excess.quantile(.10))
        now["F3_NULL_Q90"]=float(past.clipped_future_excess.quantile(.90))
        now["F3_Q10"]=f3[:,0];now["F3_Q50"]=f3[:,1];now["F3_Q90"]=f3[:,2]
        now["H3_RESID_Q10"]=h2[:,0];now["H3_RESID_Q90"]=h2[:,2]
        now["training_maturity"]=str(past.maturity.max())
        now["training_month_count"]=len(usable)
        prediction.append(now)
        factor_diag.append(dict(block=int(idx),signal=str(signal.date()),
            factor_future_mse=float(np.mean((factor_pred-Z[idx])**2)),
            historical_matured_mean_mse=float(np.mean(
                (models["factor_null"]-Z[idx])**2))))
    p=pd.concat(prediction,ignore_index=True)
    assert (pd.to_datetime(p.training_maturity)<pd.to_datetime(p.signal)).all()
    assert len(p)==len(testidx)*60
    assert np.isfinite(p[list(("F3_EUROPE_REFIT","H1_EUROPE_REFIT",
                              "H3_EUROPE_REFIT"))].to_numpy(float)).all()
    return p,pd.DataFrame(factor_diag),testidx

def picked(df,scorer,k=5):
    z=df.sort_values([scorer,"ticker"],ascending=[False,True],kind="mergesort")
    return z.ticker.head(k).tolist()

def portfolio_weights(p,cal,refit_rh,testidx,include):
    methods={m:[] for m in M}
    selections_rows=[]
    for i in testidx:
        now=p[p.block==i]
        frozen=refit_rh[i]
        f=picked(now,"F3_EUROPE_REFIT")
        h=picked(now,"H1_EUROPE_REFIT")
        third=picked(now,"H3_EUROPE_REFIT")
        assert len(set(f))==len(set(h))==len(set(third))==5
        mix={}
        for t in f:mix[t]=mix.get(t,0)+.1
        for t in h:mix[t]=mix.get(t,0)+.1
        current={
          M[0]:{t:.5 for t in frozen},
          M[1]:{t:.2 for t in f},
          M[2]:{t:.2 for t in h},
          M[3]:{t:.2 for t in third},
          M[4]:mix}
        for m,w in current.items():
            assert set(w).issubset(set(include)) and abs(sum(w.values())-1)<1e-12
            methods[m].append(w)
            for t,x in w.items():
                selections_rows.append(dict(block=i,signal=str(cal.loc[i,"signal_date"].date()),
                       method=m,ticker=t,weight=x))
    return methods,pd.DataFrame(selections_rows)

def costed_path(monthly_weights,cal,open_prices,common_days):
    """Exact self-financing portfolio starts at 1 just before the first entry.
    No extra trades in between monthly signals. Daily opened marks coherent.
    """
    days=common_days[(common_days>=cal.entry_date.min()) &
                     (common_days<=cal.exit_date.max())]
    shares={};cash=1.;curve={};monthly=[];fees=0.;gross=0.
    for k,row in cal.iterrows():
        w=monthly_weights[k]
        dates=days[(days>=row.entry_date)&(days<=row.exit_date)]
        quotes={t:float(open_prices.loc[row.entry_date,t]) for t in set(shares)|set(w)}
        pre=cash+sum(shares[t]*quotes[t] for t in shares)
        shares,cash,turn,fee=rebalance(shares,cash,w,quotes)
        fees+=fee;gross+=turn
        for d in dates:
            net=cash+sum(q*float(open_prices.loc[d,t]) for t,q in shares.items())
            if d==row.exit_date:final=net
            else:curve[pd.Timestamp(d)]=net
        monthly.append(dict(block=k,signal=str(row.signal_date.date()),
                before=pre,end_nav=final,net_log_growth=float(np.log(final/pre)),
                ETF_count=len(w),traded_notional=turn,fee=fee))
    curve[pd.Timestamp(cal.exit_date.iloc[-1])]=final
    nav=pd.Series(curve).sort_index()
    assert len(nav)==len(days) and nav.index.equals(days)
    arr=nav.to_numpy(float);assert np.isfinite(arr).all() and min(arr)>0
    dr=np.diff(np.log(arr))
    years=(days[-1]-days[0]).days/365.25
    metrics=dict(cagr=float(final**(1/years)-1),terminal_capital=float(final),
       maxdd_daily_open=float((arr/np.maximum.accumulate(arr)-1).min()),
       sharpe_daily_log=float(np.mean(dr)/np.std(dr,ddof=1)*np.sqrt(252)),
       es5_daily=float(np.mean(np.sort(np.expm1(dr))[:math.ceil(.05*len(dr))])),
       ann_vol=float(dr.std(ddof=1)*np.sqrt(252)),
       fee_notional=fees,gross_turnover=gross,position_count_mean=float(
           np.mean([len(w) for w in monthly_weights])),
       n_sessions=len(days))
    return metrics,nav,pd.DataFrame(monthly)

def ci(vals,seed):
    a=np.array(vals,float);n=len(a)
    rng=np.random.default_rng(seed);dist=[]
    for _ in range(2500):
        ids=[]
        while len(ids)<n:
            v=int(rng.integers(n))
            ids.extend((v+j)%n for j in range(3))
        dist.append(float(a[np.array(ids[:n])].mean()))
    return {"mean":float(a.mean()),"CI95":[float(x) for x in np.quantile(dist,[.025,.975])]}

def pinball(y,p,q):
    r=np.asarray(y,float)-np.asarray(p,float)
    return float(np.maximum(q*r,(q-1)*r).mean())

def evaluate(args):
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    roster=pd.read_csv(ROSTER)
    assert len(roster)==60 and roster.ticker.nunique()==60
    names=list(roster.ticker)
    candidate=read_prices(names,ROOT/"data/eu120/raw_ticker_csv")
    refs=read_prices(REF,Path(args.raw149)/"etf_trader_raw")
    fx=Path(args.fx)/"EURUSD_PRIOR_US_CLOSE.csv"
    if not fx.exists():raise AssertionError("Missing archived EURUSD FX")
    euC,eur=join_eur_prices(candidate,refs,fx)
    annual=pd.read_csv(Path(args.eu_model)/"TRAINING_AUDIT.csv")
    assert len(annual)==10 and annual.lookahead_guard_PASS.astype(bool).all()
    for y in annual.itertuples():
        assert pd.Timestamp(y.latest_training_label_exit)<pd.Timestamp(int(y.year),1,1)
        assert pd.Timestamp(y.ma3_latest_exit)<pd.Timestamp(int(y.year),1,1)
    compact=pd.read_parquet(Path(args.eu_model)/"COMPACT_REFITTED.parquet")
    hybrid=pd.read_parquet(Path(args.eu_model)/"HYBRID_REFITTED.parquet")
    joinedO=pd.concat([candidate["Open"],refs["Open"]],axis=1).sort_index()
    cal,commondays=construct_calendar(joinedO,(compact,hybrid))
    rhscore=frozen_rh_scores(compact,hybrid,cal,names)
    rhselected=selections(rhscore,names)
    legacy=verify_archived_fixed(cal,rhselected,candidate["Open"],
                                 Path(args.eu_model)/"FIXED_5050.csv")
    # independently reproduce our exact full EUR60 R_H share curve from
    # previous risk trial before measuring any EUROPE F3/H1 forecasts
    fullweights=[{t:.5 for t in row} for row in rhselected]
    r,original_full,monthly=execute(fullweights,cal,candidate["Open"],commondays)
    previous=pd.read_csv(ARCHIVED,parse_dates=["day"]).set_index("day")
    same=original_full.to_numpy()-previous.B0_RH_TOP2.to_numpy(float)
    parity=float(np.max(np.abs(same)))
    assert parity<1e-9 and len(original_full)==2277
    frame,Z,contexts=create_labels_and_asof_features(roster,candidate,euC,cal,eur)
    forecast,factor_stats,testidx=fit_predict(frame,Z,contexts,cal)
    weights,selected=portfolio_weights(forecast,cal,rhselected,testidx,names)
    smallcal=cal.iloc[testidx].reset_index(drop=True)
    allmetrics={};curves={};monthlys={}
    for name in M:
        metric,curve,month=costed_path(weights[name],smallcal,
                                      candidate["Open"],commondays)
        allmetrics[name]=metric;curves[name]=curve;monthlys[name]=month
        print("EU60_F3H1H3_COSTED_ECON",name,json.dumps(metric),flush=True)
    assert all(curves[x].index.equals(curves[M[0]].index) for x in M)
    # Three-month circular date bootstrap compares truly cost-matched monthly
    # EU R_H, F3, H1, H3 and 50:50 on identical later evaluation opens.
    years=smallcal.signal_date.dt.year.to_numpy()
    ref=monthlys[M[0]].net_log_growth.to_numpy(float)
    comparison={}
    for i,method in enumerate(M[1:]):
        d=monthlys[method].net_log_growth.to_numpy(float)-ref
        comparison[method]=dict(
          vs_euro_RH=ci(d,SEED+i+1),
          earlier_2021_2023=float(np.mean(d[years<=2023])),
          later_2024_2026=float(np.mean(d[years>=2024])),
          dd_improvement_pp=(allmetrics[method]["maxdd_daily_open"]-
              allmetrics[M[0]]["maxdd_daily_open"])*100,
          es5_improvement_pp=(allmetrics[method]["es5_daily"]-
              allmetrics[M[0]]["es5_daily"])*100)
    # Full-universe signed next-period rank: forecast skill vs actual EU
    # future relative LOG payoff, cluster unit is monthly anchor, NOT 60 rows.
    score_records=[]
    for i in testidx:
        q=forecast.loc[forecast.block==i]
        for method in ("F3_EUROPE_REFIT","H1_EUROPE_REFIT","H3_EUROPE_REFIT"):
            s=float(spearmanr(q[method],q.future_excess).statistic)
            sel=set(picked(q,method))
            score_records.append(dict(block=int(i),model=method,signal=q.signal.iloc[0],
              spear=s,selected_mean_excess=float(q[q.ticker.isin(sel)].future_excess.mean()),
              selected_mean_nominal=float(q[q.ticker.isin(sel)].future_nominal_log.mean())))
    score_df=pd.DataFrame(score_records)
    skill={}
    for j,method in enumerate(("F3_EUROPE_REFIT","H1_EUROPE_REFIT","H3_EUROPE_REFIT")):
        rows=score_df[score_df.model==method]
        skill[method]=dict(crosssection_spearman=ci(rows.spear,SEED+15+j),
          chosen5_future_relative_log=float(rows.selected_mean_excess.mean()))
    y=forecast.clipped_future_excess.to_numpy(float)
    q10=pinball(y,forecast.F3_Q10,.1)
    q90=pinball(y,forecast.F3_Q90,.9)
    null10=pinball(y,forecast.F3_NULL_Q10,.1)
    null90=pinball(y,forecast.F3_NULL_Q90,.9)
    factor_mse=dict(factor_model=float(factor_stats.factor_future_mse.mean()),
                    matured_null=float(factor_stats.historical_matured_mean_mse.mean()))
    primary="F3_H1_50_EUROPE"
    a=comparison[primary]
    joint=bool(allmetrics[primary]["cagr"]>allmetrics[M[0]]["cagr"] and
      a["dd_improvement_pp"]>=0 and a["es5_improvement_pp"]>=0 and
      a["vs_euro_RH"]["CI95"][0]>0 and a["earlier_2021_2023"]>0 and
      a["later_2024_2026"]>0 and any(
        skill[z]["crosssection_spearman"]["CI95"][0]>0 for z in
        ("F3_EUROPE_REFIT","H1_EUROPE_REFIT")))
    table=pd.DataFrame({"day":curves[M[0]].index})
    for m in M:table[m]=curves[m].to_numpy(float)
    table.to_csv(out/"EUROPE60_F3_H1_H3_REAL_COST_DAILY_NAV.csv",index=False)
    selected.to_csv(out/"ALL_EXPERT_MONTHLY_REAL_ETF_SHARES.csv",index=False)
    forecast.to_csv(out/"EUR60_ALL_60_F3_H1_H3_WALK_FORWARD_FORECASTS.csv",index=False)
    factor_stats.to_csv(out/"ASOF_FACTOR_REGRESSION_MONTHLY_PROPER_SCORE.csv",index=False)
    score_df.to_csv(out/"MONTHLY_TRUE_FUTURE_SIGNED_RANK_SCORE.csv",index=False)
    for m in M:monthlys[m].to_csv(out/("MONTHLY_"+m+".csv"),index=False)
    result=dict(status="EUROPE60_ORIGINAL_F3_H1_H3_WALKFORWARD_AND_MATCHED_RH_COMPLETE",
        n_europeonly_EUR_candidate_etfs=60,
        n_annual_eu_source_RH_folds=10,
        n_eu_calendar_months_total=len(cal),n_retained_asof_feature_label_blocks=frame.block.nunique(),n_eval_months=len(testidx),
        eval_begin=str(smallcal.signal_date.min().date()),
        eval_end=str(smallcal.exit_date.max().date()),
        daily_open_evaluations=len(table),
        no_US_149_ETF_portfolio_positions=True,
        original_19_plus_6_F3_features=True,original_10_factor_H1_beta=True,
        original_quantile_lightgbm_parameters=True,training_quarterly_asof_strict=True,
        legacy_EUR60_RH_50_50_approx_fee_parity=legacy,
        original_20261019_real_share_RH_parity=parity,
        all_policy_results=allmetrics,
        paired_vs_RH=comparison,
        full_universe_directional_skill=skill,
        original_F3_quantile_pinball=dict(
            model_q10=q10,prior_q10=null10,model_q90=q90,prior_q90=null90),
        original_H1_factor_next21_MSE=factor_mse,
        F3_H1_50_strict_scientific_GO=joint,
        reference_fx_sha=sha(fx),
        usa_factor_prices_use_prior_calendar_day=True,
        original149_us_cohort_trained_models_used=False,
        model_60_target_EUR_labels_only=True,
        static_eur60_source_roster_sha=sha(ROSTER),
        historical_curation_survivorship_not_PIT=True,
        EU_EUR_trade_and_ISIN_not_individually_verified=True,
        no_etf_trader_production_changes=True,
        caveats=["EU60 comprises 2026 known survivors, backtesting reused 2017–2026 dates",
                 "Imported 11 US ETF factor proxies converted at lagged EURUSD prior US closing for conservative EU clock",
                 "Original USA F3/H1 algorithms retrained on Europe; predictions not original USA-trained weights",
                 "European monthly periods are variable 19-23 sessions, unlike original US exactly21",
                 "Euro adjusted ETF OHLC not live executable broker quotes; missing spreads, trading FX, taxes",
                 "FX Yahoo download historical vintage not real PIT, currency/ISIN venue requires further audits"])
    (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
    print("EUROPE60_ORIGINAL_F3H1H3_RESULT "+json.dumps(result),flush=True)
    return result


if __name__=="__main__":
    q=argparse.ArgumentParser()
    q.add_argument("--eu-model",required=True)
    q.add_argument("--raw149",required=True)
    q.add_argument("--fx",required=True)
    q.add_argument("--out",required=True)
    evaluate(q.parse_args())
