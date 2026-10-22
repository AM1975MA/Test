#!/usr/bin/env python3
"""L11.W1 original source-only 500 matched V2 reference; evaluate new policies ONLY on five ETFs chosen before risk screening. Original
Causal, original weekly next-open Top2-weight/risk overlay. Full 500 used only to assert exact historical reference, not new strategy test.

Consumes FS02 SOURCE-ONLY generated as-of checkpoint. Not a virgin new fit.
No labels/future ETF returns consumed by decisions. Fail closed on exact
replay parity of both BASE and documented original ETF_TRAINER_V2 Stage19.
"""
from __future__ import annotations
import argparse,hashlib,io,json,math,sys
from pathlib import Path
import numpy as np,pandas as pd

WANT_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
REF_500_CAGR=.2217716371734245
REF_STAGE19_CAGR=.2245930412878681

def metrics(E,mask):
    mask=np.asarray(mask,bool)
    ln=np.diff(np.log(np.column_stack([np.ones(E.shape[0]),E])),axis=1)[:,mask]
    rr=np.expm1(ln);N=rr.shape[1]
    cagr=np.expm1(ln.sum(axis=1)*252/N)
    nav=np.exp(ln.cumsum(axis=1))
    hi=np.maximum.accumulate(np.column_stack([np.ones(len(E)),nav]),axis=1)[:,1:]
    dd=(nav/hi-1).min(axis=1)
    sd=rr.std(axis=1,ddof=1)
    sh=np.divide(rr.mean(axis=1)*np.sqrt(252),sd,out=np.zeros_like(sd),where=sd>0)
    n=nav.mean(axis=0)
    agg=np.mean(np.expm1(ln.sum(axis=1))) # informational, not aggregate CAGR
    return dict(cagr_mean=float(cagr.mean()),cagr_median=float(np.median(cagr)),
                cagr_p10=float(np.quantile(cagr,.1)),
                maxdd_mean=float(dd.mean()),maxdd_worst=float(dd.min()),
                sharpe_mean=float(sh.mean()),
                aggregate_nav_cagr=float(n[-1]**(252/N)-1),
                basket_positive_return_rate=float((cagr>0).mean()))

def boot(Ea,Eb,mask,seed=20261022,reps=3000,block=21):
    r1=np.diff(np.log(np.column_stack([np.ones(Ea.shape[0]),Ea])),axis=1)[:,mask]
    r2=np.diff(np.log(np.column_stack([np.ones(Eb.shape[0]),Eb])),axis=1)[:,mask]
    x=(r2-r1).mean(axis=0)
    n=len(x);rng=np.random.default_rng(seed)
    ix=((rng.integers(0,n,size=(reps,math.ceil(n/block)))[:,:,None]+
          np.arange(block))%n).reshape(reps,-1)[:,:n]
    bs=x[ix].mean(axis=1)*252
    return dict(annualized_calendar_mean_logalpha=float(x.mean()*252),
          lower95=float(np.quantile(bs,.025)),upper95=float(np.quantile(bs,.975)),
          reps=reps,trading_day_block=block,common_days=n)

def main():
    a=argparse.ArgumentParser()
    for x in ("raw","fs02-path","fs02-result","fs02-pred","pair","baskets","out"):
        a.add_argument("--"+x,required=True)
    q=a.parse_args()
    out=Path(q.out);out.mkdir(parents=True,exist_ok=True)
    if hashlib.sha256(Path(q.baskets).read_bytes()).hexdigest()!=WANT_SHA:
        raise RuntimeError("CANONICAL BASKET SHA CHANGE")
    prior=json.loads(Path(q.fs02_result).read_text())
    assert prior["contract"]["titanium_maturity_safe"]
    assert prior["contract"]["cluster_source_causal"]
    assert prior["contract"]["ensemble_maturity_safe"]
    assert prior["contract"]["basket_sha256"]==WANT_SHA
    assert abs(prior["metrics"]["full"]["highcagr24"]["cagr"]-REF_500_CAGR)<1e-11
    assert abs(prior["metrics"]["full"]["etf_trainer_v2_risk_conviction"]["cagr"]-REF_STAGE19_CAGR)<1e-11
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/"src"))
    from etf_trader.source_only.raw_io import load_ticker_csv_folder
    from etf_trader.ma3 import ddfirst,v6
    raw,cats,_=load_ticker_csv_folder(q.raw)
    p=np.load(q.fs02_path,allow_pickle=True)
    ds=pd.DatetimeIndex(p["dates"])
    tickers=list(map(str,p["tickers"]))
    assert len(tickers)==149 and len(ds)==2366
    assert list(raw["Open"].columns)==tickers
    old_choice=p["d1"];old_second=p["d2"]
    old_w=p["wg"];margin=p["margin"]
    macro_gross=p["global_gross"];alt=p["alt_idx"]
    assert old_choice.shape==old_second.shape==old_w.shape==margin.shape==(500,len(ds))
    assert macro_gross.shape==(len(ds),)
    Odf=raw["Open"].reindex(columns=tickers).ffill().bfill()
    Ldf=raw["Low"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    Cdf=raw["Close"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    Odf=Odf.loc[:ds[-1]];Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index)
    st=int(Odf.index.get_loc(ds[0]));en=int(Odf.index.get_loc(ds[-1]))
    assert Odf.index[st:en+1].equals(ds)
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
       ex[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    bi=tickers.index("BIL");sh=tickers.index("SHV")
    # Recreate exact original SOURCE-ONLY daily baseline first.
    Ebase,Tbase,_,_=v6.simulate_with_alt(
        old_choice,old_second,old_w,O,L,C,PC,gap,ud1,uneg,UH,SA,
        bi,sh,macro_gross,alt,True,.001)
    np.testing.assert_allclose(Ebase,p["equity"],atol=1e-10,rtol=0)
    np.testing.assert_allclose(Tbase,p["turnover"],atol=1e-10,rtol=0)
    # Source-generated frozen historical tail component scores, no model refits.
    pred=pd.read_csv(q.fs02_pred,parse_dates=["signal_date"])
    assert len(pred)==16986 and pred.ticker.nunique()==149 and pred.signal_date.nunique()==114
    months=sorted(pd.Timestamp(x) for x in pred.signal_date.unique())
    def mat(k):
        return pred.pivot(index="signal_date",columns="ticker",values=k).reindex(
                   index=months,columns=tickers).to_numpy(float)
    et=mat("ET_TAIL");xgb=mat("XGB_TAIL")
    assert np.isfinite(et).all() and np.isfinite(xgb).all()
    v3=pd.read_csv(q.pair,parse_dates=["signal_date"])
    v3=v3.loc[v3.variant.eq("CORRECTED"),["signal_date","ticker","pred"]].copy()
    assert len(v3)==149*102 and v3.signal_date.nunique()==102
    assert not v3.duplicated(["signal_date","ticker"]).any()
    v3by={pd.Timestamp(dt):g.set_index("ticker").pred.rank(method="average",pct=True).reindex(tickers).to_numpy(float)
          for dt,g in v3.groupby("signal_date")}
    all_agree=np.zeros_like(old_choice,bool)
    majority=np.zeros_like(old_choice,bool)
    agreement_counts=[]
    for i,signal in enumerate(months):
        a=int(ds.searchsorted(signal,side="right"))
        next_signal=months[i+1] if i+1<len(months) else ds[-1]
        b=int(ds.searchsorted(next_signal,side="right")) if i+1<len(months) else len(ds)
        if a>=len(ds) or b<=a:continue
        first=old_choice[:,a].astype(int);second=old_second[:,a].astype(int)
        assert (first>=0).all() and (second>=0).all()
        e1=et[i,first]>et[i,second]
        e2=xgb[i,first]>xgb[i,second]
        two=e1&e2
        if signal in v3by:
            z=v3by[signal]
            assert np.isfinite(z).all()
            e3=z[first]>z[second]
            m=(e1&e2)|(e1&e3)|(e2&e3)
        else:
            m=two # no V3 OOS prediction, no invented pre-2018 value
        all_agree[:,a:b]=two[:,None]
        majority[:,a:b]=m[:,None]
        agreement_counts.append(dict(signal_date=str(signal.date()),
                  eligible_pairs=int((e1|e2).sum()),ET_XGB_agree=int(two.sum()),
                  majority_with_V3=int(m.sum()),V3_OOS_available=signal in v3by))
    eligible=(macro_gross[None,:]<.999)&(margin>=.03)
    action2=eligible&all_agree
    action3=eligible&majority
    # The two-source agreement must be subset of majority, on every day.
    assert not np.any(action2&~action3)
    weight2=old_w.copy();weight2[action2]=1.
    weight3=old_w.copy();weight3[action3]=1.
    E2,T2,_,_=v6.simulate_with_alt(
        old_choice,old_second,weight2,O,L,C,PC,gap,ud1,uneg,UH,SA,
        bi,sh,macro_gross,alt,True,.001)
    # Must EXACTLY regenerate archived original ETF_TRAINER_V2 risk arm.
    np.testing.assert_allclose(E2,p["etf_trainer_v2_equity"],atol=1e-10,rtol=0)
    np.testing.assert_allclose(T2,p["etf_trainer_v2_turnover"],atol=1e-10,rtol=0)
    E3,T3,_,_=v6.simulate_with_alt(
        old_choice,old_second,weight3,O,L,C,PC,gap,ud1,uneg,UH,SA,
        bi,sh,macro_gross,alt,True,.001)
    # Baseline original 500 reconciled exactly; new weekly risk policies
    # run ONLY on the preregistered five representative baskets.
    sys.path.insert(0,str(root/"experiments"))
    from l11_weekly_v6 import simulate_with_weekly_overlay
    selection=[227,69,327,301,220]
    ia=np.array(selection,int)
    base_d1=old_choice[ia].copy()
    base_d2=old_second[ia].copy()
    wbase=weight2[ia].copy()
    dd=margin[ia].copy()
    alt5=alt[ia].copy()
    B=len(selection);D=len(ds)
    risk_original=np.ones((B,D),float)
    verified,verified_turn,_,_=simulate_with_weekly_overlay(
       base_d1,base_d2,wbase,wbase,risk_original,
       O,L,C,PC,gap,ud1,uneg,UH,SA,bi,sh,macro_gross,alt5,True,.001)
    np.testing.assert_allclose(verified,E2[ia],atol=1e-10,rtol=0)
    np.testing.assert_allclose(verified_turn,T2[ia],atol=1e-10,rtol=0)
    # Align signal histories with the full historical OHLCV calendar,
    # shift(1) means new Monday open may see ONLY prior session closes.
    ret21=(Cdf/Cdf.shift(21)-1).shift(1).to_numpy(float)[st:en+1]
    ret5=(Cdf/Cdf.shift(5)-1).shift(1).to_numpy(float)[st:en+1]
    peak63=Cdf.rolling(63,min_periods=63).max().shift(1).to_numpy(float)[st:en+1]
    prevclose=Cdf.shift(1).to_numpy(float)[st:en+1]
    dd63=prevclose/peak63-1
    all_close_log=np.diff(np.log(Cdf.to_numpy(float)),axis=0)
    weeks=ds.isocalendar()
    weekcodes=np.asarray(weeks.year*100+weeks.week)
    starts=np.flatnonzero(np.r_[True,weekcodes[1:]!=weekcodes[:-1]])
    assert len(starts)>=450
    names=["WEEKLY_BALANCED_DOWNTREND","WEEKLY_RELATIVE_ROTATION",
           "WEEKLY_TAIL_THEN_RECOVERY"]
    policies={n:{"risk":np.ones((B,D),float),"weight":wbase.copy(),"events":[]} for n in names}
    state=np.ones(B)
    for b,basket in enumerate(selection):
        for si,k in enumerate(starts):
            end=starts[si+1] if si+1<len(starts) else D
            # A monthly V2 name update inside a week must NOT inherit
            # a stale overlay generated for last month's Top1/Top2.
            changes=np.flatnonzero((base_d1[b,k+1:end]!=base_d1[b,k:end-1])|
                      (base_d2[b,k+1:end]!=base_d2[b,k:end-1]))
            if len(changes):end=k+1+int(changes[0])
            if end<=k:continue
            t1=int(base_d1[b,k]);t2=int(base_d2[b,k])
            w=float(wbase[b,k])
            r1=ret21[k,t1];r2=ret21[k,t2]
            d1r=dd63[k,t1];d2r=dd63[k,t2]
            rr1=ret5[k,t1];rr2=ret5[k,t2]
            if not np.isfinite([r1,r2,d1r,d2r,rr1,rr2]).all():continue
            corr=np.nan
            g=st+k
            if g>=64:
                x=all_close_log[g-63:g,t1];y=all_close_log[g-63:g,t2]
                if np.std(x)>0 and np.std(y)>0:
                    corr=float(np.corrcoef(x,y)[0,1])
            ret=w*r1+(1-w)*r2
            ret5w=w*rr1+(1-w)*rr2
            # A: original monthly names, correlated risk after downturn.
            if np.isfinite(corr) and ret<=-.05 and corr>=.65:
                policies[names[0]]["risk"][b,k:end]=.6
                policies[names[0]]["events"].append((basket,str(ds[k].date()),
                    tickers[t1],tickers[t2],float(ret),float(corr),".6"))
            # B: original monthly names, weekly relative strength,
            # respect original Stage19 riskoff Top1 conviction daily.
            if (not action2[basket,k]) and abs(r1-r2)>.08 and max(r1,r2)>0:
                nw=.8 if r1>r2 else .2
                z=np.full(end-k,nw)
                z[action2[basket,k:end]]=wbase[b,k:end][action2[basket,k:end]]
                policies[names[1]]["weight"][b,k:end]=z
                policies[names[1]]["events"].append((basket,str(ds[k].date()),
                    tickers[t1],tickers[t2],float(r1),float(r2),str(nw)))
            # C: weekly recovery (no lookahead), original risky sleeve
            # temporarily reduced, no synthetic short positions.
            if state[b]<1:
                if ret5w>.02 and ret>-.02:state[b]=1.
            elif ret<=-.06 and min(d1r,d2r)<=-.15:
                state[b]=.5
            if state[b]<1:
                policies[names[2]]["risk"][b,k:end]=state[b]
                policies[names[2]]["events"].append((basket,str(ds[k].date()),
                    tickers[t1],tickers[t2],float(ret),float(ret5w),str(state[b])))
    def score(E,T):
        c=np.expm1(np.log(E[:,-1])*252/D)
        peak=np.maximum.accumulate(np.column_stack([np.ones(B),E]),axis=1)[:,1:]
        dd=(E/peak-1).min(axis=1)
        logret=np.diff(np.log(np.column_stack([np.ones(B),E])),axis=1)
        sharpe=logret.mean(axis=1)*np.sqrt(252)/logret.std(axis=1,ddof=1)
        return c,dd,sharpe,T.mean(axis=1)*252
    navs={"V2_STAGE19":verified}
    s0=score(verified,verified_turn)
    rows=[]
    for name in ["V2_STAGE19"]+names:
        pol=(dict(risk=risk_original,weight=wbase,events=[]) if name=="V2_STAGE19" else policies[name])
        if name=="V2_STAGE19":E,T=verified,verified_turn
        else:
            E,T,_,_=simulate_with_weekly_overlay(
                base_d1,base_d2,wbase,pol["weight"],pol["risk"],
                O,L,C,PC,gap,ud1,uneg,UH,SA,bi,sh,macro_gross,alt5,True,.001)
        navs[name]=E
        m=score(E,T)
        for j,basket in enumerate(selection):
            rows.append(dict(policy=name,basket=basket,
                n_weekly_policy_events=sum(int(z[0]==basket) for z in pol["events"]),
                cagr=float(m[0][j]),maxdd=float(m[1][j]),
                sharpe=float(m[2][j]),turnover_ann=float(m[3][j]),
                delta_cagr_pp=float(100*(m[0][j]-s0[0][j])),
                delta_maxdd_pp=float(100*(m[1][j]-s0[1][j]))))
        if name!="V2_STAGE19":
            pd.DataFrame(pol["events"],columns=["basket","weekly_effective_session",
              "etf_1","etf_2","diagnostic_1","diagnostic_2","policy_strength"]).to_csv(
               out/(name+"_WEEKLY_DECISION_AUDIT.csv"),index=False)
    tab=pd.DataFrame(rows)
    tab.to_csv(out/"FIVE_BASKETS_EXACT_WEEKLY_SCORES.csv",index=False)
    np.savez_compressed(out/"FIVE_BASKETS_DAILY_NAV.npz",
                        dates=ds.values,baskets=ia,**navs)
    result=tab.groupby("policy").agg(cagr=("cagr","mean"),
        maxdd=("maxdd","mean"),turnover=("turnover_ann","mean"),
        delta_cagr_pp=("delta_cagr_pp","mean"),
        delta_maxdd_pp=("delta_maxdd_pp","mean")).reset_index()
    # Fail closed against prior stand-alone source-only 5-basket calculation.
    reference={"V2_STAGE19":.22446978024908676,
        "WEEKLY_BALANCED_DOWNTREND":.2174032499758562,
        "WEEKLY_RELATIVE_ROTATION":.19053596503921183,
        "WEEKLY_TAIL_THEN_RECOVERY":.1993948158853373}
    for key,target in reference.items():
        value=float(result.loc[result.policy.eq(key),"cagr"].iloc[0])
        assert abs(value-target)<1e-9,(key,value,target)
    metadata=dict(status="FIVE_SCREEN_NEGATIVE_NO_500_VETO_EXTENSION",
        original_full_500_baseline_replay_exact=True,
        original_full_500_Stage19_replay_exact=True,
        modified_weekly_executor_five_NAV_and_turnover_exact=True,
        source_snapshot_run=39482809691,
        source_only_original_v2_500_run=39836842157,
        original_FS03_500_path_run=39838818618,
        n_full_source_ETFs=149,n_canonical_baskets=500,
        n_NEW_tested_baskets=5,selected_ids=selection,
        n_sessions=D,first_signal_only_previous_session_close=True,
        source_monthly_Top2_unmodified=True,
        weekly_next_open_rebalance=True,
        monthly_intraweek_name_change_cancels_stale_overlay=True,
        stage19_original_riskoff_priority=True,
        one_way_cost_bps=10,original_intraday_stop_slippage_and_V6_alt=True,
        LME_independent_market_not_in_raw_149=True,
        no_500_extension_triggered=True,nonvirgin_history=True,
        production_V2_and_V3_unchanged=True)
    (out/"MANIFEST.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print("L11_WEEKLY_FIVE\n"+tab.to_string(index=False),flush=True)
    print("L11_WEEKLY_SUMMARY\n"+result.to_string(index=False),flush=True)
    print("L11_WEEKLY_MANIFEST "+json.dumps(metadata),flush=True)

if __name__=="__main__":
    main()
