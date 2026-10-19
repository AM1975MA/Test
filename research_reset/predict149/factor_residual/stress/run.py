#!/usr/bin/env python3
"""H1 post-discovery risk/control nulls. NO new training, no parameter tuning."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from oasis149.canonical import load_149,sha,SRC
from research_reset.predict149.tournament import dataset,portfolio
from research_reset.predict149.factor_residual.run import (
    add_factor_labels,FACTORS,SEED)
from research_reset.predict149.factor_neutral.diagnose import (
    matched_pair_indices,concordance)
from research_reset.m0b.enrichment import trial_surrogates
ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/"research_reset/predict149/factor_residual/results"
ARMS=("H1_OLD_FORECAST","HM_MATURED_FACTOR_MEAN",
      "HT_PAST63_FACTOR_TREND","F3_FROZEN")
NNULL=250

def bootstrap(v,offset=27):
    a=np.asarray(v,float)
    assert len(a)==64
    rng=np.random.default_rng(SEED+offset)
    results=[]
    for _ in range(1800):
        ix=[]
        while len(ix)<64:
            t=int(rng.integers(64));ix.extend((t+j)%64 for j in range(3))
        results.append(float(a[np.asarray(ix[:64],int)].mean()))
    return dict(mean=float(a.mean()),ci95=np.quantile(results,[.025,.975]).tolist())

def enrich_controls(pred,full,Z,context):
    pred=pred.copy()
    vals=[];lags=[]
    for b in sorted(pred.block.unique()):
        sub=pred[pred.block==b]
        signal=pd.Timestamp(sub.signal.iloc[0])
        matur=pd.to_datetime(full.groupby("block").maturity.first())
        train_ids=np.flatnonzero(matur<signal)
        if len(train_ids)<40 or np.any(matur.iloc[train_ids]>=signal):
            raise AssertionError("Factor null uses future labels")
        # Mean of only fully matured 21-session future returns of 10 factor proxies.
        historic=Z[train_ids].mean(axis=0)
        x=sub[["beta_"+f for f in FACTORS]].to_numpy(float)
        vals.extend(x@historic)
        lags.extend(x@(context[b][20:30]/3.))
    pred["H1_OLD_FORECAST"]=pred.H1_FACTOR_ONLY
    pred["HM_MATURED_FACTOR_MEAN"]=vals
    pred["HT_PAST63_FACTOR_TREND"]=lags
    pred["F3_FROZEN"]=pred.B0_F3_FROZEN
    for x in ARMS:
        if not np.isfinite(pred[x].to_numpy(float)).all():
            raise AssertionError("forecast not finite "+x)
    return pred

def eval_arm(pred,blocks,prices,names,days):
    rows=[];selected={};paths={};metrics={}
    for model in ARMS:
        picks=[]
        for b in blocks:
            d=pred[pred.block==b].sort_values(model,ascending=False)
            p=d.head(5)
            picks.append(p.ticker.tolist())
            i,j=matched_pair_indices(d.category.to_numpy(str),
                 d.v63.to_numpy(float),band=.20)
            if len(i)<30:raise AssertionError("Insufficient as-of matched pairs")
            rows.append(dict(model=model,block=int(b),signal=d.signal.iloc[0],
                conditional_concordance=concordance(d[model].to_numpy(float),
                    d.future_excess.to_numpy(float),i,j),
                selected_signed_excess=float(p.future_excess.mean()),
                selected_bottom15=float(p.bottom15.mean())))
        curve,econ=portfolio(picks,blocks,prices,names,days)
        paths[model]=curve;selected[model]=picks
        x=pd.DataFrame([z for z in rows if z["model"]==model])
        eras={}
        for name,mask in (("2021_2023",pd.to_datetime(x.signal).dt.year<=2023),
                          ("2024_2026",pd.to_datetime(x.signal).dt.year>=2024)):
            y=x[mask]
            eras[name]=dict(n=int(len(y)),
                conditional_concordance=float(y.conditional_concordance.mean()),
                selected_signed_excess=float(y.selected_signed_excess.mean()),
                selected_bottom15=float(y.selected_bottom15.mean()))
        metrics[model]=dict(economics=econ,
            concordance=bootstrap(x.conditional_concordance),
            selected_signed_excess=float(x.selected_signed_excess.mean()),
            bottom15=float(x.selected_bottom15.mean()),eras=eras)
        print("T149H_STRESS_NULL_ARM",model,json.dumps(metrics[model]),flush=True)
    return pd.DataFrame(rows),selected,metrics,paths

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    output=Path(a.parse_args().out);output.mkdir(parents=True,exist_ok=False)
    pred=pd.read_csv(SOURCE/"FULL_9536_ASOF_FACTOR_AND_RESIDUAL_FORECASTS.csv")
    roster,O,C,V,days,signals,quality=load_149()
    ref,rr,dates,prices,names=dataset()
    if not names==list(roster.ticker):raise AssertionError("Original149 roster changed")
    full,Z,context=add_factor_labels(ref,roster,dates,prices,C)
    ids=sorted(pred.block.unique())
    if len(ids)!=64 or len(pred)!=9536:
        raise AssertionError("Changing original testing window is forbidden")
    now=full[["block","ticker","future_log","future_excess","category","signal"]]
    chk=pred.merge(now,on=["block","ticker"],suffixes=("","_fresh"),validate="one_to_one")
    for x in ("future_log","future_excess"):
        np.testing.assert_allclose(chk[x],chk[x+"_fresh"],atol=1e-12,rtol=0)
    if not(chk.category==chk.category_fresh).all():raise AssertionError("Group changed")
    pred=enrich_controls(pred,full,Z,context)
    panel,picks,score,curves=eval_arm(pred,ids,prices,names,dates)
    original=json.loads((SOURCE/"RESULT.json").read_text())
    old=original["per_model_evaluation"]["H1_FACTOR_ONLY"]["economics"]
    for k in ("cagr","max_daily_open_drawdown","daily_es5",
              "fee_amount_initial_units"):
        if abs(score["H1_OLD_FORECAST"]["economics"][k]-old[k])>1e-10:
            raise AssertionError("H1 forensic portfolio replay not identical "+k)
    paired={}
    for m in ("HM_MATURED_FACTOR_MEAN","HT_PAST63_FACTOR_TREND","F3_FROZEN"):
        first=panel.loc[panel.model=="H1_OLD_FORECAST"].sort_values("block")
        next_=panel.loc[panel.model==m].sort_values("block")
        if not(first.block.to_numpy()==next_.block.to_numpy()).all():
            raise AssertionError("paired calendar shifted")
        paired[m]=dict(concordance_delta=bootstrap(first.conditional_concordance.to_numpy()-
                                                   next_.conditional_concordance.to_numpy(),33),
           signed_payoff_delta=bootstrap(first.selected_signed_excess.to_numpy()-
                                         next_.selected_signed_excess.to_numpy(),34))
    # As-of 63 close realized vol for each tick of exact original 149.
    close_vol=np.log(C).diff().rolling(63,min_periods=63).std()
    sigs=pd.to_datetime(pred.groupby("block").signal.first())
    vol=close_vol.loc[sigs,names].copy()
    vol.index=sigs
    assert np.isfinite(vol.to_numpy()).all()
    category=roster.set_index("ticker").macro_category.to_dict()
    groups={z:roster.loc[roster.macro_category==z,"ticker"].tolist()
            for z in sorted(set(category.values()))}
    label=pred.set_index(["block","ticker"])
    trials=[];summaries={}
    for kind in ("category_only","category_and_vol"):
        for k in range(NNULL):
            rng=np.random.default_rng(SEED+601*k+(0 if kind=="category_only" else 100000))
            ns,mis=trial_surrogates(picks["H1_OLD_FORECAST"],
                       list(sigs),vol,category,groups,kind,rng)
            cash,econ=portfolio(ns,ids,prices,names,dates)
            signed=np.mean([label.loc[[(b,x) for x in bucket]].future_excess.mean()
                for b,bucket in zip(ids,ns)])
            trials.append(dict(kind=kind,trial=k,vol_mismatch=mis,
                signed_21day_excess=float(signed),**econ))
        sub=pd.DataFrame([z for z in trials if z["kind"]==kind])
        h=score["H1_OLD_FORECAST"]
        summaries[kind]=dict(n=len(sub),median_cagr=float(sub.cagr.median()),
            p95_cagr=float(sub.cagr.quantile(.95)),
            H1_percentile_cagr=float(np.mean(sub.cagr<h["economics"]["cagr"])),
            median_drawdown=float(sub.max_daily_open_drawdown.median()),
            H1_drawdown=h["economics"]["max_daily_open_drawdown"],
            median_signed_excess=float(sub.signed_21day_excess.median()),
            H1_signed_excess=h["selected_signed_excess"],
            H1_fraction_beating_null_excess=float(np.mean(
                sub.signed_21day_excess<h["selected_signed_excess"])),
            median_vol_mismatch=float(sub.vol_mismatch.median()))
        print("T149H_STRESS_CONDITIONAL_NULL",kind,json.dumps(summaries[kind]),
            flush=True)
    m1=paired["HM_MATURED_FACTOR_MEAN"]["concordance_delta"]["ci95"][0]>0
    m2=paired["HT_PAST63_FACTOR_TREND"]["concordance_delta"]["ci95"][0]>0
    h1=score["H1_OLD_FORECAST"]
    f3=score["F3_FROZEN"]
    null=summaries["category_and_vol"]
    gate=bool(
        m1 and m2 and
        original["factor_forecast_MSE_vs_matured_mean"]["estimated_factor_mse"]<
        original["factor_forecast_MSE_vs_matured_mean"]["simple_matured_mean_mse"] and
        all(h1["eras"][e]["selected_signed_excess"]>
            score[m]["eras"][e]["selected_signed_excess"]
            for e in ("2021_2023","2024_2026")
            for m in ("HM_MATURED_FACTOR_MEAN","HT_PAST63_FACTOR_TREND")) and
        h1["concordance"]["ci95"][0]>.5 and
        h1["economics"]["cagr"]>null["p95_cagr"] and
        h1["economics"]["max_daily_open_drawdown"]>=
            max(null["median_drawdown"],f3["economics"]["max_daily_open_drawdown"]))
    pd.DataFrame(trials).to_csv(output/"H1_500_MATCHED_RISK_FACTOR_NULLS.csv",index=False)
    panel.to_csv(output/"H1_VS_FACTOR_MEAN_AND_MOMENTUM_64_ANCHORS.csv",index=False)
    pcols=["block","ticker","signal","category","future_log","future_excess",
           *ARMS]
    pred[pcols].to_csv(output/"H1_COMPLETE_NULL_EXPOSURE_PREDICTIONS.csv",index=False)
    pathsfile=pd.DataFrame({"day":dates[ids[0]*21:(ids[-1]+1)*21+1]})
    for key,v in curves.items():pathsfile[key]=v
    pathsfile.to_csv(output/"H1_VS_PURE_FACTOR_PREMIA_COSTED_DAILY.csv",index=False)
    record=dict(status="EXACT149_H1_POSTRESULT_FACTOR_PREMIUM_AND_VOL_PLACEBO_AUDIT_DONE",
        original_etfs=149,source_roster_sha=sha(SRC/"universe.csv"),
        n_eval_anchors=64,n_rows=9536,
        after_observing_prior_H1_backtest=True,
        no_model_refit_or_parameter_tuning=True,
        all_null_forecast_features_strict_asof=True,
        H1_old_economic_parity=True,number_null_portfolios=500,
        arms=score,paired_H1_vs_controls=paired,
        conditional_group_vol_placebos=summaries,
        untrained_factor_mean_benchmark_forecast_MSE=original[
            "factor_forecast_MSE_vs_matured_mean"],
        preregistered_incremental_FACTOR_FORECAST_gate=gate,
        decision="H1_STILL_EXPLORATORY_DO_NOT_DEPLOY" if not gate else
                 "INDEPENDENT_FUTURE_PIT_VALIDATION_REQUIRED",
        caveats=["Posthoc study of the same original149 historically mined 2021–26",
                 "10 proxies and coarse risk classes omit true exposures and FX",
                 "Current ETF universe excludes historical delistings and European availability",
                 "Random placebo matching cannot substitute untouched future observations",
                 "No direct broker spread, tax or news-data vintages verified"])
    (output/"RESULT.json").write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")
    print("T149H_POSTDISCOVERY_FALSIFIER "+json.dumps(record,allow_nan=False),flush=True)
if __name__=="__main__":main()
