#!/usr/bin/env python3
"""P149B: After-detection falsifier of nonlinear future Top15 prediction.

This is intentionally post-selection on repeatedly mined ETF universe.
True scientific question: does N4 beat AS-OF risk exposure and matched null,
or does it merely target high-volatility extreme-return names?
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from research_reset.predict149.tournament import dataset,portfolio,risk_metrics,STEP,NAMES,SEED
from research_reset.m0b.enrichment import trial_surrogates
from oasis149.canonical import sha,SRC
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"research_reset/predict149/results"
METHODS=("N4_NONLINEAR_TOP15","N6_VOL_GROUP_PROB","N7_VOL_ONLY_RANK")
TRIALS=250
RNG=SEED+1400

def read_source():
    d=json.loads((SOURCE/"RESULT.json").read_text())
    p=pd.read_csv(SOURCE/"ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv")
    assert d["status"]=="EXACT149_BEST_TICKER_FORECAST_TOURNAMENT_COMPLETE"
    assert d["universe_size"]==149 and d["original149_roster_sha256"]==sha(SRC/"universe.csv")
    assert len(p)==d["n_21day_eval_anchors"]*149
    assert p.groupby("block").size().eq(149).all()
    return d,p

def risk_null_predict(all_data,p):
    original=p.copy().reset_index(drop=True)
    times=sorted(original.block.unique())
    z=[]
    feats=["vol_log","down63"]+[f"g{i}" for i in range(6)]
    data=all_data.copy()
    data["vol_log"]=np.log(data.v63.clip(lower=.0001))
    for b in times:
        test=data[data.block==b].copy()
        s=pd.Timestamp(test.signal.iloc[0])
        train=data[pd.to_datetime(data.maturity)<s].copy()
        assert train.block.nunique()>=40 and (pd.to_datetime(train.maturity)<s).all()
        sc=StandardScaler()
        x=sc.fit_transform(train[feats].to_numpy(float))
        zz=sc.transform(test[feats].to_numpy(float))
        lr=LogisticRegression(C=.2,solver="liblinear",random_state=RNG,max_iter=300)
        lr.fit(x,train.top15.to_numpy(int))
        test["N6_VOL_GROUP_PROB"]=lr.predict_proba(zz)[:,1]
        test["N7_VOL_ONLY_RANK"]=test.v63.to_numpy(float)
        z.append(test[["block","ticker","N6_VOL_GROUP_PROB","N7_VOL_ONLY_RANK"]])
    a=pd.concat(z,ignore_index=True)
    joined=original.merge(a,on=["block","ticker"],validate="one_to_one")
    assert len(joined)==len(original)
    for key in ["signal","top15","future_log","future_excess","N4_NONLINEAR_TOP15"]:
        assert joined[key].notna().all()
    if not (joined.groupby("block").top15.sum()==15).all():
        raise AssertionError("Top15 source label drift")
    return joined

def score_binary(data,key):
    y=data.top15.to_numpy(float)
    prob=np.clip(data[key].to_numpy(float),.00001,.99999)
    return dict(Brier=float(np.mean((y-prob)**2)),
         logloss=float(np.mean(-y*np.log(prob)-(1-y)*np.log(1-prob))),
         mean_prediction=float(np.mean(prob)),
         observed_rate=float(np.mean(y)))

def bootstrap_risk_improvement(df,against):
    blocks=sorted(df.block.unique())
    yerr=[]
    for b in blocks:
        x=df[df.block==b]
        e=(x.top15-x[against]).pow(2)-(x.top15-x.N4_NONLINEAR_TOP15).pow(2)
        yerr.append(float(e.mean()))
    v=np.array(yerr);n=len(v)
    rng=np.random.default_rng(RNG)
    draws=[]
    for _ in range(2000):
        ix=[]
        while len(ix)<n:
            k=int(rng.integers(n))
            ix.extend((k+j)%n for j in range(3))
        draws.append(float(v[np.asarray(ix[:n],int)].mean()))
    return dict(mean_Brier_improvement_vs_reference=float(v.mean()),
         ci95=np.quantile(draws,[.025,.975]).tolist(),
         n_nonoverlapping_anchors=n)

def evaluate():
    summary,source=read_source()
    full,roster,days,opens,names=dataset()
    df=risk_null_predict(full,source)
    ids=sorted(df.block.unique());n=len(ids)
    assert n==64 and all(ids[i]+1==ids[i+1] for i in range(n-1))
    original={}
    samples={}
    for method in METHODS:
        picks=[]
        for b in ids:
            anchor=df[df.block==b].sort_values(method,ascending=False)
            picks.append(anchor.ticker.head(5).tolist())
        econ,_=portfolio(picks,ids,opens,names,days)
        hit=sum(df[(df.block==b)&(df.ticker.isin(t))].future_log.max()>=
            df[df.block==b].future_log.max() for b,t in zip(ids,picks))
        # max-in-top5 gives an exact hit on actual best if no ties.
        p10=np.mean([df[df.block==b].nlargest(10,method).top15.mean() for b in ids])
        original[method]=dict(economics=econ,
            top1_winner_in_forecast_top5=int(hit),
            precision10=float(p10),
            n_anchors=n)
        samples[method]=picks
        print("P149B_METHOD",method,json.dumps(original[method]),flush=True)
    archived=summary["metrics"]["N4_NONLINEAR_TOP15"]
    expected=archived["economics"]
    actual=original["N4_NONLINEAR_TOP15"]["economics"]
    parity=float(max(abs(actual[k]-expected[k]) for k in
        ("cagr","terminal_wealth_multiple","max_daily_open_drawdown","fee_amount_initial_units")))
    if parity>1e-10:raise AssertionError("N4 P149 archive economic comparison drift: "+str(parity))
    # Class- and volatility-conditional random checks use strictly lagged vol.
    t=full[full.block.isin(ids)].copy()
    vols=t.pivot(index="signal",columns="ticker",values="v63").sort_index()
    current=[str(df[df.block==b].signal.iloc[0]) for b in ids]
    vol=vols.loc[current,names].copy()
    vol.index=current
    cat=roster.set_index("ticker").macro_category.to_dict()
    members={g:roster.loc[roster.macro_category==g,"ticker"].tolist()
             for g in sorted(set(cat.values()))}
    best_by_anchor={
        int(b):df[df.block==b].sort_values("future_log",ascending=False).ticker.iloc[0]
        for b in ids}
    top15_by_anchor={int(b):set(df[(df.block==b)&(df.top15==1)].ticker)
                     for b in ids}
    checks=[]
    compare={}
    basepicks=samples["N4_NONLINEAR_TOP15"]
    for kind in ("category_only","category_and_vol"):
        for j in range(TRIALS):
            rng=np.random.default_rng(RNG+11001*j+(0 if kind=="category_only" else 300001))
            seq,volerr=trial_surrogates(basepicks,current,vol,cat,members,kind,rng)
            outcome,_=portfolio(seq,ids,opens,names,days)
            hit=int(sum(best_by_anchor[b] in seq[k] for k,b in enumerate(ids)))
            p10_ratio=float(np.mean([sum(ticker in top15_by_anchor[b]
                for ticker in seq[k])/5 for k,b in enumerate(ids)]))
            checks.append(dict(placebo_kind=kind,trial=j,
                 future_absolute_winner_hits=hit,
                 precision_top5=p10_ratio,
                 mean_abs_log_vol_mismatch=volerr,
                 **outcome))
        sub=pd.DataFrame([x for x in checks if x["placebo_kind"]==kind])
        e=actual
        compare[kind]=dict(
             n=TRIALS,observed_winner_hits=original["N4_NONLINEAR_TOP15"]["top1_winner_in_forecast_top5"],
             median_matched_winner_hits=float(sub.future_absolute_winner_hits.median()),
             95pct_quantile_matched_hits=float(sub.future_absolute_winner_hits.quantile(.95)),
             conditional_empirical_upper_tail_hit_rate=float((1+sum(sub.future_absolute_winner_hits>=
                original["N4_NONLINEAR_TOP15"]["top1_winner_in_forecast_top5"]))/(TRIALS+1)),
             median_null_CAGR=float(sub.cagr.median()),
             95pct_CAGR=float(sub.cagr.quantile(.95)),
             original_model_CAGR=float(e["cagr"]),
             percentile_of_original_CAGR=float(np.mean(sub.cagr<e["cagr"])),
             median_null_daily_drawdown=float(sub.max_daily_open_drawdown.median()),
             original_daily_drawdown=float(e["max_daily_open_drawdown"]),
             median_daily_ES5=float(sub.daily_es5.median()),
             original_daily_ES5=float(e["daily_es5"]),
             mean_volatility_mismatch=float(sub.mean_abs_log_vol_mismatch.mean()))
        print("P149B_CONDITIONAL_PLACEBO",kind,json.dumps(compare[kind]),flush=True)
    scoring={}
    for key in ("N4_NONLINEAR_TOP15","N6_VOL_GROUP_PROB","null_top15_probability"):
        scoring[key]=score_binary(df,key)
    eras={}
    for label,mask in (("2021_2023",pd.to_datetime(df.signal).dt.year<=2023),
          ("2024_2026",pd.to_datetime(df.signal).dt.year>=2024)):
        a=df[mask]
        eras[label]={k:score_binary(a,k) for k in scoring}
    ci={r:bootstrap_risk_improvement(df,r) for r in ("N6_VOL_GROUP_PROB","null_top15_probability")}
    p60=summary["passive"]["6040_SPY_AGG_NO_REBALANCE"]
    e=actual
    q=compare["category_and_vol"]
    positive=bool(
        all(scoring["N4_NONLINEAR_TOP15"][m]<scoring["N6_VOL_GROUP_PROB"][m]
            for m in ("Brier","logloss")) and
        ci["N6_VOL_GROUP_PROB"]["ci95"][0]>0 and
        all(eras[era]["N4_NONLINEAR_TOP15"]["Brier"]<
            eras[era]["N6_VOL_GROUP_PROB"]["Brier"] for era in eras) and
        original["N4_NONLINEAR_TOP15"]["top1_winner_in_forecast_top5"]>
            q["95pct_quantile_matched_hits"] and
        e["cagr"]>p60["cagr"] and
        e["max_daily_open_drawdown"]>=-.30 and
        e["cagr"]>q["median_null_CAGR"] and
        e["max_daily_open_drawdown"]>=q["median_null_daily_drawdown"])
    results=dict(status="ORIGINAL149_POSTDISCOVERY_N4_RISK_CONDITIONAL_FALSIFIER_COMPLETE",
         research_post_selection=True,no_real_holdout=True,
         source_original149_sha256=sha(SRC/"universe.csv"),
         original149_universe_exact=True,
         n_eval_anchors=n,full_outcomes_149_each_anchor=True,
         no_future_labels_in_risk_null_training=True,
         original_n4_archived_wealth_parity_max_error=parity,
         original_models=original,
         conditional_placebo_summary=compare,
         risk_baseline_proper_scores=scoring,
         proper_scores_by_era=eras,
         paired_block_bootstrap=ci,
         live_deployment_or_30pct_claim_allowed=False,
         strict_research_go_gate=positive,
         caveats=["Source ETF cohort and sample already heavily researched",
             "Outcome label is max positive return, not positive tail-adjusted portfolio economic utility",
             "As-of volatility matching controls only crude category and conditional 63-day risk",
             "Null selections share time/covariance and should not be regarded independent market samples",
             "No true PIT delistings, broker fill spreads, FX, Euro trading venue or tax"])
    return results,df,pd.DataFrame(checks)

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    args=p.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    result,df,checks=evaluate()
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    df[["block","signal","ticker","category","future_log","future_excess",
        "top15","N4_NONLINEAR_TOP15","N6_VOL_GROUP_PROB","N7_VOL_ONLY_RANK",
        "null_top15_probability"]].to_csv(out/"RISK_BASELINE_PER_TICKER_PREQUENTIAL.csv",index=False)
    checks.to_csv(out/"N4_500_ASOF_RISK_MATCHED_PLACEBO_WEALTH.csv",index=False)
    print("P149B_RISK_CONTROL_RESULT "+json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
