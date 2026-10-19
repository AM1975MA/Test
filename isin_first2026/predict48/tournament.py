#!/usr/bin/env python3
"""EUROPE48: genuine prior-only walk-forward ranking improvement search.

NO new ETF universe, zero lookahead in fitting, 2021-23 development, 2024-26
pre-held-out confirmation of ONLY winner selected using development. Exact old
ETF Trader MA3 Hybrid24 65-month raw ranks for a baseline.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from collections import defaultdict
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from etf_trader.ma3 import producer
from europe_only75.f3h1_original_transfer.run import costed_path,ci
from isin_first2026.v2_forensic48.ablate import calculate_score
ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/"isin_first2026/full_eu_2017/results/STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv"
OLD=ROOT/"isin_first2026/v2_unrestricted48/results"
SEED=20261019
RAWFEATURES=("m5","m21","m63","m126","m252","m126_skip21",
             "m63_skip5","v63","down63","dd126","r63_excess_europe",
             "r63_bucket_excess","trendrisk63")
FITTED=("RIDGE_ALL_HISTORY","RIDGE_RECENT36M","LGBM_RECENT48M")
SIMPLE=("MOM21","MOM63","MOM126","MOM126_SKIP21","MOM63_SKIP5",
       "MOM63_126","RISK_ADJUSTED_MOM63",
       "MOM63_126_SECTOR_NEUTRAL",
       "MOM63_126_VAR_ADJUSTED",
       "MA3_MOM_BLEND_25_75","MA3_MOM_BLEND_50_50",
       "MA3_MOM_BLEND_75_25")
CANDIDATES=("ORIGINAL_MA3",)+SIMPLE+FITTED
assert len(CANDIDATES)==16

def sha(f):
    h=hashlib.sha256()
    with open(f,"rb") as fd:
        for b in iter(lambda:fd.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def rank(x):
    y=np.asarray(x,float)
    assert np.isfinite(y).all()
    return pd.Series(y).rank(method="average",pct=True).to_numpy(float)-.5

def proper_avg(monthly,month_metric):
    a=monthly.groupby("method",sort=False)[month_metric].mean()
    return a.to_dict()

def price_data(prep):
    d=Path(prep)/"raw_ticker_csv"
    master=pd.read_csv(MASTER)
    assert len(master)==48 and master["isin"].is_unique
    names=master.ticker.to_list()
    op,cp={},{}
    first=None
    for t in names:
        z=pd.read_csv(d/(t+".csv"),parse_dates=["date"])
        assert z.date.is_unique and z.date.is_monotonic_increasing
        assert z[["Open","Close"]].notna().all(axis=None)
        if first is None:first=pd.DatetimeIndex(z.date)
        assert first.equals(pd.DatetimeIndex(z.date)),t
        op[t]=z.Open.to_numpy(float)
        cp[t]=z.Close.to_numpy(float)
    opens=pd.DataFrame(op,index=first)
    closes=pd.DataFrame(cp,index=first)
    assert first.size==2746 and (first<pd.Timestamp("2017-01-01")).sum()>=252
    return master,names,opens,closes

def monthly_data(master,names,O,C):
    day=C.index
    mend=pd.DatetimeIndex(pd.Series(day,index=day).groupby(day.to_period("M")).max().values)
    signals=mend[(mend>=pd.Timestamp("2017-01-01"))&
                 (mend<=pd.Timestamp("2026-05-31"))]
    assert len(signals)==113,len(signals)
    log=np.log(C)
    dret=log.diff()
    mom={k:log-log.shift(k) for k in (5,21,63,126,252)}
    v=dret.rolling(63,min_periods=63).std()
    down=dret.clip(upper=0).pow(2).rolling(63,min_periods=63).mean().pow(.5)
    DD=log-log.rolling(126,min_periods=126).max()
    buckets=master.set_index("ticker").benchmark_bucket.to_dict()
    rows,cal=[],[]
    for k,sd in enumerate(signals):
        i=int(day.get_loc(sd))
        assert i>=253
        after=int(mend.searchsorted(sd))+1
        nex=mend[after]
        last=int(day.get_loc(nex))+1
        assert last<len(day)
        enter=day[i+1]; exit=day[last]
        assert sd<enter<exit
        cal.append(dict(block=k,signal_date=sd,entry_date=enter,exit_date=exit))
        open_ret=np.log(O.loc[exit,names]/O.loc[enter,names])
        mean=float(open_ret.mean())
        assert np.isfinite(open_ret).all()
        X={
          "m5":mom[5].loc[sd],
          "m21":mom[21].loc[sd],
          "m63":mom[63].loc[sd],
          "m126":mom[126].loc[sd],
          "m252":mom[252].loc[sd],
          "m126_skip21":mom[126].loc[sd]-mom[21].loc[sd],
          "m63_skip5":mom[63].loc[sd]-mom[5].loc[sd],
          "v63":v.loc[sd],
          "down63":down.loc[sd],
          "dd126":DD.loc[sd],
          "r63_excess_europe":mom[63].loc[sd]-mom[63].loc[sd,"IMEU.AS"],
          "r63_bucket_excess":mom[63].loc[sd]-pd.Series(
             {t:float(mom[63].loc[sd,
                 [x for x in names if buckets[x]==buckets[t]]].mean())
                  for t in names}),
          "trendrisk63":(mom[63].loc[sd]/v.loc[sd].clip(lower=.001))
        }
        features=pd.DataFrame(X,index=names).astype(float)
        assert np.isfinite(features.to_numpy()).all()
        ranks=features.apply(lambda col:pd.Series(rank(col.to_numpy()),
             index=names),axis=0)
        for t in names:
            row=dict(block=k,signal_date=sd,entry_date=enter,
                     maturity=exit,ticker=t,isin=master.set_index("ticker").loc[t,"isin"],
                     category=buckets[t],actual_future_log=float(open_ret[t]),
                     future_excess_equal48=float(open_ret[t]-mean))
            for f in RAWFEATURES:
                row[f]=float(features.loc[t,f])
                row[f+"_rank"]=float(ranks.loc[t,f])
            rows.append(row)
    cal=pd.DataFrame(cal)
    f=pd.DataFrame(rows)
    assert len(f)==113*48 and f.groupby("block").size().eq(48).all()
    return f,cal

def candidates_from_features(now,names,orig):
    cur=now.set_index("ticker").loc[names]
    z=lambda k:np.asarray(cur[k+"_rank"],float)
    m63126=rank(.5*z("m63")+.5*z("m126"))
    sd=rank(.5*z("m63")+.5*z("m126")-.4*z("v63"))
    sect=rank(.5*z("r63_bucket_excess")+.5*z("m126_skip21"))
    results={
       "MOM21":z("m21"),
       "MOM63":z("m63"),
       "MOM126":z("m126"),
       "MOM126_SKIP21":z("m126_skip21"),
       "MOM63_SKIP5":z("m63_skip5"),
       "MOM63_126":m63126,
       "RISK_ADJUSTED_MOM63":z("trendrisk63"),
       "MOM63_126_SECTOR_NEUTRAL":sect,
       "MOM63_126_VAR_ADJUSTED":sd,
       "MA3_MOM_BLEND_25_75":rank(.25*rank(orig)+.75*m63126),
       "MA3_MOM_BLEND_50_50":rank(.50*rank(orig)+.50*m63126),
       "MA3_MOM_BLEND_75_25":rank(.75*rank(orig)+.25*m63126)
    }
    assert set(results)==set(SIMPLE)
    return results

def fit_regressors(frame,cal,names):
    cols=[f+"_rank" for f in RAWFEATURES]
    all_months=sorted(frame.block.unique())
    first=int(cal[cal.signal_date>=pd.Timestamp("2021-01-01")].index.min())
    assert first==48,first
    preds={m:[] for m in FITTED}
    model=None; last_train=None;audits=[]
    for j in range(first,len(cal)):
        signal=cal.loc[j,"signal_date"]
        past=frame[frame.maturity<signal].copy()
        tr_blocks=sorted(past.block.unique())
        assert len(tr_blocks)>=40 and max(tr_blocks)<=j-2
        assert (past.maturity<signal).all()
        if model is None or (j-first)%3==0:
            xall=past[cols].to_numpy(float)
            yall=past.future_excess_equal48.clip(-.20,.20).to_numpy(float)
            recent36=past[past.block.isin(tr_blocks[-36:])]
            recent48=past[past.block.isin(tr_blocks[-48:])]
            m1=StandardScaler().fit(xall)
            ridge_all=Ridge(alpha=40.,fit_intercept=True).fit(m1.transform(xall),yall)
            x36=recent36[cols].to_numpy(float)
            ss=StandardScaler().fit(x36)
            ridge36=Ridge(alpha=40.,fit_intercept=True).fit(
                ss.transform(x36),recent36.future_excess_equal48.clip(-.20,.20))
            gbm=LGBMRegressor(objective="regression",n_estimators=65,
                 learning_rate=.035,num_leaves=7,max_depth=3,
                 min_child_samples=85,reg_lambda=35.,random_state=SEED,
                 n_jobs=1,verbosity=-1)
            gbm.fit(recent48[cols].to_numpy(float),
                recent48.future_excess_equal48.clip(-.20,.20))
            model=(m1,ridge_all,ss,ridge36,gbm)
            last_train=past.maturity.max()
            audits.append(dict(fit_signal=str(signal.date()),
                 max_label_maturity=str(last_train.date()),train_months=len(tr_blocks),
                 train_last36months=len(recent36.block.unique()),
                 train_last48months=len(recent48.block.unique()),
                 distinct_ETF_isins=48))
        now=frame[frame.block==j].set_index("ticker").loc[names]
        x=now[cols].to_numpy(float)
        m1,ra,ss,rr,gbm=model
        outputs={"RIDGE_ALL_HISTORY":ra.predict(m1.transform(x)),
                 "RIDGE_RECENT36M":rr.predict(ss.transform(x)),
                 "LGBM_RECENT48M":gbm.predict(x)}
        for name,y in outputs.items():
            assert len(y)==48 and np.isfinite(y).all()
            preds[name].append(rank(y))
    return {m:np.vstack(p) for m,p in preds.items()},pd.DataFrame(audits)

def boot(x,seed=SEED,n=4000):
    a=np.asarray(x,float);N=len(a)
    assert N>15 and np.isfinite(a).all()
    r=np.random.default_rng(seed);out=np.empty(n,float)
    for i in range(n):
        indices=[]
        while len(indices)<N:
            k=int(r.integers(N))
            indices.extend(((k+j)%N) for j in range(3))
        out[i]=a[np.asarray(indices[:N],int)].mean()
    return dict(mean=float(a.mean()),CI95=[
      float(q) for q in np.quantile(out,[.025,.975])])

def score_matrix(frame,cal,names):
    pred=pd.read_csv(OLD/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv",
         parse_dates=["signal_date"])
    refcal=cal[cal.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(refcal)==65
    assert pd.DatetimeIndex(sorted(pred.signal_date.unique())).equals(
       pd.DatetimeIndex(refcal.signal_date))
    score,et,xb,_=calculate_score(pred,refcal,names)
    saved=pd.read_csv(OLD/"ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv")
    assert len(saved)==65
    top=np.array(names)[np.argmax(score,axis=1)]
    assert np.array_equal(top,np.asarray(saved.leader)),(
        "source MA3 leader/score reconstruction failed",list(zip(top[:5],saved.leader.iloc[:5])))
    allscore={"ORIGINAL_MA3":score}
    for i,cur in enumerate(refcal.itertuples(index=False)):
        block=int(cur.block)
        now=frame[frame.block==block]
        orig=score[i]
        if i==0:
            raw={k:[] for k in SIMPLE}
        candidates=candidates_from_features(now,names,orig)
        for k in SIMPLE: raw[k].append(candidates[k])
    for k in SIMPLE:allscore[k]=np.vstack(raw[k])
    pred_fit,refits=fit_regressors(frame,cal,names)
    allscore.update(pred_fit)
    assert set(allscore)==set(CANDIDATES)
    assert all(v.shape==(65,48) and np.isfinite(v).all() for v in allscore.values())
    return allscore,refcal,refits

def evaluate_scores(frame,cal,allscore,names,out):
    out=Path(out)
    roster=pd.read_csv(MASTER).set_index("ticker")
    assert len(cal)==65
    skill=[];hold=[];positions={}
    for name in CANDIDATES:
        assert allscore[name].shape==(65,48)
        positions[name]=[]
        for i,row in enumerate(cal.itertuples(index=False)):
            fut=frame[frame.block==row.block].set_index("ticker").loc[names]
            y=fut.actual_future_log.to_numpy(float)
            s=allscore[name][i]
            assert len(y)==48 and np.isfinite(y).all()
            i5=np.argsort(-s,kind="stable")[:5]
            i2=np.argsort(-s,kind="stable")[:2]
            sp=float(spearmanr(s,y).statistic)
            assert np.isfinite(sp)
            top5=float(y[i5].mean()-y.mean())
            top2=float(y[i2].mean()-y.mean())
            std=float(y.std(ddof=1))
            hist=dict(method=name,block=int(row.block),
                signal_date=str(row.signal_date.date()),
                signal_year=int(row.signal_date.year),
                signed_spearman=sp,top5_excess_log=top5,
                top2_excess_log=top2,crosssection_sd_log=std,
                positive_top5_excess=int(top5>0),
                positive_top2_excess=int(top2>0))
            skill.append(hist)
            positions[name].append({names[ix]:.2 for ix in i5})
            for rankn,ix in enumerate(i5):
                hold.append(dict(method=name,block=int(row.block),
                     signal_date=str(row.signal_date.date()),
                     rank=rankn+1,ticker=names[ix],
                     isin=str(roster.loc[names[ix],"isin"]),
                     category=str(roster.loc[names[ix],"benchmark_bucket"]),
                     realized_future_log=float(y[ix])))
    ss=pd.DataFrame(skill)
    ss.to_csv(out/"ALL_CANDIDATE_MONTHLY_TRUE_FORWARD_RANK_SKILL.csv",index=False)
    pd.DataFrame(hold).to_csv(out/"ALL_CANDIDATES_TOP5_ISIN_SECTOR_SELECTION.csv",index=False)
    dev=ss[ss.signal_year<=2023]
    assert dev.groupby("method").size().eq(36).all()
    holdout=ss[ss.signal_year>=2024]
    assert holdout.groupby("method").size().eq(29).all()
    disp=float(dev[dev.method=="ORIGINAL_MA3"].crosssection_sd_log.mean())
    assert disp>.001
    # PRECOMMITTED ONLY development statistic; all 2024-26 data quarantined
    # until champion is chosen and written into report.
    objectives={}
    for m,d in dev.groupby("method"):
        objects=dict(mean_spearman=float(d.signed_spearman.mean()),
            mean_top5_excess_log=float(d.top5_excess_log.mean()))
        objects["development_objective"]=float(
             .5*objects["mean_spearman"]+
             .5*objects["mean_top5_excess_log"]/disp)
        objectives[m]=objects
    champion=max(CANDIDATES,key=lambda m:(
        objectives[m]["development_objective"],-CANDIDATES.index(m)))
    base="ORIGINAL_MA3"
    detail={}
    for seg,subset in (("dev_2021_2023",dev),
                       ("confirmation_2024_2026",holdout),
                       ("entire_reused_2021_2026",ss)):
        df=subset.pivot(index="signal_date",columns="method",
                values="signed_spearman").sort_index()
        et=subset.pivot(index="signal_date",columns="method",
                values="top5_excess_log").sort_index()
        obj={}
        for m in CANDIDATES:
            d=subset[subset.method==m]
            obj[m]=dict(mean_monthly_spearman=float(df[m].mean()),
                 mean_top5_excess_log=float(et[m].mean()),
                 positive_spearman_months=int((df[m]>0).sum()),
                 positive_top5_months=int((et[m]>0).sum()),
                 mean_top2_excess_log=float(d.top2_excess_log.mean()),
                 n_months=len(d))
        detail[seg]=obj
    d=detail["confirmation_2024_2026"]
    relative_spearman=boot(
       holdout[holdout.method==champion].sort_values("signal_date").signed_spearman.to_numpy()-
       holdout[holdout.method==base].sort_values("signal_date").signed_spearman.to_numpy(),SEED+201)
    relative_top5=boot(
       holdout[holdout.method==champion].sort_values("signal_date").top5_excess_log.to_numpy()-
       holdout[holdout.method==base].sort_values("signal_date").top5_excess_log.to_numpy(),SEED+202)
    vs_market=boot(
       holdout[holdout.method==champion].sort_values("signal_date").top5_excess_log.to_numpy(),SEED+203)
    absolute_rank=boot(
       holdout[holdout.method==champion].sort_values("signal_date").signed_spearman.to_numpy(),SEED+204)
    # Keep all paths identical cash accounting/fees. This tests how much a
    # ranker improvement actually pays AFTER costs but is NOT selection target.
    openprices={}
    folder=Path(out.parent)/"_PREP"/"raw_ticker_csv"
    # caller provides exact common EU48 Open dataframe to avoid vendor reload
    return dict(champion=champion,dev_obj=objectives,development=detail,
         confirm=dict(n_months=29,champion=champion,
             champion_vs_old_monthly_spearman_paired_bootstrap=relative_spearman,
             champion_vs_old_top5_excess_log_paired_bootstrap=relative_top5,
             champion_absolute_monthly_spearman_bootstrap=absolute_rank,
             champion_top5_log_excess_vs_EW48_bootstrap=vs_market,
             positive_confirmatory_paired_rank_advantage=
                 relative_spearman["CI95"][0]>0,
             positive_confirmatory_top5_excess=
                 vs_market["CI95"][0]>0),positions=positions)

def run(raw,out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    master,names,O,C=price_data(raw)
    frame,cal=monthly_data(master,names,O,C)
    allscore,evalcal,audit=score_matrix(frame,cal,names)
    audit.to_csv(out/"SUPERVISED_RIDGE_LGBM_ACTUAL_TRAIN_MATURITY_AUDIT.csv",index=False)
    analysis=evaluate_scores(frame,evalcal,allscore,names,out)
    champion=analysis.pop("positions")
    # Monthly costed portfolio NAV 10bps both sides, no intramonth stops,
    # since the user requested PREDICTIVE ranking skill not risk optimization.
    selected=analysis["champion"]
    econ={}
    rows={}
    for m in (("ORIGINAL_MA3",selected,"MOM63_126","RIDGE_ALL_HISTORY","LGBM_RECENT48M")):
        for method in dict.fromkeys(m):
            metric,nav,month=costed_path(champion[method],evalcal,O,O.index)
            econ[method]=metric
            nav.name=method;rows[method]=nav
    pd.DataFrame(rows).rename_axis("day").to_csv(out/"COSTED_EUR_OPEN_MONTHLY_TOP5_NET_EQUITY_CURVES.csv")
    preds=[]
    for method,scores in allscore.items():
        for i,r in enumerate(evalcal.itertuples(index=False)):
            for j,t in enumerate(names):
                preds.append(dict(method=method,signal_date=str(r.signal_date.date()),
                       ticker=t,isin=str(master.set_index("ticker").loc[t,"isin"]),
                       forecast_rank_score=float(scores[i,j])))
    pd.DataFrame(preds).to_csv(out/"48_ETF_PREDICTIVE_SCORES_CHRONOLOGICAL.csv",index=False)
    result=dict(status="EU48_PREDICTIVE_RANKING_WALKFORWARD_AND_LOCKED_2024_CONFIRMATION_COMPLETE",
        n_funds=48,n_original_months=len(cal),n_evaluation_months=len(evalcal),
        historical_training_from="2017-01-01",
        development_period="2021-01 through 2023-12",
        confirmation_period="2024-01 through 2026-05",
        months_dev=36,months_confirmation=29,
        no_lookahead_all_train_maturities_before_signal=True,
        original_MA3_leader_65months_exactly_reproduced=True,
        original_MA3_training_scores_unchanged=True,
        original_2021_2026_holdout_not_pristine_across_prior_research=True,
        development_winner_selected_without_2024_2026_labels=True,
        pre_registered_candidate_count=len(CANDIDATES),
        pre_registered_candidate_names=CANDIDATES,
        discovery_winner=selected,
        discovery_development_scores=analysis["dev_obj"],
        diagnostics_split=analysis["development"],
        confirmatory_champion_only=analysis["confirm"],
        costed_10bps_no_stop_2021_2026_selected_portfolios=econ,
        no_production_changes=True,
        caveat_vendor_historical_prices_adjusted_after_corporate_actions=True,
        caveat_2026_survivor_roster_not_historical_PIT=True,
        source_original_48_roster_SHA256=sha(MASTER),
        source_MA3_archived_48_preds_SHA256=sha(
             OLD/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv"))
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EU48_PREDICTION_IMPROVEMENT_FINAL",json.dumps(result,allow_nan=False),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--raw",required=True)
    a.add_argument("--out",required=True)
    p=a.parse_args();run(p.raw,p.out)
