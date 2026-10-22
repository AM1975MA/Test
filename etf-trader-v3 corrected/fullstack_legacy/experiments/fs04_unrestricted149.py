#!/usr/bin/env python3
"""FS04 exact-source single unrestricted 149 ETF full-stack portfolio.

No fitting, no new model. Reconstruct frozen source-only 114 monthly original
V2 hybrid score from archived FS02 source-generated ET/XGB/Titanium signals,
assert all original FS02 500-basket daily original holdings and gross reference.
Then trade same V2 Top2 on SINGLE 149 ETF basket with original V2 daily
intraday simulator and fee 10bps. Compare risk-off V2 ET/XGB conviction and
a frozen majority (ET/XGB/V3 Pair127) vote. All decisions as-of past.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def metrics(equity,turn,mask):
    m=np.asarray(mask,bool)
    L=np.diff(np.log(np.r_[1.,np.asarray(equity).reshape(-1)]))[m]
    n=len(L)
    ar=np.expm1(L)
    nav=np.exp(L.cumsum());pk=np.maximum.accumulate(np.r_[1.,nav])[1:]
    d=nav/pk-1.
    return dict(cagr=float(np.expm1(L.sum()*252/n)),
      maxdd=float(d.min()),sharpe_rf0=float(ar.mean()*np.sqrt(252)/ar.std(ddof=1)) if ar.std(ddof=1)>0 else 0.,
      annualized_trade_notional=float(np.asarray(turn).reshape(-1)[m].mean()*252),
      n_days=n,terminal_NAV_return=float(nav[-1]-1))

def main():
    ap=argparse.ArgumentParser()
    for key in ("raw","fs02-path","fs02-result","fs02-pred","baskets","pair","out"):
        ap.add_argument("--"+key,required=True)
    z=ap.parse_args();out=Path(z.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(z.baskets).read_bytes()).hexdigest()==SHA
    origin=json.loads(Path(z.fs02_result).read_text())
    assert origin["contract"]["titanium_maturity_safe"] and origin["contract"]["cluster_source_causal"] and origin["contract"]["ensemble_maturity_safe"]
    assert origin["contract"]["basket_sha256"]==SHA
    assert abs(origin["metrics"]["full"]["etf_trainer_v2_risk_conviction"]["cagr"]-.2245930412878681)<1e-10
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/"src"))
    from etf_trader.source_only.raw_io import load_ticker_csv_folder
    from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
    mats,cats,manifest=load_ticker_csv_folder(z.raw)
    prior=np.load(z.fs02_path,allow_pickle=True)
    ds=pd.DatetimeIndex(prior["dates"])
    names=list(map(str,prior["tickers"]));N=len(names)
    assert N==149 and len(ds)==2366
    assert list(mats["Open"].columns)==names
    preds=pd.read_csv(z.fs02_pred,parse_dates=["signal_date"])
    assert preds.signal_date.nunique()==114 and preds.ticker.nunique()==149
    months=pd.DatetimeIndex(sorted(preds.signal_date.unique()))
    def panel(name):
        return preds.pivot(index="signal_date",columns="ticker",values=name).reindex(index=months,columns=names).to_numpy(float)
    base=panel("BASE");et=panel("ET_TAIL");xgb=panel("XGB_TAIL")
    tail=panel("TAIL_HYBRID")
    assert np.allclose(tail,.6*et+.4*xgb,atol=1e-12,rtol=0)
    lag1=np.vstack([tail[:1],tail[:-1]])
    lag2=np.vstack([tail[:1],tail[:1],tail[:-2]])
    score=.475*base+.525*np.power(np.clip(.4*tail+.3*lag1+.3*lag2,0,1),1.1)
    assert np.isfinite(score).all() and score.shape==(114,149)
    # Exact SOURCE_ONLY reference 500-basket original original holdings are
    # regenerated from OOS scores and matched per-day before 149-global test.
    original_baskets=pd.read_csv(z.baskets)
    assert len(original_baskets)==12000
    ticker_pos={t:i for i,t in enumerate(names)}
    # Use EXACT original source group order. Sorting ticker names can alter
    # stable/argpartition ordering for ties even when memberships are identical.
    bm,BOK=producer.basket_arrays(original_baskets,names,n_baskets=500)
    assert bm.shape==BOK.shape==(500,24) and BOK.all()
    days=pd.DatetimeIndex(mats["Open"].index)
    ent=[days[days.searchsorted(sig,side="right")] for sig in months]
    assert ent[0]==ds[0] and ent[-1]==ds[-1]
    exit_dates=ent[1:]+[ds[-1]+pd.Timedelta(days=1)]
    cal=pd.DataFrame({"signal_date":months,"entry_date":ent,"exit_date":exit_dates})
    prior500=producer.allocations_from_score(score,cal,ds,bm,BOK,continuous=True)
    np.testing.assert_array_equal(prior500.d1,prior["d1"])
    np.testing.assert_array_equal(prior500.d2,prior["d2"])
    # PATH.wg is the HighCAGR24 TRANSFORMED allocation, not the raw
    # continuous producer.weight1. Compare after applying the exact source
    # gross + selected-weight transform below.
    np.testing.assert_allclose(prior500.margin,prior["margin"],atol=1e-12,rtol=0)
    # Original systemic prior-close risk is identical to the original reference.
    Odf=mats["Open"].reindex(columns=names).ffill().bfill()
    Ldf=mats["Low"].reindex(columns=names).ffill().bfill().reindex(Odf.index)
    Cdf=mats["Close"].reindex(columns=names).ffill().bfill().reindex(Odf.index)
    Odf=Odf.loc[:ds[-1]];Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index)
    st=int(Odf.index.get_loc(ds[0]));en=int(Odf.index.get_loc(ds[-1]))
    assert Odf.index[st:en+1].equals(ds)
    dd_gross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float)
    gross_ref,corrected_w=highcagr24.apply_highcagr24(dd_gross,prior500.weight1,prior500.margin)
    np.testing.assert_allclose(gross_ref,prior["global_gross"],atol=1e-12,rtol=0)
    np.testing.assert_allclose(corrected_w,prior["wg"],atol=1e-12,rtol=0)
    # Original V2 Top2 selector on one basket containing *all 149 ETFs*.
    ALL=np.arange(149,dtype=np.int32)[None,:]
    alloc=producer.allocations_from_score(score,cal,ds,ALL,np.ones_like(ALL,bool),continuous=True)
    assert alloc.d1.shape==(1,len(ds)) and alloc.d2.shape==(1,len(ds))
    assert np.all(alloc.d1!=alloc.d2)
    G,w_original=highcagr24.apply_highcagr24(dd_gross,alloc.weight1,alloc.margin)
    np.testing.assert_allclose(G,prior["global_gross"],atol=1e-12,rtol=0)
    state=v6.build_v6_state(Cdf.loc[ds,names],alloc.d1,alloc.d2,alloc.weight1,dd_gross)
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    r3=pd.read_csv(z.pair,parse_dates=["signal_date"])
    r3=r3.loc[r3.variant.eq("CORRECTED"),["signal_date","ticker","pred"]]
    assert len(r3)==149*102 and r3.signal_date.nunique()==102
    frozen={pd.Timestamp(sig):g.set_index("ticker")["pred"].rank(method="average",pct=True).reindex(names).to_numpy(float)
         for sig,g in r3.groupby("signal_date")}
    et_xgb=np.zeros_like(alloc.d1,bool);majority=np.zeros_like(alloc.d1,bool)
    summaries=[]
    for i,sig in enumerate(months):
        a=int(ds.searchsorted(ent[i]))
        b=int(ds.searchsorted(exit_dates[i]))
        if a>=len(ds) or b<=a:continue
        old=int(alloc.d1[0,a]);runner=int(alloc.d2[0,a])
        e1=bool(et[i,old]>et[i,runner]);e2=bool(xgb[i,old]>xgb[i,runner])
        old_cons=e1 and e2
        if sig in frozen:
            pred=frozen[sig];assert np.isfinite(pred).all()
            e3=bool(pred[old]>pred[runner])
            accept=(e1 and e2) or (e1 and e3) or (e2 and e3)
        else:
            e3=None
            accept=old_cons
        et_xgb[:,a:b]=old_cons
        majority[:,a:b]=accept
        summaries.append(dict(signal_date=str(sig.date()),incumbent_top1=names[old],original_top2=names[runner],
                  score_margin=float(alloc.margin[0,a]),
                  vote_ET=int(e1),vote_XGB=int(e2),
                  vote_V3=None if e3 is None else int(e3),
                  original_model_consensus=int(old_cons),new_majority=int(accept),
                  causal_frozen_V3_available=sig in frozen))
    np.testing.assert_array_equal(et_xgb&~majority,np.zeros_like(et_xgb))
    eligible=(G[None,:]<.999)&(alloc.margin>=.03)
    w_stage19=w_original.copy();w_stage19[eligible&et_xgb]=1.
    w_majority=w_original.copy();w_majority[eligible&majority]=1.
    arrays={}
    for label,w in (("HYBRID24_ORIGINAL",w_original),("ETF_TRAINER_V2",w_stage19),("V3_MAJORITY2OF3",w_majority)):
        equity,turnover,_,_=v6.simulate_with_alt(
             alloc.d1,alloc.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,
             names.index("BIL"),names.index("SHV"),G,state.alt_idx,True,.001)
        assert equity.shape==turnover.shape==(1,len(ds)) and np.isfinite(equity).all()
        arrays[label]=(equity[0],turnover[0])
    masks={"FULL":np.ones(len(ds),bool),
          "DEVELOPMENT_2017_2022":ds<pd.Timestamp("2023-01-01"),
          "LATER_2023_2026":ds>=pd.Timestamp("2023-01-01"),
          "COMMON_2018_2026":ds>=pd.Timestamp("2018-02-01"),
          "COMMON_2022_2026":ds>=pd.Timestamp("2022-02-01")}
    scorecard=[]
    for window,mask in masks.items():
        for model,(eq,turn) in arrays.items():
            scorecard.append(dict(window=window,arm=model,**metrics(eq,turn,mask)))
    yearly=[]
    for yr in sorted(ds.year.unique()):
        mask=ds.year==yr
        for arm,(equity,turnover) in arrays.items():
            yearly.append(dict(year=int(yr),arm=arm,**metrics(equity,turnover,mask)))
    pd.DataFrame(scorecard).to_csv(out/"ECONOMIC_SCORECARD.csv",index=False)
    pd.DataFrame(yearly).to_csv(out/"YEARLY.csv",index=False)
    pd.DataFrame(summaries).to_csv(out/"ORIGINAL_TOP2_ASOF_MONTHLY.csv",index=False)
    pd.DataFrame({"date":ds,"market_risk_gross":G,
             "original_ET_XGB_concentration":(eligible&et_xgb).sum(axis=0),
             "V3_2OF3_concentration":(eligible&majority).sum(axis=0)}).to_csv(out/"ASOF_DAILY_RISK.csv",index=False)
    pd.DataFrame({"date":ds,**{x:arrays[x][0] for x in arrays}}).to_csv(out/"DAILY_NAV.csv",index=False)
    metadata=dict(strategy="UNRESTRICTED_SINGLE_149_ETF_FULL_HYBRID24",
      causal_frozen_source_only_Titanium_Hybrid24_S3B_run=39836842157,
      n_total_tickers=149,n_economic_baskets=1,n_months=len(months),trading_days=len(ds),
      original_500_basket_Top2_and_weights_exact_parity=True,
      original_500_basket_risk_gross_exact_parity=True,
      frozen_original_500_Hybrid24_source_only_reproduced=True,
      original_ETF_TRAINER_V2_rank_unchanged=True,
      future_outcomes_used_for_decisions=False,original_ranker_refitted=False,
      fee_bps_one_way=10,
      full_vintage_current_raw=True,old_43pct_snapshot_not_identical=True,
      source_experiment_run=39836842157,
      v3_pair_frozen_run=39700865721,
      original_500_basket_sha256=SHA,
      original_prod_unchanged=True)
    (out/"MANIFEST.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print("FS04_GLOBAL149_SCORECARD\n"+pd.DataFrame(scorecard).to_string(index=False),flush=True)
    print("FS04_GLOBAL149_META "+json.dumps(metadata),flush=True)

if __name__=="__main__":main()
