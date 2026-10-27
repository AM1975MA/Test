#!/usr/bin/env python3
"""Exact original V2 Hybrid24 fullstack 500x24 baskets, change ONLY causal risk veto.
Uses archived SOURCE-ONLY trained BASE/ET/XGB frozen original original inputs.
Reconstruct and certify exact original Top2, HighCAGR weights, GROSS and equity
BEFORE making separate veto variants; never edit legacy source.
No Ridge forecasts used in THIS full V2 experiment; Ridge-before-V2 has no
meaning as a direct swap. This tests mathematical risk filter within V2 fullstack.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.special import ndtr
from etf_trader.source_only.baskets import build_canonical_baskets
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24

SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
FEE=.001
def metrics(equity,mask):
    lr=np.diff(np.log(np.column_stack([np.ones(equity.shape[0]),equity])),axis=1)[:,mask]
    r=np.expm1(lr);n=lr.shape[1]
    cagr=np.expm1(lr.sum(axis=1)*252/n)
    eq=np.exp(np.cumsum(lr,axis=1))
    peak=np.maximum.accumulate(np.column_stack([np.ones(equity.shape[0]),eq]),axis=1)[:,1:]
    dd=(eq/peak-1).min(axis=1)
    sd=r.std(axis=1,ddof=1)
    sharpe=np.divide(r.mean(axis=1)*np.sqrt(252),sd,out=np.zeros_like(sd),where=sd>0)
    return dict(cagr=float(cagr.mean()),median_cagr=float(np.median(cagr)),
        p10_cagr=float(np.quantile(cagr,.1)),p05_cagr=float(np.quantile(cagr,.05)),
        maxdd=float(dd.mean()),p10dd=float(np.quantile(dd,.1)),
        p05dd=float(np.quantile(dd,.05)),worst=float(dd.min()),
        sharpe=float(sharpe.mean()))
def analytic_risk(C,signal_date):
    """Mathematical score computed on closing prices observable at signal_date.
    No future prices. No ML parameters, future labels or training.
    """
    x=C.loc[:signal_date]
    if len(x)<252:raise AssertionError("Insufficient prior-only closes")
    p=x.iloc[-1]
    returns=x.pct_change(fill_method=None)
    mom21=p/x.iloc[-22]-1
    mom63=p/x.iloc[-64]-1
    mom126=p/x.iloc[-127]-1
    mu=.50*mom21+.30*mom63/3+.20*mom126/6
    sigma21=returns.iloc[-21:].std(ddof=1)*np.sqrt(21)
    sig=np.maximum(sigma21.to_numpy(float),.001)
    risk=ndtr((-.05-mu.to_numpy(float))/sig)
    risk=np.where(np.isfinite(risk),risk,np.inf)
    return risk,mom63.to_numpy(float)
def guarded_alloc(baseline,score,cal,ds,BM,BOK,close,policy,
                  *,first_active=pd.Timestamp("2018-01-01")):
    alloc=producer.AllocationResult(d1=baseline.d1.copy(),
        d2=baseline.d2.copy(),weight1=baseline.weight1.copy(),margin=baseline.margin.copy())
    B=BM.shape[0]
    assert B==500 and BM.shape==(500,24)
    veto_events=[];precomputed={}
    for i,row in enumerate(cal.itertuples()):
        sig=pd.Timestamp(row.signal_date)
        if sig<first_active:continue
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        e=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if a>=len(ds) or e<=a:continue
        if sig not in precomputed:
            precomputed[sig]=analytic_risk(close,sig)
        risk,mom=precomputed[sig]
        rr=risk[BM]
        mo=mom[BM]
        # fixed number six of 24; random control applied per basket and month
        if policy=="PHYS_TAIL_25":
            removed=np.argsort(-rr,axis=1,kind="stable")[:,:6]
        elif policy=="MOMENTUM_25":
            removed=np.argsort(mo,axis=1,kind="stable")[:,:6]
        elif policy=="RANDOM_25":
            rng=np.random.default_rng(20261027+i)
            removed=np.array([rng.choice(24,6,replace=False) for _ in range(B)],dtype=np.int64)
        else:raise ValueError(policy)
        s=np.where(BOK,score[i,BM],-np.inf).copy()
        s[np.arange(B)[:,None],removed]=-np.inf
        top=np.argpartition(s,-2,axis=1)[:,-2:]
        ts=np.take_along_axis(s,top,axis=1)
        order=np.argsort(-ts,axis=1)
        top=np.take_along_axis(top,order,axis=1)
        ts=np.take_along_axis(ts,order,axis=1)
        assert np.isfinite(ts).all()
        ids=np.take_along_axis(BM,top,axis=1)
        margin=ts[:,0]-ts[:,1]
        w=.60+.40*np.minimum(margin/.13,1.0)**2
        alloc.d1[:,a:e]=ids[:,0,None]
        alloc.d2[:,a:e]=ids[:,1,None]
        alloc.weight1[:,a:e]=w[:,None]
        alloc.margin[:,a:e]=margin[:,None]
        old=baseline.d1[:,a]
        old2=baseline.d2[:,a]
        blocked=(old!=ids[:,0]) & (old!=ids[:,1])
        blocked2=(old2!=ids[:,0]) & (old2!=ids[:,1])
        for b in range(B):
            veto_events.append(dict(signal_date=str(sig.date()),basket=b,
                replaced_original_top1=int(blocked[b]),replaced_original_top2=int(blocked2[b]),
                old_top1=int(old[b]),old_top2=int(old2[b]),
                top1=int(ids[b,0]),top2=int(ids[b,1]),
                analytic_risk_top1=float(risk[ids[b,0]]),
                chosen_risk_top2=float(risk[ids[b,1]]),
                score_margin=float(margin[b])))
    return alloc,pd.DataFrame(veto_events)
def main():
    ap=argparse.ArgumentParser()
    for nm in ("raw","fs02-path","fs02-result","fs02-pred","baskets","out"):
        ap.add_argument("--"+nm,required=True)
    z=ap.parse_args();out=Path(z.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(z.baskets).read_bytes()).hexdigest()==SHA
    origin=json.loads(Path(z.fs02_result).read_text())
    assert origin["contract"]["basket_sha256"]==SHA
    assert origin["contract"]["titanium_maturity_safe"]
    assert origin["contract"]["ensemble_maturity_safe"]
    assert origin["contract"]["cluster_source_causal"]
    mats,cats,raw=load_ticker_csv_folder(z.raw)
    prior=np.load(z.fs02_path,allow_pickle=True)
    ds=pd.DatetimeIndex(prior["dates"])
    names=list(map(str,prior["tickers"]))
    assert len(names)==149 and len(ds)==2366
    assert list(mats["Open"].columns)==names
    old_baskets=pd.read_csv(z.baskets)
    assert len(old_baskets)==12000 and old_baskets.basket.nunique()==500
    recreated=build_canonical_baskets(pd.read_csv(Path(z.raw)/"universe.csv"),names)
    assert recreated.equals(old_baskets)
    bm,bok=producer.basket_arrays(old_baskets,names,n_baskets=500)
    assert bm.shape==(500,24) and bok.all()
    p=pd.read_csv(z.fs02_pred,parse_dates=["signal_date"])
    assert p.signal_date.nunique()==114 and p.ticker.nunique()==149
    months=pd.DatetimeIndex(sorted(p.signal_date.unique()))
    def panel(k):
        return p.pivot(index="signal_date",columns="ticker",values=k).reindex(index=months,columns=names).to_numpy(float)
    base,et,xgb,tail=[panel(k) for k in ("BASE","ET_TAIL","XGB_TAIL","TAIL_HYBRID")]
    np.testing.assert_allclose(tail,.6*et+.4*xgb,atol=1e-12,rtol=0)
    lag1=np.vstack([tail[:1],tail[:-1]])
    lag2=np.vstack([tail[:1],tail[:1],tail[:-2]])
    score=.475*base+.525*np.power(np.clip(.4*tail+.3*lag1+.3*lag2,0,1),1.1)
    assert score.shape==(114,149) and np.isfinite(score).all()
    dayindex=pd.DatetimeIndex(mats["Open"].index)
    enters=[dayindex[dayindex.searchsorted(s,side="right")] for s in months]
    assert enters[0]==ds[0] and enters[-1]==ds[-1]
    exits=enters[1:]+[ds[-1]+pd.Timedelta(days=1)]
    cal=pd.DataFrame(dict(signal_date=months,entry_date=enters,exit_date=exits))
    baseline=producer.allocations_from_score(score,cal,ds,bm,bok,continuous=True)
    np.testing.assert_array_equal(baseline.d1,prior["d1"])
    np.testing.assert_array_equal(baseline.d2,prior["d2"])
    np.testing.assert_allclose(baseline.margin,prior["margin"],atol=1e-12,rtol=0)
    Odf=mats["Open"].reindex(columns=names).ffill().bfill()
    Ldf=mats["Low"].reindex(columns=names).ffill().bfill().reindex(Odf.index)
    Cdf=mats["Close"].reindex(columns=names).ffill().bfill().reindex(Odf.index)
    Odf=Odf.loc[:ds[-1]]; Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index)
    st=int(Odf.index.get_loc(ds[0]));en=int(Odf.index.get_loc(ds[-1]))
    assert Odf.index[st:en+1].equals(ds)
    gross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float)
    g,w=highcagr24.apply_highcagr24(gross,baseline.weight1,baseline.margin)
    np.testing.assert_allclose(g,prior["global_gross"],atol=1e-12,rtol=0)
    np.testing.assert_allclose(w,prior["wg"],atol=1e-12,rtol=0)
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k][st:en+1] for k in
        ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    def simulate(alloc):
        gr,weight=highcagr24.apply_highcagr24(gross,alloc.weight1,alloc.margin)
        np.testing.assert_allclose(gr,g,atol=1e-12,rtol=0)
        state=v6.build_v6_state(Cdf.loc[ds,names],
            alloc.d1,alloc.d2,alloc.weight1,gross)
        eq,turn,expo,aw=v6.simulate_with_alt(
            alloc.d1,alloc.d2,weight,O,L,C,PC,gap,ud1,uneg,UH,SA,
            names.index("BIL"),names.index("SHV"),gr,state.alt_idx,
            True,.001)
        assert eq.shape==(500,len(ds)) and np.isfinite(eq).all()
        return eq,turn,expo,aw,state
    eq0,turn0,expo0,aw0,state0=simulate(baseline)
    # Stronger baseline parity: original V2 daily NAV and risk parts all equal.
    dif=float(np.max(np.abs(eq0-prior["equity"])))
    print("SOURCE_ONLY_FULLSTACK500_V2_EQUITY_PARITY_MAX",dif,flush=True)
    np.testing.assert_allclose(eq0,prior["equity"],atol=1e-9,rtol=1e-9)
    np.testing.assert_allclose(turn0,prior["turnover"],atol=1e-9,rtol=1e-9)
    np.testing.assert_array_equal(state0.alt_idx,prior["alt_idx"])
    masks=dict(full=np.ones(len(ds),bool),
               common2018plus=ds>=pd.Timestamp("2018-02-01"),
               common2022plus=ds>=pd.Timestamp("2022-02-01"))
    srcmetric=origin["metrics"]["common2018plus"]["highcagr24"]
    actual=metrics(eq0,masks["common2018plus"])
    for key in ("cagr","maxdd","p10_cagr","p10dd","worst"):
        assert abs(actual[key]-srcmetric[key])<1e-9,(key,actual[key],srcmetric[key])
    econ=[];month_picks=[];events=[];arrs={"ORIGINAL_FULL_V2":(eq0,turn0)}
    all_alloc={"ORIGINAL_FULL_V2":baseline}
    for policy in ("PHYS_TAIL_25","MOMENTUM_25","RANDOM_25"):
        alloc,ev=guarded_alloc(baseline,score,cal,ds,bm,bok,Cdf,policy)
        assert np.array_equal(baseline.d1[:,ds<pd.Timestamp("2018-02-01")],
                       alloc.d1[:,ds<pd.Timestamp("2018-02-01")])
        events.append(ev.assign(policy=policy))
        eq,turn,expo,aw,state=simulate(alloc)
        arrs[policy]=(eq,turn);all_alloc[policy]=alloc
        print("COMPLETE_ORIGINAL_V2_RISK_SLEEVES",policy,"V6_alternatives",(state.alt_idx>=0).sum(),flush=True)
    for window,mask in masks.items():
        for policy,(eq,turn) in arrs.items():
            stats=metrics(eq,mask)
            agg=eq.mean(axis=0)
            aggmetric=metrics(agg[None,:],mask)
            stats.update(window=window,policy=policy,
                         equal_capital_cagr=aggmetric["cagr"],
                         equal_capital_maxdd=aggmetric["maxdd"],
                         annualized_turnover=float(turn[:,mask].mean()*252))
            econ.append(stats)
            print("V2_FULLSTACK_MATH",window,policy,round(stats["cagr"]*100,4),
                  round(stats["maxdd"]*100,4),
                  round(stats["equal_capital_cagr"]*100,4),flush=True)
    pd.DataFrame(econ).to_csv(out/"FULL_STACK500_ECONOMICS.csv",index=False)
    pd.concat(events,ignore_index=True).to_csv(out/"VETO_ORIGINAL_500_TOP2_REPLACEMENT_AUDIT.csv",index=False)
    nav=pd.DataFrame({"date":ds,**{key:v[0].mean(axis=0) for key,v in arrs.items()}})
    nav.to_csv(out/"FULLSTACK500_EQUAL_CAPITAL_DAILY_NAV.csv",index=False)
    np.savez_compressed(out/"FULLSTACK500_ALL_BASKETS_DAILY_NAV.npz",dates=ds.values,
        **{policy:eq for policy,(eq,turn) in arrs.items()})
    # Analyze price-reality 21d future drawdowns: per basket selection, not
    # correlated 500 baskets treated as independent data for uncertainty.
    ts=Odf.reindex(index=dayindex).to_numpy(float)
    output=[]
    for i,sig in enumerate(months):
        if sig<pd.Timestamp("2018-01-01"):continue
        j=int(dayindex.searchsorted(sig,side="right"))
        j21=min(j+21,len(dayindex)-1)
        actual=ts[j21]/ts[j]-1.
        ix=int(ds.searchsorted(enters[i]))
        for policy,alloc in all_alloc.items():
            a=alloc.d1[:,ix].astype(int);b=alloc.d2[:,ix].astype(int)
            both=np.concatenate([actual[a],actual[b]])
            output.append(dict(signal_date=str(sig.date()),policy=policy,
                 selected_future21_avg=float(np.nanmean(both)),
                 severe_loss5_rate=float(np.nanmean(both<=-.05)),
                 mean_margin=float(alloc.margin[:,ix].mean()),
                 n_selected=int(len(both))))
    o=pd.DataFrame(output)
    o.to_csv(out/"FULLSTACK500_MONTHLY_SELECTED_FUTURE21_SKILL.csv",index=False)
    # Paired block intervals across 101 calendar months.
    rng=np.random.default_rng(20261027);pairs=[]
    for policy in ("PHYS_TAIL_25","MOMENTUM_25","RANDOM_25"):
        a=o[o.policy.eq(policy)].reset_index(drop=True)
        b=o[o.policy.eq("ORIGINAL_FULL_V2")].reset_index(drop=True)
        assert a.signal_date.equals(b.signal_date) and len(a)==101
        for key in ("selected_future21_avg","severe_loss5_rate"):
            x=(a[key]-b[key]).to_numpy(float)
            bs=[]
            for _ in range(4000):
                indices=[]
                while len(indices)<len(x):
                    start=int(rng.integers(0,len(x)))
                    indices.extend((start+np.arange(6))%len(x))
                bs.append(float(np.mean(x[np.array(indices[:len(x)],int)])))
            pairs.append(dict(policy=policy,metric=key,mean_delta=float(x.mean()),
                ci_95_low=float(np.percentile(bs,2.5)),ci_95_high=float(np.percentile(bs,97.5))))
    pd.DataFrame(pairs).to_csv(out/"FULLSTACK500_PAIRED_MONTHLY_PREDICTIVE_BOOTSTRAP.csv",index=False)
    record=dict(run="Original complete 500-basket V2 fullstack with pure mathematical veto before unchanged V2 score Top2",
        source_run=39836842157,source_locked_500_membership_sha=SHA,
        parity_full_original_daily_NAV_exact=True,
        parity_max_error=dif,
        source_raw_run=39482809691,
        root_V2_source_unmodified=True,
        score_components="Titanium BASE .475 + smoothed .6 ET/.4 XGB Tail .525 power1.1",
        veto_design="delete 6 highest estimated tail probability out of each original 24 before original Top2",
        physics="Gaussian drift diffusion mu=.50R21+.30R63/3+.20R126/6; sigma=stdev21*sqrt(21), P(R21<-5%)",
        preserves=["Top2 continuous margin weights", "DDfirst market risk", "V6 alternate engine", "HighCAGR24", "10bps one-way original intraday simulation"],
        note="No Ridge forecasts used: this is the ORIGINAL complete V2 fullstack including its original ExtraTrees XGB Titanic, not a new Ridge stack.",
        study_window="101 calendar month signals Jan2018-May2026",
        no_new_training=True,
        warning="non-virgin historical backtest, exploratory; 500 baskets highly correlated, use calendar time blocks",
        target_production_change=False)
    (out/"MANIFEST.json").write_text(json.dumps(record,indent=2))
    print("FULLSTACK_CANONICAL500_PARITY_AND_VETO_ALL_PASS",flush=True)
if __name__=="__main__":main()
