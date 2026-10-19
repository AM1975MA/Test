#!/usr/bin/env python3
"""Full original US149 ETF Trader MA3 and ADAPT4 single-149-universe test.

No original 500 balanced24-basket method. True genuinely refitted TIT/MA3
2021–2026 forecasts from original archived US149 OHLCV. ADAPT4 locked European
protocol imported by reference (13 features + Ridge36 + monthly 12 mature
reward + temperature4 + floor10%). One 149x1 candidate opportunity set.
All US ETF source V6/DD original unaltered, SPY HYG IEF BIL SHV used as in source.
"""
from __future__ import annotations
import argparse,os,sys,json,inspect,importlib.util
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from etf_trader.source_only import kernel as k
from etf_trader.source_only import features as feature_module
from etf_trader.source_only.models import fit_predict,variants
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from etf_trader.ma3.hybrid_producer import fit_hybrid_producer
from europe_only75.f3h1_original_transfer.run import costed_path
from isin_first2026.predict48.tournament import RAWFEATURES,rank,boot,sha
from isin_first2026.v2_unrestricted48.run import evaluate
from research_reset.us149_adapt4_free.prepare import prepare

ROOT=Path(__file__).resolve().parents[2]
EXPERTS=("ORIGINAL_MA3","MOM21","MOM126","RIDGE_RECENT36M")
MODEL_WINDOW=12
SOFTMAX_TEMPERATURE=4.
EXPERT_FLOOR=.10
COST=.001

def fit_source_titanium(raw,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    os.environ["ETF_TRADER_XGB_WORKERS"]="2"
    os.environ["ETF_TRADER_XGB_THREADS_PER_WORKER"]="1"
    mats,cats,manifest=load_ticker_csv_folder(raw)
    names=list(mats["Close"])
    assert len(names)==149
    k.ALL_TICKERS=sorted(names)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted([t for t in names if cats[t]==c]) for c in set(cats.values())}
    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats)
    compact=compact[compact.signal_date.isin(dates)].copy()
    tail=tail[tail.signal_date.isin(dates)].copy()
    compact=k.add_labels(compact,mats["Open"],dates)
    tail=k.add_labels(tail,mats["Open"],dates)
    unlabelled=tail.drop(columns=[c for c in tail if
        c.startswith(("fwd_","target_","exit_")) or c in ["entry_date","y_tailmix"]])
    macro,mfeatures=k.build_macro_panel(unlabelled,tail)
    extra=feature_module.build(mats,cats,dates)
    print("US149_TITANIUM_ORIGINAL_US_SPY_FEATURES_AND_FITS",len(names),len(compact),flush=True)
    pred=fit_predict(k,compact,tail,macro,mfeatures,extra,
        out/"annual_models",years=range(2021,2027))
    pred=pred[(pred.signal_date>="2021-01-01")&
              (pred.signal_date<="2026-06-30")].copy()
    s=variants(pred)["baseline"].rename(columns={"score":"TIT_R"})
    cal=pred[["signal_date","ticker","entry_date","exit_date"]].drop_duplicates(["signal_date","ticker"])
    schedule=s.merge(cal,on=["signal_date","ticker"],validate="one_to_one")
    schedule=schedule[["signal_date","entry_date","exit_date","ticker","TIT_R"]]
    schedule=schedule[schedule.exit_date.notna()].sort_values(["signal_date","ticker"])
    assert schedule.ticker.nunique()==149
    assert schedule.signal_date.nunique()==65,(schedule.signal_date.nunique(),schedule.signal_date.drop_duplicates().tail())
    assert schedule.groupby("signal_date").ticker.nunique().eq(149).all()
    schedule.to_csv(out/"TIT_R_FULL149_SOURCE_REFITTED.csv",index=False)
    audit=sorted((out/"annual_models").glob("fit_audit_*.json"))
    assert len(audit)==6
    manifest2=dict(raw_manifest=manifest,annual_retrain_details=[json.loads(p.read_text()) for p in audit],
       status="REAL_ORIGINAL_US149_TITANIUM_2021_2026_FULL_RANK_FIT",
       n_tradable_candidates=149,no_500_baskets=True,n_signal_months=65,
       source_US149_archived_ohlcv_only=True,original_SPY_HYG_IEF_as_source=True)
    (out/"MANIFEST.json").write_text(json.dumps(manifest2,indent=2,default=str)+"\n")
    return schedule

def build_real_ma3(raw,titanium,out,names):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    builder=ROOT/"vendor/etf_trader_v2/scripts/build_ma3_panel_source_only.py"
    spec=importlib.util.spec_from_file_location("original_US149_source_ma3_builder",builder)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    saved=list(sys.argv)
    try:
        sys.argv=[str(builder),"--data",str(raw),"--output",str(out/"MA3_SOURCE_RAW_FEATURE_PANEL")]
        result=mod.main()
        assert result==0
    finally:
        sys.argv=saved
    panel=pd.read_pickle(out/"MA3_SOURCE_RAW_FEATURE_PANEL/RAW_FEATURE_PANEL.pkl")
    assert panel.ticker.nunique()==149,(panel.ticker.nunique(),panel.ticker.unique())
    p=fit_hybrid_producer(panel,titanium,names,
           start_year=2021,end_year=2026,et_n_jobs=2,xgb_n_jobs=2)
    assert p.fit_audit.maturity_ok.all() and len(p.fit_audit)==6
    assert p.score.shape==(65,149)
    assert np.isfinite(p.score).all()
    assert len(p.calendar)==65
    p.predictions.to_csv(out/"FULL149_MA3_HYBRID24_GENUINE_SOURCE_FORECASTS.csv",index=False)
    p.fit_audit.to_csv(out/"FULL149_MA3_ANNUAL_MATURITY_FIT.csv",index=False)
    return p

def monthly_feature_rows(mats,names,cal,cats):
    # SAME 13 feature names/formulas used in original EUROPE48 tournament.py
    # source-unchanged hyperparameters Ridge=40, last36 matured month labels.
    C=mats["Close"][names];O=mats["Open"][names];log=np.log(C)
    lr=log.diff()
    mom={h:log-log.shift(h) for h in (5,21,63,126,252)}
    v=lr.rolling(63,min_periods=63).std()
    down=lr.clip(upper=0).pow(2).rolling(63,min_periods=63).mean().pow(.5)
    draw=log-log.rolling(126,min_periods=126).max()
    rows=[]
    md=k.month_end_dates(C.index)
    earliest=md[(md>=pd.Timestamp("2017-01-01"))&(md<=pd.Timestamp("2026-05-31"))]
    assert len(earliest)==113
    calall=[]
    for block,signal in enumerate(earliest):
        pos=int(C.index.get_loc(signal))
        nextpos=int(md.searchsorted(signal))+1
        exitpos=int(C.index.get_loc(md[nextpos]))+1
        enter=C.index[pos+1];stop=C.index[exitpos]
        assert signal<enter<stop
        calall.append(dict(block=block,signal_date=signal,entry_date=enter,exit_date=stop))
        fut=np.log(O.loc[stop,names]/O.loc[enter,names])
        assert np.isfinite(fut).all(),(signal,fut[fut.isna()])
        m63=mom[63].loc[signal]
        # category peer excess is invariant to currency and economic sector
        bygrp={g:list(t for t in names if cats[t]==g) for g in set(cats.values())}
        gmean={g:float(m63[tt].mean()) for g,tt in bygrp.items()}
        fx=pd.DataFrame({
           "m5":mom[5].loc[signal],
           "m21":mom[21].loc[signal],
           "m63":m63,
           "m126":mom[126].loc[signal],
           "m252":mom[252].loc[signal],
           "m126_skip21":mom[126].loc[signal]-mom[21].loc[signal],
           "m63_skip5":m63-mom[5].loc[signal],
           "v63":v.loc[signal],
           "down63":down.loc[signal],
           "dd126":draw.loc[signal],
           "r63_excess_europe":m63-m63["SPY"], # same economic market index SPY, no EU proxy
           "r63_bucket_excess":pd.Series({t:float(m63[t]-gmean[cats[t]]) for t in names}),
           "trendrisk63":m63/v.loc[signal].clip(lower=.001)
        },index=names)
        assert tuple(fx.columns)==RAWFEATURES and np.isfinite(fx.to_numpy()).all(),(signal,fx.isna().sum().to_dict())
        ranked=fx.apply(lambda col:pd.Series(rank(col.to_numpy()),index=names),axis=0)
        for t in names:
            row=dict(block=block,signal_date=signal,maturity=stop,ticker=t,
                actual_future_log=float(fut[t]),
                future_excess_equal149=float(fut[t]-fut.mean()))
            for feature in RAWFEATURES:row[feature+"_rank"]=float(ranked.at[t,feature])
            rows.append(row)
    frame=pd.DataFrame(rows)
    assert len(frame)==113*149
    return frame,pd.DataFrame(calall)

def ridge_recent36(frame,cal,names):
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    cols=[z+"_rank" for z in RAWFEATURES]
    index_start=int(cal.index[cal.signal_date>=pd.Timestamp("2021-01-01")].min())
    assert index_start==48
    result=[];audits=[];model=None
    for i in range(index_start,len(cal)):
        signal=pd.Timestamp(cal.loc[i,"signal_date"])
        past=frame[frame.maturity<signal]
        mature=sorted(past.block.unique())
        assert len(mature)>=36 and max(mature)<=i-2
        if model is None or (i-index_start)%3==0:
            recent=past[past.block.isin(mature[-36:])]
            x=recent[cols].to_numpy(float)
            y=recent.future_excess_equal149.clip(-.20,.20).to_numpy(float)
            sc=StandardScaler().fit(x)
            model=Ridge(alpha=40.,fit_intercept=True).fit(sc.transform(x),y)
            audits.append(dict(fit_signal=str(signal.date()),last_train_label_maturity=
                str(recent.maturity.max().date()),distinct_months=36,
                rows=len(recent),prior_only=True,period=str(signal.year)))
        now=frame[frame.block==i].set_index("ticker").loc[names,cols]
        score=model.predict(sc.transform(now.to_numpy(float)))
        assert np.isfinite(score).all()
        result.append(rank(score))
    return np.asarray(result),pd.DataFrame(audits)

def predictive_adapt4(frame,allcal,ma3,names):
    cal=allcal[allcal.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65 and len(ma3.calendar)==65
    assert pd.DatetimeIndex(cal.signal_date).equals(
        pd.DatetimeIndex(ma3.calendar.signal_date))
    base=np.vstack([rank(row) for row in ma3.score])
    r36,audit=ridge_recent36(frame,allcal,names)
    mom21=[];mom126=[];labels=[]
    for row in cal.itertuples(index=False):
        z=frame[frame.block==row.block].set_index("ticker").loc[names]
        mom21.append(np.asarray(z["m21_rank"],float))
        mom126.append(np.asarray(z["m126_rank"],float))
        labels.append(z.actual_future_log.to_numpy(float))
    mom21=np.asarray(mom21);mom126=np.asarray(mom126)
    y=np.asarray(labels)
    assert base.shape==mom21.shape==mom126.shape==r36.shape==y.shape==(65,149)
    ex=np.stack([base,mom21,mom126,r36])
    rewards=np.empty((4,65))
    for e in range(4):
        for i in range(65):
            pred=ex[e,i]
            realized=y[i]
            spearman=float(spearmanr(pred,realized).statistic)
            best=np.argsort(-pred,kind="stable")[:5]
            dispersion=float(realized.std(ddof=1))
            assert dispersion>.000001 and np.isfinite(spearman)
            excess=float(realized[best].mean()-realized.mean())
            rewards[e,i]=.5*spearman+.5*excess/dispersion
    portfolio=[];weight_audit=[]
    for i,row in enumerate(cal.itertuples(index=False)):
        signal=pd.Timestamp(row.signal_date)
        hist=np.where((cal.exit_date.to_numpy()<np.datetime64(signal))&
                       (np.arange(len(cal))<i))[0][-MODEL_WINDOW:]
        assert all(cal.exit_date.iloc[j]<signal for j in hist)
        if len(hist)<6:weights=np.full(4,.25)
        else:
            avg=rewards[:,hist].mean(axis=1)
            logit=SOFTMAX_TEMPERATURE*(avg-avg.max())
            soft=np.exp(logit);soft=soft/soft.sum()
            weights=EXPERT_FLOOR+(1-4*EXPERT_FLOOR)*soft
        assert abs(weights.sum()-1)<1e-10
        predicted=rank(weights@ex[:,i,:])
        portfolio.append(predicted)
        weight_audit.append(dict(signal_date=str(signal.date()),
            prior_label_matured_month_count=len(hist),
            most_recent_train_label_maturity=str(cal.exit_date.iloc[hist[-1]].date()) if len(hist) else "",
            **{("weight_"+EXPERTS[j]):float(weights[j]) for j in range(4)}))
    out=np.asarray(portfolio)
    assert out.shape==(65,149)
    return out,cal,ex,y,audit,pd.DataFrame(weight_audit)

def ranking_metrics(score,labels,cal,names,method):
    sel=[];monthly=[];monthlyweights=[]
    for i,row in enumerate(cal.itertuples(index=False)):
        raw=score[i];y=labels[i]
        ordered=np.argsort(-raw,kind="stable")
        five=ordered[:5];two=ordered[:2]
        monthly.append(dict(method=method,signal_date=str(row.signal_date.date()),
           year=row.signal_date.year,
           signed_spearman=float(spearmanr(raw,y).statistic),
           top5_forward_log_excess_vs_equal149=float(y[five].mean()-y.mean()),
           top2_forward_log_excess_vs_equal149=float(y[two].mean()-y.mean())))
        monthlyweights.append({names[j]:.2 for j in five})
        for n,j in enumerate(five):
            sel.append(dict(method=method,signal_date=str(row.signal_date.date()),
                rank=n+1,ticker=names[j],forward_log=float(y[j])))
    return pd.DataFrame(monthly),pd.DataFrame(sel),monthlyweights

def backtest_v2(mats,cal,ma3,adap4,names):
    # original MA3 source, source V6, 149 all funds eligible, a single group.
    Odf=mats["Open"][names];Ldf=mats["Low"][names];Cdf=mats["Close"][names]
    end=cal.exit_date.max()
    Odf=Odf.loc[:end];Ldf=Ldf.loc[Odf.index];Cdf=Cdf.loc[Odf.index]
    st=int(Odf.index.get_loc(cal.entry_date.iloc[0]))
    en=int(Odf.index.get_loc(end))
    days=Odf.index[st:en+1]
    assert len(days)>1200 and days[0].year==2021 and days[-1].year==2026
    EX=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
        EX[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    gross0=ddfirst.sync_c95_m75_gross(Cdf)[st:en+1]
    BM,BOK=producer.basket_arrays(
         pd.DataFrame(dict(basket=[0]*149,ticker=names)),names,n_baskets=1)
    assert BM.shape==(1,149) and BOK.all()
    no_stop=np.zeros_like(UH,dtype=bool)
    zeros=np.zeros_like(ud1,dtype=float)
    no_alt=np.full((1,len(days)),-1,dtype=np.int64)
    allmetrics={};dailynav={"day":days};leader_rows=[]
    pred=ma3.predictions
    et=ma3.et_tail;xb=ma3.xgb_tail
    assert et.shape==xb.shape==(65,149)
    for model_name,score in (("MA3_ORIGINAL",ma3.score),("ADAPT4",adap4)):
        alloc=producer.allocations_from_score(score,cal,days,BM,BOK,continuous=True)
        assert alloc.d1.shape==(1,len(days))
        gross,w=highcagr24.apply_highcagr24(gross0,alloc.weight1,alloc.margin)
        v2w=w.copy()
        for j,row in enumerate(cal.itertuples(index=False)):
            a=int(days.searchsorted(row.entry_date))
            b=int(days.searchsorted(row.exit_date))
            if b<=a:continue
            idx1=int(alloc.d1[0,a]);idx2=int(alloc.d2[0,a])
            assert idx1!=idx2 and 0<=idx1<149 and 0<=idx2<149
            agree=bool(alloc.margin[0,a]>=.03 and et[j,idx1]>et[j,idx2] and xb[j,idx1]>xb[j,idx2])
            if agree:
                mask=gross[a:b]<.999999
                v2w[0,a:b][mask]=1.
            leader_rows.append(dict(model=model_name,signal_date=str(row.signal_date.date()),
                first=names[idx1],second=names[idx2],score_margin=float(alloc.margin[0,a]),
                both_et_xgb_agree=agree,
                v2_extra_concentration_days=int((v2w[0,a:b]>w[0,a:b]+1e-12).sum())))
        V=v6.build_v6_state(Cdf.loc[days,names],alloc.d1,alloc.d2,alloc.weight1,gross0,
                bil_ticker="BIL",shv_ticker="SHV")
        for config in ("FULL_HYBRID24","FULL_V2","NO_RISK_NO_STOPS"):
            if config=="FULL_V2":
                weights=v2w;gr=gross;stop=True;usealt=True
            elif config=="FULL_HYBRID24":
                weights=w;gr=gross;stop=True;usealt=True
            else:
                weights=w;gr=np.ones_like(gross);stop=False;usealt=False
            eq,tr,_,_=v6.simulate_with_alt(
                alloc.d1,alloc.d2,weights,O,L,C,PC,gap,
                ud1 if stop else zeros,uneg if stop else zeros,
                UH if stop else no_stop,SA if stop else no_stop,
                names.index("BIL"),names.index("SHV"),
                gr,V.alt_idx if usealt else no_alt,usealt,COST)
            nav=eq[0];turn=tr[0]
            lr=np.diff(np.log(np.r_[1.,nav]))
            ret=np.expm1(lr)
            peak=np.maximum.accumulate(np.r_[1.,nav])[1:]
            key=model_name+"_"+config
            allmetrics[key]=dict(
                cagr=float(np.expm1(lr.sum()*252/len(lr))),
                maxdd=float((nav/peak-1).min()),
                sharpe=float(ret.mean()/ret.std(ddof=1)*np.sqrt(252)),
                terminal_nav=float(nav[-1]),n_daily=len(nav),
                turnover_annual=float(turn.mean()*252))
            dailynav[key]=nav
            print("US149_ONE_FREE_BASKET_TRUE_SOURCE",key,json.dumps(allmetrics[key]),flush=True)
    return allmetrics,pd.DataFrame(dailynav),pd.DataFrame(leader_rows)

def run(raw,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    derived=out/"SOURCE_ORIGINAL_US149";prepare(raw,derived)
    source=derived/"raw_ticker_csv"
    mats,cats,rawmanifest=load_ticker_csv_folder(source)
    names=list(mats["Close"].columns)
    assert len(names)==149 and set(("SPY","HYG","IEF","BIL","SHV"))<=set(names)
    titan=fit_source_titanium(source,out/"TITANIUM_TRUE_SOURCE")
    ma3=build_real_ma3(source,titan,out/"MA3_TRUE_SOURCE",names)
    features,allcal=monthly_feature_rows(mats,names,titan.groupby("signal_date").first().reset_index(),cats)
    adapt,cal,ex,y,raudit,weightaudit=predictive_adapt4(features,allcal,ma3,names)
    raudit.to_csv(out/"RIDGE36_QUARTERLY_REAL_MATURITY_FITS.csv",index=False)
    weightaudit.to_csv(out/"ADAPT4_MONTHLY_LEARNED_WEIGHTS_PREVIOUS12_ONLY.csv",index=False)
    namescores=pd.DataFrame(adapt,index=cal.signal_date,columns=names)
    namescores.rename_axis("signal_date").to_csv(out/"ADAPT4_ALL_149_FREE_RANK_SCORES.csv")
    sk=[];selection=[];top5economics={};perf=[]
    for m,scores in (("MA3_ORIGINAL",ma3.score),("ADAPT4",adapt)):
        s,hold,w=ranking_metrics(scores,y,cal,names,m)
        sk.append(s);selection.append(hold)
        metric,nav,months=costed_path(w,cal,mats["Open"][names],mats["Open"].index)
        top5economics[m]=metric
        perf.append(nav.rename(m))
    pd.concat(sk).to_csv(out/"149_UNRESTRICTED_PREDICTIVE_MONTHLY_RANK_SKILL.csv",index=False)
    pd.concat(selection).to_csv(out/"149_UNRESTRICTED_BEST5_LEADERS.csv",index=False)
    pd.concat(perf,axis=1).rename_axis("day").to_csv(out/"TOP5_US149_UNRESTRICTED_10BPS_NET_NAV.csv")
    vs=pd.concat(sk).pivot(index="signal_date",columns="method",values="signed_spearman")
    t5=pd.concat(sk).pivot(index="signal_date",columns="method",values="top5_forward_log_excess_vs_equal149")
    effect=boot((vs.ADAPT4-vs.MA3_ORIGINAL).to_numpy(),20261020)
    effect5=boot((t5.ADAPT4-t5.MA3_ORIGINAL).to_numpy(),20261021)
    results,equity,leaders=backtest_v2(mats,cal,ma3,adapt,names)
    equity.to_csv(out/"ORIGINAL_SOURCE_V2_US149_ONE_FREE_UNIVERSE_DAILY_NAV.csv",index=False)
    leaders.to_csv(out/"ORIGINAL_SOURCE_US149_65_MONTH_ONE_FREE_UNIVERSE_LEADERS.csv",index=False)
    summary=dict(status="US149_ORIGINAL_SOURCE_ADAPT4_149_UNRESTRICTED_REAL_RETRAIN_COMPLETE",
      n_eligible_american_etfs=149,distinct_tradable_symbols=149,
      n_baskets=1,never_500_balanced_baskets=True,sector_membership_not_used_to_limit_trading=True,
      n_months=65,
      source_HYG_SPY_IEF_BIL_SHV_original_unmodified=True,
      original_US149_Titanium_MA3_retrained_actual_source=True,
      original_ADAPT4_4expert_weights_and_recency_uncahnged=True,
      maturity_in_every_fit_prior_to_decision=True,
      online_matured_months_strictly_prior=True,
      early_causal_weights_equal25pct=True,
      rolling_expert_reward_lookback_months=12,
      expert_weight_floor_each=.10,
      softmax_temperature=4.,
      original_US149_500_Baskets_Mean_CAGR_Not_Comparable_To_Unrestricted=True,
      all_backtest_2021_to_2026_not_pristine_outofsample=True,
      original_SPY_market_factor_model_and_risk=True,
      original_US_BIL_SHV_defensive_in_USD=True,
      prior_model_USA_narrow_149_end_survivor_universe_caveat=True,
      source_original_model_vs_adaptive_rank_monthly_Spearman_delta_block_bootstrap=effect,
      source_original_model_vs_adaptive_top5_excess_delta_block_bootstrap=effect5,
      top5_10bps_real_US_source_net=top5economics,
      true_source_original_US149_V2_one_unrestricted_basket=results,
      original_EUR48_ADAPT4_versioning_checksum=sha(ROOT/"isin_first2026/predict48/online_experts.py"),
      source_149_original_data_quality_audit_sha=sha(derived/"ORIGINAL_SOURCE_AUDIT.json"),
      original_149_genuine_source_TITANIUM_manifest_sha=sha(out/"TITANIUM_TRUE_SOURCE/MANIFEST.json"),
      no_production_mutation=True)
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.glob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("US149_ADAPT4_ALL_149_FREE_FINAL",json.dumps(summary,allow_nan=False),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--raw",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args()
    run(args.raw,args.out)
