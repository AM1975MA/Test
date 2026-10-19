#!/usr/bin/env python3
"""T149-D: exact 149 future-winner forecasting feature and learning-target ablations.

In every walk-forward fit, all labels have fully matured before as-of signal.
This is a REPEATEDLY-MINED historical corpus; no results certify live alpha.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score
from lightgbm import LGBMClassifier,LGBMRanker
from oasis149.canonical import load_149,sha,SRC
from research_reset.predict149.tournament import dataset,portfolio,FEATS,SEED

ROOT=Path(__file__).resolve().parents[3]
PARENT=ROOT/"research_reset/predict149/results"
METHODS=("B0_ARCHIVED_N4","D1_RAW63_LGBM","D2_ENGINEERED_LGBM",
         "D3_CONTEXT_LGBM","D4_GRADED_LAMBDARANK","D5_SIGNED_TAIL_LGBM")
GROUPS=tuple(f"g{i}" for i in range(6))
CONTEXT=("r5","r21","r63","r126","v21","v63","v126",
         "down63","beta126","res21","res63","draw63","volshock","accel","trendrisk")
RAW=tuple(f"raw_ret_{j:02d}" for j in range(63))
FEATURE_RAW=RAW+GROUPS
FEATURE_ENG=tuple(FEATS)+GROUPS
FEATURE_CONTEXT=FEATURE_ENG+tuple(f"crossrank_{name}" for name in CONTEXT)
EVAL=pd.Timestamp("2021-01-01")
TOPN=15
N=149
FIT_PERIOD=3
SEED=20261019

def expand_features(frame,closed,roster):
    """Raw log Close-to-Close returns and as-of within-month factor ranks."""
    names=list(roster.ticker)
    blocks=sorted(frame.block.unique())
    m=np.zeros((len(frame),63),float)
    # Dataset() stores each block in roster order. Enforce rather than infer.
    for b in blocks:
        ix=np.flatnonzero(frame.block.to_numpy()==b)
        block=frame.iloc[ix]
        if block.ticker.tolist()!=names or len(ix)!=N:raise AssertionError("ticker order drift")
        cutoff=pd.Timestamp(block.signal.iloc[0])
        hist=np.log(closed[names].loc[:cutoff]).diff().tail(63).to_numpy(float)
        if hist.shape!=(63,149) or not np.isfinite(hist).all():
            raise AssertionError("Invalid historical raw return window")
        m[ix,:]=hist.T
    for k,f in enumerate(RAW):
        frame[f]=m[:,k]
    for f in CONTEXT:
        frame["crossrank_"+f]=frame.groupby("block")[f].rank(method="average",pct=True)
    for feature in FEATURE_RAW+FEATURE_CONTEXT:
        if not np.isfinite(frame[feature].to_numpy(float)).all():
            raise AssertionError("nonfinite as-of feature: "+feature)
    frame["bottom15"]=(frame.groupby("block").future_log.rank(
        method="first",ascending=True)<=15).astype(int)
    rank=frame.groupby("block").future_log.rank(method="first",ascending=False)
    frame["graded_relevance"]=np.select(
        [rank<=5,rank<=15,rank<=30],[3,2,1],default=0).astype(int)
    assert frame.groupby("block").top15.sum().eq(15).all()
    assert frame.groupby("block").bottom15.sum().eq(15).all()
    assert frame.groupby("block").graded_relevance.apply(
        lambda s: tuple(s.value_counts().reindex([3,2,1,0]).tolist())).nunique()==1
    return frame

def clf():
    return LGBMClassifier(n_estimators=75,learning_rate=.05,num_leaves=9,
        max_depth=4,min_child_samples=90,reg_lambda=20.,
        random_state=SEED,n_jobs=1,verbosity=-1)

def ranker():
    return LGBMRanker(objective="lambdarank",
        n_estimators=75,learning_rate=.05,num_leaves=9,max_depth=4,
        min_child_samples=90,reg_lambda=20.,label_gain=[0,1,3,7],
        random_state=SEED,n_jobs=1,verbosity=-1)

def training(frame):
    src=Path(PARENT/"ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv")
    stored=pd.read_csv(src)
    assert stored.block.nunique()==64 and len(stored)==64*149
    assert stored.groupby("block").size().eq(149).all()
    assert stored[["block","ticker"]].duplicated().sum()==0
    eval_ids=sorted(stored.block.unique())
    out=[]
    models={}
    for k,b in enumerate(eval_ids):
        sub=frame.loc[frame.block==b].copy()
        s=pd.Timestamp(sub.signal.iloc[0])
        tr=frame.loc[pd.to_datetime(frame.maturity)<s]
        assert tr.block.nunique()>=40
        assert (pd.to_datetime(tr.maturity)<s).all()
        if k%FIT_PERIOD==0:
            xraw=tr[list(FEATURE_RAW)].to_numpy(float)
            xeng=tr[list(FEATURE_ENG)].to_numpy(float)
            xcontext=tr[list(FEATURE_CONTEXT)].to_numpy(float)
            yy=tr.top15.to_numpy(int)
            models["raw"]=clf().fit(xraw,yy)
            models["eng"]=clf().fit(xeng,yy)
            models["context"]=clf().fit(xcontext,yy)
            # Query: 149 unique ticker observations per completed anchor,
            # sorted in chronological order; all previous labels matured.
            grouparr=tr.groupby("block",sort=True).size().to_numpy(int)
            if not np.all(grouparr==N) or sum(grouparr)!=len(tr):
                raise AssertionError("Learning-to-rank query grouping corrupted")
            models["ranking"]=ranker().fit(xcontext,
                tr.graded_relevance.to_numpy(int),group=grouparr)
            models["tail_down"]=clf().fit(xcontext,tr.bottom15.to_numpy(int))
            print("T149D_QUARTERLY_MODEL_REFIT",k,"signal",s.date(),
                  "historically_matured_anchors",tr.block.nunique(),flush=True)
        qraw=sub[list(FEATURE_RAW)].to_numpy(float)
        qeng=sub[list(FEATURE_ENG)].to_numpy(float)
        qcontext=sub[list(FEATURE_CONTEXT)].to_numpy(float)
        sub["D1_RAW63_LGBM"]=models["raw"].predict_proba(qraw)[:,1]
        sub["D2_ENGINEERED_LGBM"]=models["eng"].predict_proba(qeng)[:,1]
        sub["D3_CONTEXT_LGBM"]=models["context"].predict_proba(qcontext)[:,1]
        sub["D4_GRADED_LAMBDARANK"]=models["ranking"].predict(qcontext)
        sub["D5_SIGNED_TAIL_LGBM"]=sub["D3_CONTEXT_LGBM"]-models["tail_down"].predict_proba(qcontext)[:,1]
        sub["D5_TOP15_PROB"]=sub["D3_CONTEXT_LGBM"]
        sub["D5_BOTTOM15_PROB"]=models["tail_down"].predict_proba(qcontext)[:,1]
        sub["n_prior_matured_anchors"]=tr.block.nunique()
        sub["latest_train_outcome_maturity"]=str(pd.Timestamp(tr.maturity.max()).date())
        out.append(sub)
    merged=pd.concat(out,ignore_index=True)
    archived=stored[["block","ticker","N4_NONLINEAR_TOP15","future_log",
                     "future_excess","top15"]].copy()
    merged=merged.merge(archived,on=["block","ticker"],suffixes=("","_old"),
                        validate="one_to_one")
    for col in ("future_log","future_excess","top15"):
        if not np.allclose(merged[col],merged[col+"_old"],atol=1e-12,rtol=0):
            raise AssertionError("Archived 149 prediction labels drifted "+col)
    merged["B0_ARCHIVED_N4"]=merged.N4_NONLINEAR_TOP15
    assert len(merged)==64*149 and merged.block.nunique()==64
    for m in METHODS:
        if not np.isfinite(merged[m]).all():raise AssertionError("nonfinite "+m)
    if not(pd.to_datetime(merged.latest_train_outcome_maturity)<
           pd.to_datetime(merged.signal)).all():
        raise AssertionError("Future label inside fitted model")
    return merged,eval_ids

def bootstrap(values):
    x=np.asarray(values,float)
    n=len(x)
    assert n==64
    rng=np.random.default_rng(SEED+99)
    vals=[]
    for _ in range(1500):
        ix=[]
        while len(ix)<n:
            start=int(rng.integers(n))
            ix.extend((start+j)%n for j in range(3))
        vals.append(float(x[np.asarray(ix[:n],int)].mean()))
    return dict(mean=float(np.mean(x)),
        ci95=np.quantile(vals,[.025,.975]).tolist(),n_anchors=n)

def metrics(frame,ids,opens,names,dates):
    score={}
    chosen={}
    curves={}
    rows=[]
    for model in METHODS:
        select=[]
        for b in ids:
            s=frame.loc[frame.block==b]
            s=s.sort_values([model,"ticker"],ascending=[False,True])
            p=s.head(5)
            select.append(p.ticker.tolist())
            actual_future_best=s.loc[s.future_log.idxmax(),"ticker"]
            # ndcg using fixed relevance; higher (not excess raw) is better.
            nscore=float(ndcg_score(s.graded_relevance.to_numpy(float)[None,:],
                                  s[model].to_numpy(float)[None,:],k=10))
            x=spearmanr(s[model],s.future_excess).statistic
            baseline=spearmanr(s.B0_ARCHIVED_N4,s.future_excess).statistic
            rows.append(dict(model=model,block=int(b),signal=s.signal.iloc[0],
                spearman=float(x),spearman_delta_vs_B0=float(x-baseline),
                precision10=float(s.head(10).top15.mean()),
                precision5=float(p.top15.mean()),
                hit_future_best_top5=int(actual_future_best in set(p.ticker)),
                chosen_top5_return_excess=float(p.future_excess.mean()),
                chosen_bottom15_fraction=float(p.bottom15.mean()),
                selected_group_count=int(p.category.nunique()),
                chosen_prior_vol63=float(p.v63.mean()),
                ndcg10=nscore))
        equity,economics=portfolio(select,ids,opens,names,dates)
        curves[model]=equity
        chosen[model]=select
        r=pd.DataFrame([x for x in rows if x["model"]==model])
        early=r[pd.to_datetime(r.signal).dt.year<=2023]
        late=r[pd.to_datetime(r.signal).dt.year>=2024]
        if len(early)<20 or len(late)<20:raise AssertionError("wrong regime windows")
        period={period:dict(n=len(sub),
            spearman=float(sub.spearman.mean()),
            spearman_delta_vs_B0=float(sub.spearman_delta_vs_B0.mean()),
            precision10=float(sub.precision10.mean()),
            forward_excess=float(sub.chosen_top5_return_excess.mean()),
            bottom15_rate=float(sub.chosen_bottom15_fraction.mean()))
            for period,sub in (("2021_2023",early),("2024_2026",late))}
        if model in ("D1_RAW63_LGBM","D2_ENGINEERED_LGBM",
                     "D3_CONTEXT_LGBM","B0_ARCHIVED_N4"):
            p=frame[model].clip(.00001,.99999).to_numpy(float)
            y=frame.top15.to_numpy(float)
            proper=dict(brier=float(np.mean((p-y)**2)),
                log_loss=float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p))),
                probability_mean=float(np.mean(p)))
        else:proper=None
        skill=bootstrap(r.spearman.to_numpy(float))
        uplift=bootstrap(r.spearman_delta_vs_B0.to_numpy(float))
        score[model]=dict(economics=economics,
            mean_spearman=float(r.spearman.mean()),
            precision10=float(r.precision10.mean()),
            precision5=float(r.precision5.mean()),
            future_best_hit_in_top5=int(r.hit_future_best_top5.sum()),
            forward_top5_excess=float(r.chosen_top5_return_excess.mean()),
            chosen_bottom15_fraction=float(r.chosen_bottom15_fraction.mean()),
            average_63day_vol_selected=float(r.chosen_prior_vol63.mean()),
            average_categories_in_top5=float(r.selected_group_count.mean()),
            graded_ndcg10=float(r.ndcg10.mean()),
            score_calibration=proper,
            spearman_ci=skill,
            paired_spearman_delta_vs_N4_ci=uplift,
            by_period=period)
        print("T149D_MODEL_RESULT",model,json.dumps(score[model]),flush=True)
    panel=pd.DataFrame(rows)
    c=score["B0_ARCHIVED_N4"]
    gates={}
    for model in METHODS[1:]:
        v=score[model];p=v["by_period"];gates[model]=bool(
            v["paired_spearman_delta_vs_N4_ci"]["ci95"][0]>0 and
            v["precision10"]>c["precision10"] and
            v["chosen_bottom15_fraction"]<c["chosen_bottom15_fraction"] and
            p["2021_2023"]["spearman_delta_vs_B0"]>0 and
            p["2024_2026"]["spearman_delta_vs_B0"]>0)
    # Independently verify B0 N4 costed capital curve parity, not only labels.
    ref=json.loads((PARENT/"RESULT.json").read_text())
    for key in ("cagr","max_daily_open_drawdown","daily_es5",
                "fee_amount_initial_units"):
        actual=score["B0_ARCHIVED_N4"]["economics"][key]
        old=ref["metrics"]["N4_NONLINEAR_TOP15"]["economics"][key]
        if abs(actual-old)>1e-10:raise AssertionError("N4 financial parity drift "+key)
    w=pd.DataFrame({"day":dates[ids[0]*21:(ids[-1]+1)*21+1]})
    for m,x in curves.items():w[m]=x
    w.to_csv("PLACEHOLDER",index=False) if False else None
    return score,gates,panel,w

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    args=a.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    full,roster,days,opens,names=dataset()
    _,_,closes,_,_,_,_=load_149()
    full=expand_features(full,closes,roster)
    pred,ids=training(full)
    score,gates,panel,wealth=metrics(pred,ids,opens,names,days)
    panel.to_csv(out/"PER_64_ANCHOR_MODEL_RANK_RESULTS.csv",index=False)
    wealth.to_csv(out/"TOP5_ALL_MODEL_COSTED_WEALTH_DAILY.csv",index=False)
    preds=pred[["block","signal","entry","maturity","ticker","category","future_log",
        "future_excess","top15","bottom15","graded_relevance",
        "latest_train_outcome_maturity","n_prior_matured_anchors",
        *METHODS,"D5_TOP15_PROB","D5_BOTTOM15_PROB"]]
    preds.to_csv(out/"COMPLETE_9536_TICKER_PREDICTIONS.csv",index=False)
    result=dict(status="T149D_FEATURE_AND_OBJECTIVE_EXPLORATORY_DONE",
        original_etfs=149,exact_source_sha=sha(SRC/"universe.csv"),
        previous_149_N4_baseline_economics_identical=True,
        feature_families=dict(raw63=63,engineered=19,
            asset_categories=6,crosssectional_rank_features=15),
        chronological_matured_labels_only=True,
        no_new_future_information_or_pit_certification=True,
        n_evaluation_21day_anchors=64,
        n_ticker_month_predictions=len(pred),
        models=score,preregistered_skill_gates=gates,
        best_by_precision10=max(METHODS,key=lambda m:score[m]["precision10"]),
        best_by_rank_spearman=max(METHODS,key=lambda m:score[m]["mean_spearman"]),
        must_not_select_model_using_same_researched_2021_2026_sample=True,
        caveats=["Same historical 149 universe, extensively tested before; multiple model comparisons",
                 "Yahoo adjusted OHLC not executable broker quotes, no true PIT fund membership",
                 "N4 original scores obtained from frozen archive, not refitted",
                 "Learning-to-rank score is not a calibrated event probability",
                 "CAGR and drawdown secondary exploratory outcomes not generalization evidence",
                 "No leverage/FX/bid-ask/taxes, no untouched future interval"])
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("T149D_FINAL_RESULT",json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
