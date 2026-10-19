#!/usr/bin/env python3
"""Original149 T149C: a bidirectional *direction-of-extreme* forecaster.

Distinguishes high-right-tail likely winners from merely volatile ETFs
having BOTH high positive and negative future tail probabilities.
Precommitted post-selection; no performance optimization or leverage.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from research_reset.predict149.tournament import (
    dataset,portfolio,STEP,FEATS,SEED)
from oasis149.canonical import sha,SRC
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"research_reset/predict149/results"
RISKBASE=ROOT/"research_reset/predict149/conditional_validation/results"
METHODS=("N4_NONLINEAR_TOP15","N2_RIDGE_EXCESS",
    "N6_VOL_GROUP_PROB","T149C_ASYMMETRIC_EDGE","T149C_TAIL_DIRECTION")

def read_data():
    original=json.loads((BASE/"RESULT.json").read_text())
    assert original["original149_roster_sha256"]==sha(SRC/"universe.csv")
    published=pd.read_csv(BASE/"ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv")
    matched=pd.read_csv(RISKBASE/"RISK_BASELINE_PER_TICKER_PREQUENTIAL.csv")
    full,roster,days,opens,names=dataset()
    assert len(full)==112*149
    full["bottom15"]=(full.groupby("block").future_log.rank(method="first",ascending=True)<=15).astype(int)
    assert full.groupby("block").bottom15.sum().eq(15).all()
    ids=sorted(published.block.unique())
    assert len(ids)==64
    expected=full[full.block.isin(ids)][["block","ticker","signal","category","future_log","future_excess","top15","bottom15"]].copy()
    common=expected.merge(published[["block","ticker","N4_NONLINEAR_TOP15",
              "N2_RIDGE_EXCESS"]],on=["block","ticker"],validate="one_to_one")
    common=common.merge(matched[["block","ticker","N6_VOL_GROUP_PROB"]],
                       on=["block","ticker"],validate="one_to_one")
    assert len(common)==64*149
    assert all(abs(common.future_log.values-expected.future_log.values)<1e-13)
    return full,common,ids,roster,days,opens,names,original

def downside_prediction(full,common,ids):
    train_data=full.copy()
    cols=list(FEATS)+[f"g{i}" for i in range(6)]
    result=[]
    model=None
    for k,b in enumerate(ids):
        current=train_data[train_data.block==b].copy()
        signal=pd.Timestamp(current.signal.iloc[0])
        train=train_data[pd.to_datetime(train_data.maturity)<signal]
        if train.block.nunique()<40:raise AssertionError("inadequate matured labels")
        assert (pd.to_datetime(train.maturity)<signal).all()
        if k%3==0 or model is None:
            model=HistGradientBoostingClassifier(
                 max_iter=65,max_leaf_nodes=7,min_samples_leaf=80,
                 learning_rate=.05,l2_regularization=20.,
                 early_stopping=False,random_state=SEED)
            model.fit(train[cols].to_numpy(float),train.bottom15.to_numpy(int))
        prob=model.predict_proba(current[cols].to_numpy(float))[:,1]
        current["p_bottom15"]=prob
        current["tail_train_prior_block_count"]=train.block.nunique()
        result.append(current[["block","ticker","p_bottom15","tail_train_prior_block_count"]])
        if k in (0,32,63):print("T149C_MATURED",k+1,"asof",signal.date(),
                              "history",train.block.nunique(),flush=True)
    p=pd.concat(result,ignore_index=True)
    joint=common.merge(p,on=["block","ticker"],validate="one_to_one")
    joint["T149C_ASYMMETRIC_EDGE"]=joint.N4_NONLINEAR_TOP15-joint.p_bottom15
    joint["T149C_TAIL_DIRECTION"]=(joint.N4_NONLINEAR_TOP15+.005)/(
        joint.N4_NONLINEAR_TOP15+joint.p_bottom15+.010)
    for col in METHODS+("p_bottom15",):
        if not np.isfinite(joint[col]).all():raise AssertionError("prediction is nonfinite")
    return joint

def score(y,p):
    y=np.asarray(y,float);p=np.clip(np.asarray(p,float),1e-6,1-1e-6)
    return dict(Brier=float(np.mean((y-p)**2)),
        logloss=float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p))),
        event_rate=float(y.mean()),probability_mean=float(p.mean()))

def bootstrap_difference(paths,method,other="N4_NONLINEAR_TOP15"):
    x=np.diff(np.log(paths[method][::STEP]))
    y=np.diff(np.log(paths[other][::STEP]))
    assert len(x)==len(y)==64
    diff=x-y
    rng=np.random.default_rng(SEED+414)
    n=len(diff);sims=[]
    for _ in range(2000):
        ix=[]
        while len(ix)<n:
            t=int(rng.integers(n))
            ix.extend((t+j)%n for j in range(3))
        sims.append(float(diff[np.asarray(ix[:n],int)].mean()))
    return dict(mean_monthly_net_log_improvement=float(diff.mean()),
        ci95=np.quantile(sims,[.025,.975]).tolist(),
        n_monthly_blocks=n)

def results(df,ids,roster,days,opens,names,archived):
    res={};curves={};anchors=[]
    for method in METHODS:
        chosen=[]
        for b in ids:
            sub=df[df.block==b]
            selected=sub.sort_values(method,ascending=False).head(5)
            chosen.append(selected.ticker.tolist())
            best=sub.loc[sub.future_log.idxmax(),"ticker"]
            anchors.append(dict(block=int(b),signal=sub.signal.iloc[0],
                method=method,top5=";".join(selected.ticker),
                future_absolute_winner_in_top5=int(best in set(selected.ticker)),
                selected_realized_bottom15_fraction=float(selected.bottom15.mean()),
                selected_realized_top15_fraction=float(selected.top15.mean()),
                mean_future_benchmark_excess=float(selected.future_excess.mean()),
                mean_future_log_return=float(selected.future_log.mean()),
                rank_spearman=float(spearmanr(sub[method],sub.future_excess).statistic)))
        wealth,economic=portfolio(chosen,ids,opens,names,days)
        curves[method]=wealth
        group=pd.DataFrame(anchors)
        u=group[group.method==method]
        per_era={}
        for title,mask in (
          ("2021_2023",pd.to_datetime(u.signal).dt.year<=2023),
          ("2024_2026",pd.to_datetime(u.signal).dt.year>=2024)):
            v=u[mask]
            per_era[title]=dict(n=int(len(v)),
                relative_future_excess=float(v.mean_future_benchmark_excess.mean()),
                worst15_selected_rate=float(v.selected_realized_bottom15_fraction.mean()),
                future_best_hit_count=int(v.future_absolute_winner_in_top5.sum()),
                mean_spearman=float(v.rank_spearman.mean()))
        res[method]=dict(economics=economic,
            future_best_top5_hits=int(u.future_absolute_winner_in_top5.sum()),
            actual_top15_fraction=float(u.selected_realized_top15_fraction.mean()),
            actual_bottom15_fraction=float(u.selected_realized_bottom15_fraction.mean()),
            mean_forward_benchmark_excess=float(u.mean_future_benchmark_excess.mean()),
            mean_rank_spearman=float(u.rank_spearman.mean()),
            eras=per_era)
        print("T149C_METHOD",method,json.dumps(res[method]),flush=True)
    ref=archived["metrics"]["N4_NONLINEAR_TOP15"]["economics"]
    parity=max(abs(res["N4_NONLINEAR_TOP15"]["economics"][k]-ref[k]) for k
               in ("cagr","max_daily_open_drawdown","fee_amount_initial_units"))
    if parity>1e-10:raise AssertionError("N4 archive re-execution drift")
    brier=score(df.bottom15,df.p_bottom15)
    null=score(df.bottom15,np.full(len(df),15/149))
    early=df[pd.to_datetime(df.signal).dt.year<=2023]
    late=df[pd.to_datetime(df.signal).dt.year>=2024]
    paired={m:bootstrap_difference(curves,m) for m in METHODS if m!="N4_NONLINEAR_TOP15"}
    candidate={}
    baseline=res["N4_NONLINEAR_TOP15"]
    ref6040=archived["passive"]["6040_SPY_AGG_NO_REBALANCE"]
    for model in ("T149C_ASYMMETRIC_EDGE","T149C_TAIL_DIRECTION"):
        m=res[model];e=m["economics"]
        ok=(
            e["cagr"]>baseline["economics"]["cagr"] and
            e["cagr"]>ref6040["cagr"] and
            e["max_daily_open_drawdown"]>-0.30 and
            e["max_daily_open_drawdown"]>baseline["economics"]["max_daily_open_drawdown"] and
            e["daily_es5"]>baseline["economics"]["daily_es5"] and
            m["actual_bottom15_fraction"]<baseline["actual_bottom15_fraction"] and
            paired[model]["ci95"][0]>0 and
            all(v["relative_future_excess"]>0 for v in m["eras"].values()))
        candidate[model]=bool(ok)
    curvesout=pd.DataFrame({"day":days[ids[0]*STEP:(ids[-1]+1)*STEP+1]})
    for name,x in curves.items():curvesout[name]=x
    return res,paired,candidate,dict(
       downside_histGB= brier,
       historical_15of149_prior=null,
       by_era={"2021_2023":score(early.bottom15,early.p_bottom15),
               "2024_2026":score(late.bottom15,late.p_bottom15)}), \
        parity,pd.DataFrame(anchors),curvesout

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    o=Path(p.parse_args().out);o.mkdir(parents=True,exist_ok=False)
    full,original,ids,roster,days,opens,names,archive=read_data()
    predicted=downside_prediction(full,original,ids)
    res,ci,gate,down,parity,monthly,wealth=results(
        predicted,ids,roster,days,opens,names,archive)
    out=dict(status="ORIGINAL149_TWO_TAIL_WINNER_FORECAST_COMPLETED",
       exact_etf_count=149,n_anchor=64,
       source_original149_sha=sha(SRC/"universe.csv"),
       predictions_use_only_matured_training_labels=True,
       original_N4_wealth_parity=float(parity),
       underlying_upside_model_is_frozen_N4=True,
       downside_model_same_fixed_hyperparams_as_N4=True,
       downside_proper_score=down,
       models=res,paired_bootstrap_vs_N4=ci,
       preregistered_improvement_gate=gate,
       independent_holdout=False,
       live_deployable=False,
       caveats=["New after observing prior 149 poor risk-matched result",
          "Historical ETF sample repeatedly mined and selected by hindsight survivorship",
          "Bottom15 identification skill is not inherently a reliable forecast of positive alpha",
          "No verified EUR ETF broker quote or bid/ask, tax, latency, delisting",
          "Causal chronological refit but not independent future validation"])
    predicted[["block","signal","ticker","category","top15","bottom15",
       "future_log","future_excess","N4_NONLINEAR_TOP15","p_bottom15",
       "T149C_ASYMMETRIC_EDGE","T149C_TAIL_DIRECTION",
       "N6_VOL_GROUP_PROB","N2_RIDGE_EXCESS"]].to_csv(o/"PER_ETF_BIDIRECTIONAL_FORECASTS.csv",index=False)
    monthly.to_csv(o/"PER_ANCHOR_SELECTED_FUTURE_OUTCOMES.csv",index=False)
    wealth.to_csv(o/"EQUAL_SHARES_COSTED_PORTFOLIO_PATHS.csv",index=False)
    (o/"RESULT.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("T149C_BIDIRECTIONAL_RESULT "+json.dumps(out,allow_nan=False),flush=True)
if __name__=="__main__":main()
