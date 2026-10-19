#!/usr/bin/env python3
"""F3/H1/H3 *unmodified estimators* genuinely refit on the new strict EU48 ISIN cohort.

Mechanical variable-N portability from existing EUROPE60 code is made explicit
and source-hashed. Never reuse trained Europe60 or US149 F3/H1/H3 weights.
Frozen old EUR60 R_H is a historic score control only, NOT a 48-refit.
"""
from __future__ import annotations
import argparse,hashlib,inspect,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from research_reset.predict149.tournament import FEATS
import europe_only75.f3h1_original_transfer.run as prior
from europe_only75.risk_ablation.run import read_prices,construct_calendar,frozen_rh_scores

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"isin_first2026/full_eu_2017/results"
GROUPS={
 "EU_EQUITY_BROAD":"EU_BROAD","EU_EQUITY_COUNTRY":"EU_COUNTRY",
 "EU_EQUITY_FACTOR":"EU_FACTOR","EU_EQUITY_SECTOR":"EU_SECTOR",
 "EU_PROPERTY":"EU_PROPERTY","SOVEREIGN_EUR":"EU_SOVEREIGN"
}
FACTORS=prior.FACTORS
REF=prior.REF
COLUMNS=prior.COLUMNS
INPUT=prior.INPUT
QUANTILES=prior.QUANTILES
SEED=prior.SEED
CLIP=prior.CLIP
TRAIN_MIN=prior.TRAIN_MIN
M=("RH_OLD60_MAPPED48","F3_EU48","H1_EU48","H3_EU48","F3_H1_BLEND_EU48",
   "PASSIVE_EU_60_40")
ORIG_M={"F3_EU48":"F3_EUROPE_REFIT",
        "H1_EU48":"H1_EUROPE_REFIT",
        "H3_EU48":"H3_EUROPE_REFIT"}
# All loss functions, estimators, calendars, costed cash accounting copied BY
# REFERENCE from the old code. Only three immutable shape checks are adapted.
join_eur_prices=prior.join_eur_prices
original_feature_formulas_for_60=prior.original_feature_formulas_for_60
qmodel=prior.qmodel
costed_path=prior.costed_path
ci=prior.ci
pinball=prior.pinball
picked=prior.picked
sha=prior.sha

def variable_n_original_algorithm():
    original_code_hash=sha(Path(prior.__file__))
    replacements={
        "betas":{
            "beta.shape!=(60,10)":"beta.shape!=(len(names),10)"
        },
        "create_labels_and_asof_features":{
            "np.zeros((60,6),float)":"np.zeros((len(names),6),float)",
            "len(frame)!=60*frame.block.nunique()":"len(frame)!=len(names)*frame.block.nunique()",
            "frame.groupby(\"block\").size().ne(60)":"frame.groupby(\"block\").size().ne(len(names))"
        },
        "fit_predict":{
            "assert len(now)==60":"assert len(now)==len(frame.ticker.unique())",
            "len(p)==len(testidx)*60":"len(p)==len(testidx)*len(frame.ticker.unique())"
        }
    }
    if len(FEATS)!=19 or len(COLUMNS)!=25 or len(INPUT)!=37:
        raise AssertionError("Original feature architecture changed")
    out={}
    for name,mapping in replacements.items():
        src=inspect.getsource(getattr(prior,name))
        for needle,replacement in mapping.items():
            if src.count(needle)!=1:
                raise AssertionError("Original architecture source drift "+name+": "+needle)
            src=src.replace(needle,replacement)
        assert src.startswith("def "+name+"(")
        # No arbitrary runtime external code; this is the installed version's
        # named trusted *local research source*, mechanistically sourced.
        exec(compile(src,"<variable-N-source-"+name+">","exec"),globals(),out)
    assert all(x in out for x in replacements)
    return out,dict(original_euro60_algorithm_source_sha256=original_code_hash,
                    adaptations=replacements,
                    n_feature_values=len(FEATS),n_onehot=6,
                    model_constants=dict(seed=SEED,training_min=TRAIN_MIN,
                        factor_len=len(FACTORS),quarterly_retrain_months=3))

def data(args):
    roster=pd.read_csv(D/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv")
    assert len(roster)==48 and roster["isin"].nunique()==48
    assert roster.decision.isin(("A","B")).all()
    assert roster.sufficient_252_warmup.astype(bool).all()
    assert (~roster.known_2018_current_class_quarantine.astype(bool)).all()
    names=list(roster["isin"])
    assert roster.benchmark_bucket.isin(GROUPS).all()
    r=pd.DataFrame(dict(ticker=names,
        macro_category=roster.benchmark_bucket.map(GROUPS)))
    assert r.macro_category.nunique()==6
    directory=Path(args.raw149)/"etf_trader_raw"
    refs=read_prices(REF,directory)
    original60=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    assert len(original60)==60
    orig=read_prices(list(original60.ticker),
        ROOT/"data/eu120/raw_ticker_csv")
    quotes={}
    for k in ("Open","Close"):
        f=D/("WIDE_DAILY_"+k.upper()+"_2016_2026.csv")
        p=pd.read_csv(f,parse_dates=["date"]).set_index("date").sort_index()
        assert set(p)==set(names)
        p=p[names].astype(float)
        p=p.where(np.isfinite(p)&(p>0))
        quotes[k]=p
    prior_cal=pd.concat([orig["Open"],refs["Open"]],axis=1).sort_index()
    joint=pd.concat([orig["Open"],quotes["Open"],refs["Open"]],axis=1).sort_index()
    cp=pd.read_parquet(Path(args.eu_model)/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(Path(args.eu_model)/"HYBRID_REFITTED.parquet")
    ca,days=construct_calendar(joint,(cp.copy(),hp.copy()))
    calold,dold=construct_calendar(prior_cal,(cp.copy(),hp.copy()))
    if len(ca)!=len(calold) or not ca.signal_date.equals(calold.signal_date):
        raise AssertionError("Calendar signal anchor cohort differs from old EUR60")
    shared_days=ca.entry_date.eq(calold.entry_date) & ca.exit_date.eq(calold.exit_date)
    assert ca.signal_date.dt.year.min()==2017 and ca.signal_date.dt.year.max()==2026
    # They can have different entry/exit observations, we document the drift.
    # Historical 2021-26 candidate label periods must nonetheless be present.
    for row in ca.itertuples(index=False):
        assert row.entry_date in quotes["Open"].index
        assert row.exit_date in quotes["Open"].index
        for d in (row.entry_date,row.exit_date):
            assert quotes["Open"].loc[d,names].notna().all(),str(d)
    for t in ("EXSA.DE","IMEU.AS","IBCM.DE","EUNH.DE"):
        assert t in set(roster.ticker)
    broad=roster.set_index("ticker")
    passive_names={
      "stock":str(broad.loc["IMEU.AS","isin"]),
      "gov":str(broad.loc["EUNH.DE","isin"])
    }
    fx=Path(args.fx)
    C,eur=join_eur_prices(quotes,refs,fx)
    return dict(roster=r,roster_details=roster,names=names,
        data=quotes,US_refs=refs,old_roster=original60,old_quotes=orig,
        compact=cp,hybrid=hp,cal=ca,days=days,
        old_calendar=calold,shared_day_mask=shared_days,passive=passive_names,
        C=C,eur=eur,fx=fx)

def control_weights(parts,testidx):
    names=parts["names"]
    available={str(isin):str(isin) for isin in names}
    original=parts["old_roster"]
    original_ticker_to_isin=(pd.read_csv(ROOT/
        "isin_first2026/results/ISIN_ALL_CANDIDATE_REFERENCE_MAPPING.csv").
        set_index("ticker")["isin"].to_dict())
    oldnames=list(original.ticker)
    scores=frozen_rh_scores(
        parts["compact"].copy(),parts["hybrid"].copy(),parts["cal"],oldnames)
    controls=[]
    print("RH_LEGACY_SCORE_SIZE",scores.shape,flush=True)
    for i in testidx:
        now=scores[i]
        picks=[];picks_raw=[]
        for j in np.argsort(-np.where(np.isfinite(now),now,-1e8),kind="stable"):
            ticker=oldnames[j]
            isin=original_ticker_to_isin.get(ticker,"")
            if not np.isfinite(now[j]) or isin not in available or isin in picks:
                continue
            picks.append(isin);picks_raw.append(ticker)
            if len(picks)==2:break
        if len(picks)!=2:
            raise AssertionError("No two eligible RH legacy ISIN on the matched 48 fund cohort")
        controls.append((picks,picks_raw))
    return controls

def fit_and_score(parts,engine):
    cal=parts["cal"]
    roster=parts["roster"]
    cand=parts["data"]
    C=parts["C"]
    fn=engine["create_labels_and_asof_features"]
    panel,Z,ctx=fn(roster,cand,C,cal,parts["eur"])
    assert panel.groupby("block").size().eq(len(roster)).all()
    assert len(panel.block.unique())>=110
    fit=engine["fit_predict"]
    preds,factors,testids=fit(panel,Z,ctx,cal)
    assert len(testids)==65 and len(preds)==65*48
    assert preds.groupby("block").size().eq(48).all()
    assert (pd.to_datetime(preds.training_maturity)<
            pd.to_datetime(preds.signal)).all()
    return preds,factors,testids,panel

def score_methods(parts,preds,factors,testidx,out):
    cal=parts["cal"];prices=parts["data"]["Open"];days=parts["days"]
    methods={m:[] for m in M}
    holdings=[]
    rh=control_weights(parts,testidx)
    for j,i in enumerate(testidx):
        now=preds[preds.block==i]
        assert len(now)==48
        f=picked(now,"F3_EUROPE_REFIT")
        h=picked(now,"H1_EUROPE_REFIT")
        third=picked(now,"H3_EUROPE_REFIT")
        assert len(set(f))==len(set(h))==len(set(third))==5
        merged={}
        for t in f:merged[t]=merged.get(t,0)+.1
        for t in h:merged[t]=merged.get(t,0)+.1
        policy={
            M[0]:{t:.5 for t in rh[j][0]},
            M[1]:{t:.2 for t in f},
            M[2]:{t:.2 for t in h},
            M[3]:{t:.2 for t in third},
            M[4]:merged,
            M[5]:{parts["passive"]["stock"]:.6,parts["passive"]["gov"]:.4}
        }
        for name,weight in policy.items():
            assert set(weight).issubset(set(parts["names"]))
            assert abs(sum(weight.values())-1)<1e-11
            for isin,v in weight.items():
                holdings.append(dict(model=name,block=i,
                   signal=str(cal.loc[i,"signal_date"].date()),
                   isin=isin,
                   ticker=parts["roster_details"].set_index("isin").loc[isin,"ticker"],
                   weight=v))
            methods[name].append(weight)
    caltest=cal.iloc[testidx].reset_index(drop=True)
    metrics={};nav={};monthly={}
    for method in M:
        metric,curve,monthly_frame=costed_path(
            methods[method],caltest,prices,days)
        metrics[method]=metric;nav[method]=curve;monthly[method]=monthly_frame
        print("EU48_MODEL_COSTED",method,json.dumps(metric),flush=True)
    assert all(nav[method].index.equals(nav[M[0]].index) for method in M)
    ctrl=monthly[M[0]].net_log_growth.to_numpy(float)
    dates=caltest.signal_date.dt.year.to_numpy()
    paired={}
    for k,method in enumerate(M[1:5]):
        diff=monthly[method].net_log_growth.to_numpy(float)-ctrl
        paired[method]=dict(
             bootstrap_vs_RH=ci(diff,SEED+k+1),
             earlier_2021_2023=float(np.mean(diff[dates<=2023])),
             later_2024_2026=float(np.mean(diff[dates>=2024])),
             drawdown_difference_pp=100*(metrics[method]["maxdd_daily_open"]-
                                             metrics[M[0]]["maxdd_daily_open"]),
             es5_difference_pp=100*(metrics[method]["es5_daily"]-
                                            metrics[M[0]]["es5_daily"]))
    skill={}
    ranks=[]
    for k,m in enumerate(M[1:4]):
        score=ORIG_M[m]
        for i in testidx:
            q=preds[preds.block==i]
            r=float(spearmanr(q[score],q.future_excess).statistic)
            assert np.isfinite(r)
            top=set(picked(q,score))
            ranks.append(dict(model=m,block=i,signal=q.signal.iloc[0],
                 signed_spearman=r,chosen5_mean_future_excess=float(
                     q.loc[q.ticker.isin(top),"future_excess"].mean()),
                 chosen5_mean_nominal_log=float(
                     q.loc[q.ticker.isin(top),"future_nominal_log"].mean())))
        df=pd.DataFrame([x for x in ranks if x["model"]==m])
        skill[m]=dict(spearman=ci(df.signed_spearman,SEED+15+k),
             selected5_mean_future_excess=float(df.chosen5_mean_future_excess.mean()))
    y=preds.clipped_future_excess.to_numpy(float)
    proper=dict(F3_q10_pinball=pinball(y,preds.F3_Q10,.10),
        matured_null_q10_pinball=pinball(y,preds.F3_NULL_Q10,.10),
        F3_q90_pinball=pinball(y,preds.F3_Q90,.90),
        matured_null_q90_pinball=pinball(y,preds.F3_NULL_Q90,.90),
        H1_factor_mse=float(factors.factor_future_mse.mean()),
        matured_null_factor_mse=float(factors.historical_matured_mean_mse.mean()))
    overall=paired[M[4]]
    promote=bool(metrics[M[4]]["cagr"]>metrics[M[0]]["cagr"] and
        overall["drawdown_difference_pp"]>=0 and
        overall["es5_difference_pp"]>=0 and
        overall["bootstrap_vs_RH"]["CI95"][0]>0 and
        overall["earlier_2021_2023"]>0 and overall["later_2024_2026"]>0 and
        any(skill[x]["spearman"]["CI95"][0]>0 for x in (M[1],M[2])))
    navdf=pd.DataFrame({"day":nav[M[0]].index})
    for m in M:navdf[m]=nav[m].to_numpy(float)
    navdf.to_csv(out/"DAILY_COSTED_EQUITY_SAME_EUROPE_DATES.csv",index=False)
    for name in M:monthly[name].to_csv(out/("MONTHLY_"+name+".csv"),index=False)
    pd.DataFrame(holdings).to_csv(out/"MONTHLY_HOLDINGS_UNIQUE_ISIN.csv",index=False)
    pd.DataFrame(ranks).to_csv(out/"SIGNED_RANKING_BY_MONTH.csv",index=False)
    return metrics,paired,skill,proper,promote,len(navdf),caltest

def old_eu60_historical_forecast_diagnostics(parts,testidx,out):
    p=pd.read_csv(ROOT/
       "europe_only75/f3h1_original_transfer/results/EUR60_ALL_60_F3_H1_H3_WALK_FORWARD_FORECASTS.csv")
    assert len(p)==65*60
    # This is a replay of *archived* EUR60 predictions, not retraining EUR60.
    prior_id=parts["old_roster"]
    assert set(p.ticker)==set(prior_id.ticker)
    my_cal=parts["cal"].iloc[testidx].reset_index(drop=True)
    old=parts["old_quotes"]["Open"]
    olddaily={}
    differences=[]
    for i in testidx:
        now=p[p.block==i]
        if len(now)!=60:raise AssertionError("Archived old60 F3 panel missing month")
        assert str(now.signal.iloc[0])==str(parts["cal"].loc[i,"signal_date"].date())
    for method in ("F3_EUROPE_REFIT","H1_EUROPE_REFIT","H3_EUROPE_REFIT"):
        picks=[]
        for i in testidx:
            now=p[p.block==i]
            top=picked(now,method)
            picks.append({t:.2 for t in top})
        stats,curve,month=costed_path(picks,my_cal,old,parts["days"])
        olddaily[method]=curve
        differences.append(dict(method=method,
             **{("EUR60_"+k):v for k,v in stats.items()}))
    pd.DataFrame(differences).to_csv(out/"OLD_EUR60_SAVED_PREDICTIONS_REPLAY_ON_EU48_COMMON_DAYS.csv",index=False)
    return differences

def run(args):
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    engine,provenance=variable_n_original_algorithm()
    # Betas dynamically looks up global "betas" in this module when executed.
    globals()["betas"]=engine["betas"]
    data48=data(args)
    forecast,factor_diag,testidx,frame=fit_and_score(data48,engine)
    metrics,paired,skills,proper,gate,ndaily,caltest=score_methods(
        data48,forecast,factor_diag,testidx,out)
    old=old_eu60_historical_forecast_diagnostics(data48,testidx,out)
    forecast.to_csv(out/"ALL_48_ISIN_F3_H1_H3_MATURITY_PURGED_FORECASTS.csv",index=False)
    factor_diag.to_csv(out/"H1_FACTOR_FORECAST_SKILL.csv",index=False)
    caltest.to_csv(out/"MONTHLY_EUROPE48_EXECUTION_DATES.csv",index=False)
    facts={
       "status":"EUR48_TRUE_RETRAIN_F3_H1_H3_AND_MATCHED_10BP_EXECUTION_COMPLETE",
       "isin_count":len(data48["names"]),
       "groups":data48["roster"].macro_category.value_counts().to_dict(),
       "signaled_anchors":len(data48["cal"]),
       "evaluation_months":len(testidx),
       "evaluation_daily_open_count":ndaily,
       "eval_signal_start":str(caltest.signal_date.min().date()),
       "eval_last_exit":str(caltest.exit_date.max().date()),
       "identical_entry_exit_to_original_EUR60_calendar_blocks":int(
               data48["shared_day_mask"].sum()),
       "model_architecture":provenance,
       "label_blocks":int(frame.block.nunique()),
       "label_maturity_embargo":bool(
          (pd.to_datetime(forecast.training_maturity)<
           pd.to_datetime(forecast.signal)).all()),
       "source_48_quality_manifest_sha":sha(D/"RESULT.json"),
       "source_48_roster_sha":sha(D/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv"),
       "original_eur60_predictions_sha":sha(ROOT/
          "europe_only75/f3h1_original_transfer/results/EUR60_ALL_60_F3_H1_H3_WALK_FORWARD_FORECASTS.csv"),
       "fx_historical_usd_to_eur_sha":sha(data48["fx"]),
       "n_us_etfs_allowed_as_portfolio":0,
       "cost_each_side":.001,
       "matched_dates_for_all_48_models":True,
       "all_strategies_true_ISIN_uniqueness":True,
       "all_model_results":metrics,
       "paired_vs_RH_old60_mapped48":paired,
       "signed_directional_skill":skills,
       "proper_forecast_scores":proper,
       "new_F3_H1_blend_GO":gate,
       "legacy_EUR60_archived_predictions_refunded_replay_on_joint_days":old,
       "eu60_rh_score_ISIN_dedup_BUT_NOT_refit48":True,
       "historic_2026_survivor_universe_not_real_PIT":True,
       "period_reused_after_selection_not_pristine_OOS":True,
       "no_hyperparameter_tuning_on_48_performance":True,
       "no_production_repo_modified":True
    }
    (out/"RESULT.json").write_text(json.dumps(facts,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
       sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+
       sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EUR48_F3_H1_H3_FINISHED "+json.dumps(facts,allow_nan=False),flush=True)
    return facts

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("raw149","eu-model","fx","out"):
        p.add_argument("--"+name,required=True)
    run(p.parse_args())
