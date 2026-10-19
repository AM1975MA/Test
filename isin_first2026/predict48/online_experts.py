#!/usr/bin/env python3
"""Online causal ensemble of 48 Europe ETF pre-existing saved predictor scores.

No retraining, no future target row ever consulted to compute expert weights.
Only last12 strictly matured months per signal and frozen four alternatives.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from europe_only75.f3h1_original_transfer.run import costed_path
from isin_first2026.predict48.tournament import (
 ROOT,MASTER,rank,sha,price_data,monthly_data,boot)
SRC=ROOT/"isin_first2026/predict48/results"
EXPERTS=("ORIGINAL_MA3","MOM21","MOM126","RIDGE_RECENT36M")
METHODS=("ORIGINAL_MA3","MOM21","RIDGE_RECENT36M",
         "ADAPT_4_CAUSAL","ADAPT_2_CAUSAL",
         "STATIC_MA3_MOM21_50_50","STATIC_MA3_RIDGE36_50_50")
SEED=20261019

def initial_scores(names,cal):
    a=pd.read_csv(SRC/"48_ETF_PREDICTIVE_SCORES_CHRONOLOGICAL.csv",
                   parse_dates=["signal_date"])
    assert a.groupby(["method","signal_date"])["isin"].nunique().eq(48).all()
    assert a.groupby("method").signal_date.nunique().eq(65).all()
    data={}
    for m in EXPERTS:
        s=a[a.method==m].pivot(index="signal_date",columns="ticker",
                  values="forecast_rank_score")
        s=s.reindex(index=cal.signal_date,columns=names)
        x=s.to_numpy(float)
        assert x.shape==(65,48) and np.isfinite(x).all()
        data[m]=np.vstack([rank(row) for row in x])
    return data

def get_hist_criterion(cal,oldskill):
    assert oldskill.method.nunique()==16
    source={}
    for m in EXPERTS:
        a=oldskill[oldskill.method==m].sort_values("signal_date")
        assert len(a)==65
        assert list(a.signal_date)==[str(x.date()) for x in cal.signal_date]
        sd=a.crosssection_sd_log.to_numpy(float)
        assert (sd>.0005).all()
        # Original frozen preregistered development rank+relative selector
        source[m]=.5*a.signed_spearman.to_numpy(float)+(
               .5*a.top5_excess_log.to_numpy(float)/sd)
        assert np.isfinite(source[m]).all()
    return source

def smart_weights(signal_index,cal,oldskill,experts,floor):
    curr=cal.signal_date.iloc[signal_index]
    allowed=np.where((cal.exit_date.to_numpy()<np.datetime64(curr))&
              (np.arange(len(cal))<signal_index))[0]
    hist=allowed[-12:]
    assert all(pd.Timestamp(cal.exit_date.iloc[j])<curr for j in hist)
    if len(hist)<6:
        return np.full(len(experts),1/len(experts)),len(hist)
    rewards=np.asarray([oldskill[m][hist].mean() for m in experts])
    u=4.*(rewards-np.max(rewards))
    p=np.exp(u);p=p/p.sum()
    leftover=1-floor*len(experts)
    assert leftover>=0
    weights=floor+leftover*p
    assert abs(sum(weights)-1)<1e-10
    return weights,len(hist)

def study(prep,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    master,names,O,C=price_data(prep)
    frame,calfull=monthly_data(master,names,O,C)
    cal=calfull[calfull.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65
    source=initial_scores(names,cal)
    oldscore=pd.read_csv(SRC/"ALL_CANDIDATE_MONTHLY_TRUE_FORWARD_RANK_SKILL.csv")
    history=get_hist_criterion(cal,oldscore)
    names_to_isin=master.set_index("ticker")["isin"].to_dict()
    predictions={k:[] for k in METHODS}
    weights_log=[]
    for i,r in enumerate(cal.itertuples(index=False)):
        w4,n4=smart_weights(i,cal,history,EXPERTS,.10)
        w2,n2=smart_weights(i,cal,history,EXPERTS[:2],.20)
        vals={m:source[m][i] for m in EXPERTS}
        x4=rank(np.asarray(w4)@np.vstack([vals[k] for k in EXPERTS]))
        x2=rank(np.asarray(w2)@np.vstack([vals[k] for k in EXPERTS[:2]]))
        mixtures={
          "ORIGINAL_MA3":vals["ORIGINAL_MA3"],
          "MOM21":vals["MOM21"],
          "RIDGE_RECENT36M":vals["RIDGE_RECENT36M"],
          "ADAPT_4_CAUSAL":x4,
          "ADAPT_2_CAUSAL":x2,
          "STATIC_MA3_MOM21_50_50":rank(.5*vals["ORIGINAL_MA3"]+
                                      .5*vals["MOM21"]),
          "STATIC_MA3_RIDGE36_50_50":rank(.5*vals["ORIGINAL_MA3"]+
                                         .5*vals["RIDGE_RECENT36M"])
        }
        assert set(mixtures)==set(METHODS)
        for m in METHODS:
            assert len(mixtures[m])==48 and np.isfinite(mixtures[m]).all()
            predictions[m].append(mixtures[m])
        w=dict(signal_date=str(r.signal_date.date()),
                 max_eligible_historical_months=n4,
                 n_eligible_12month_for_2expert=n2,
                 source_available_first_signal_month="2021-01")
        for m,f in zip(EXPERTS,w4):
            w["ADAPT4_"+m]=float(f)
        for m,f in zip(EXPERTS[:2],w2):
            w["ADAPT2_"+m]=float(f)
        weights_log.append(w)
    pd.DataFrame(weights_log).to_csv(out/"CAUSAL_EXPERT_WEIGHTS_AT_EACH_SIGNAL.csv",index=False)
    labels=frame.set_index(["block","ticker"])
    measures=[];hold=[]
    results={};retmonthly={}
    for method in METHODS:
        scores=np.vstack(predictions[method])
        bweights=[]
        for i,row in enumerate(cal.itertuples(index=False)):
            y=frame[frame.block==row.block].set_index('ticker').loc[names].actual_future_log.to_numpy(float)
            val=scores[i]
            s=float(spearmanr(val,y).statistic)
            assert np.isfinite(s)
            best=np.argsort(-val,kind="stable")[:5]
            best2=np.argsort(-val,kind="stable")[:2]
            top5=float(y[best].mean()-y.mean())
            top2=float(y[best2].mean()-y.mean())
            measures.append(dict(method=method,signal_date=str(row.signal_date.date()),
                  year=int(row.signal_date.year),monthly_spearman=s,
                  top5_excess_log=top5,top2_excess_log=top2,
                  top5_positive=bool(top5>0),positive_spearman=bool(s>0)))
            weights={names[j]:.2 for j in best}
            bweights.append(weights)
            for n,k in enumerate(best):
                hold.append(dict(method=method,signal_date=str(row.signal_date.date()),
                      rank=n+1,ticker=names[k],isin=names_to_isin[names[k]],
                      score=float(val[k]),realized_future_log=float(y[k])))
        economic,nav,month=costed_path(bweights,cal,O,O.index)
        results[method]=economic
        retmonthly[method]=month.net_log_growth.to_numpy(float)
    skill=pd.DataFrame(measures)
    skill.to_csv(out/"ONLINE_EXPERT_MONTHLY_PREDICTIVE_SKILL.csv",index=False)
    pd.DataFrame(hold).to_csv(out/"ONLINE_EXPERT_TOP5_ISIN_SELECTION.csv",index=False)
    duration={}
    for period,selected in (
        ("dev_2021_2023",skill.year<=2023),
        ("reuse_2024_2026",skill.year>=2024),
        ("all_65_months",pd.Series(True,index=skill.index))):
        rec={}
        sub=skill[selected]
        base=sub[sub.method=="ORIGINAL_MA3"].sort_values("signal_date")
        for method in METHODS:
            q=sub[sub.method==method].sort_values("signal_date")
            assert len(q)==len(base)
            diffsp=q.monthly_spearman.to_numpy()-base.monthly_spearman.to_numpy()
            diffex=q.top5_excess_log.to_numpy()-base.top5_excess_log.to_numpy()
            rec[method]=dict(n=len(q),
                mean_spearman=float(q.monthly_spearman.mean()),
                mean_top5_excess_log=float(q.top5_excess_log.mean()),
                mean_top2_excess_log=float(q.top2_excess_log.mean()),
                positive_top5_months=int(q.top5_positive.sum()),
                paired_rank_vs_original=boot(diffsp,SEED+len(method)),
                paired_top5_log_excess_vs_original=boot(diffex,SEED+len(method)+50),
                absolute_top5_excess=boot(q.top5_excess_log,SEED+len(method)+100))
        duration[period]=rec
    summary=dict(
       status="EU48_CAUSAL_ONLINE_EXPERT_RANKING_SECOND_FROZEN_STUDY_COMPLETE",
       months=65,unique_isins=48,methods=METHODS,
       rank_and_next_month_payoff_learning_only_from_prior_matured_exits=True,
       actual_matured_12month_window=True,
       never_add_US_assets_or_4_category_quota=True,
       no_retrain_original_source_score=True,
       all_2024_2026_has_been_previously_observed_and_is_NOT_pristine_OOS=True,
       duration_metrics=duration,
       costed_10bps_top5_true_shares_open_EUR=results,
       original_16_predictor_scores_sha=sha(
             SRC/"48_ETF_PREDICTIVE_SCORES_CHRONOLOGICAL.csv"),
       original_16_actual_future_labels_sha=sha(
             SRC/"ALL_CANDIDATE_MONTHLY_TRUE_FORWARD_RANK_SKILL.csv"),
       original_48_isin_master_sha=sha(MASTER),
       production_modified=False)
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("CAUSAL_ONLINE_EXPERT_FINAL",json.dumps(summary,allow_nan=False),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--prep",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args();study(x.prep,x.out)
