#!/usr/bin/env python3
"""FS03 controlled downstream-only replay: same V2 selected ETFs, original
HighCAGR24 macro risk, plus E3 frozen rank as optional third risk-off vote.

Consumes FS02 SOURCE-ONLY generated as-of checkpoint. Not a virgin new fit.
No labels/future ETF returns consumed by decisions. Fail closed on exact
replay parity of both BASE and documented original ETF_TRAINER_V2 stage19.
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
    windows={
       "FULL_2017_2026":np.ones(len(ds),bool),
       "DEV_2017_2022":ds<pd.Timestamp("2023-01-01"),
       "LATER_2023_2026":ds>=pd.Timestamp("2023-01-01"),
       "COMMON_2018_2026":ds>=pd.Timestamp("2018-02-01"),
       "COMMON_2022_2026":ds>=pd.Timestamp("2022-02-01"),
    }
    arms={"V2_HYBRID24":(Ebase,Tbase),"ETF_TRAINER_V2":(E2,T2),
          "V3_MAJORITY2OF3":(E3,T3)}
    scored=[];boot=[];annual=[]
    for label,mask in windows.items():
        for arm,(nav,turn) in arms.items():
            scored.append({"window":label,"arm":arm,**metrics(nav,mask),
                 "annualized_trade_notional":float(turn[:,mask].mean()*252)})
        for arm in ("V2_HYBRID24","ETF_TRAINER_V2"):
            boot.append({"window":label,"trial":"V3_MAJORITY2OF3","control":arm,
                         **globals()["boot"](arms[arm][0],E3,mask)})
    R={arm:np.diff(np.log(np.column_stack([np.ones(500),nav])),axis=1)
       for arm,(nav,_) in arms.items()}
    for y in sorted(ds.year.unique()):
        m=ds.year==y
        for arm in arms:
            outret=np.expm1(R[arm][:,m].sum(axis=1))
            annual.append({"year":int(y),"arm":arm,
                 "mean_500_basket_calendar_return":float(outret.mean())})
    pd.DataFrame(scored).to_csv(out/"ECONOMIC_SCORECARD.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"YEARLY.csv",index=False)
    pd.DataFrame(boot).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    pd.DataFrame(agreement_counts).to_csv(out/"MONTHLY_MODEL_AGREEMENTS.csv",index=False)
    pd.DataFrame({"date":ds,"eligible_baskets":eligible.sum(axis=0),
      "original_ETF_TRAINER_V2_actions":action2.sum(axis=0),
      "V3_2of3_actions":action3.sum(axis=0)}).to_csv(out/"DAILY_ACTION_AUDIT.csv",index=False)
    np.savez_compressed(out/"PATH.npz",dates=ds.values,equity_baseline=Ebase,
             equity_stage19=E2,equity_majority=E3,turnover_majority=T3)
    meta=dict(status="EXPLORATORY_NO_PROMOTION",source_only_input_run=39836842157,
      source_only_risk_artifact="v3-fullstack-model-agreement-500",
      raw_input_run=39482809691,frozen_pair_run=39700865721,n_etfs=149,n_baskets=500,
      n_months=len(months),risk_gross_unchanged=True,selection_names_unchanged=True,
      original_V2_daily_NAV_exact_parity=True,original_ETF_TRAINER_V2_daily_NAV_exact_parity=True,
      label_and_future_return_not_used_in_sizing=True,
      matched_fee_one_way_bps=10,
      date_start=str(ds.min().date()),date_end=str(ds.max().date()),
      original_riskoff_confirmed_action_basket_days=int(action2.sum()),
      majority_2of3_action_basket_days=int(action3.sum()),
      increment_new_basket_days=int((action3&~action2).sum()),
      no_bps_or_threshold_search=True,production_unchanged=True)
    (out/"MANIFEST.json").write_text(json.dumps(meta,indent=2)+"\n")
    print("FS03_SCORECARD\n"+pd.DataFrame(scored).to_string(index=False),flush=True)
    print("FS03_BOOTSTRAP\n"+pd.DataFrame(boot).to_string(index=False),flush=True)
    print("FS03_MANIFEST "+json.dumps(meta),flush=True)

if __name__=="__main__":main()
