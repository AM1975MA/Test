#!/usr/bin/env python3
"""V3 L04: frozen corrected Ranker + frozen winner Tail score complementarity.

No learner fit, no macro gate, no cost, no execution, no allocator, no risk.
Predeclare exactly TWO equal-month rank blends (50/50; 25/75 pair/Tail).
Measure winner capture, nDCG@3 and regret against each frozen expert.
Fit-free, chronology-safe: all source expert predictions were made in
prequential expanding-year OOS runs with fully matured labels.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np,pandas as pd
from scipy.stats import spearmanr

BASE="RANKER127"
TAIL="TAIL_ELITE45"
ARMS={BASE:1.0,TAIL:0.0,"BLEND50":.50,"BLEND25PAIR_75TAIL":.25}
BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def read_baskets(path,valid):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==BASKET_SHA
    raw=pd.read_csv(path)
    raw.ticker=raw.ticker.astype(str).str.upper()
    assert len(raw)==12000 and raw.basket.nunique()==500
    assert set(raw.ticker)<=set(valid)
    b=[g.ticker.tolist() for _,g in raw.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(b)==500 and all(len(x)==24 for x in b)
    return b

def month_report(frame,baskets):
    # All 149 true matured future 21-trading-day returns are identical.
    if frame.fwd_ret_21.isna().any():return None,None
    f=frame.sort_values("ticker")
    truth=f.fwd_ret_21.to_numpy(float)
    where={t:i for i,t in enumerate(f.ticker)}
    if len(f)!=149:raise RuntimeError(f"Different 149 ETF universe at {f.signal_date.iloc[0]}")
    ranks={}
    for name,wt in ARMS.items():
        if name==BASE:ranks[name]=f.pair_percentile.to_numpy(float)
        elif name==TAIL:ranks[name]=f.tail_percentile.to_numpy(float)
        else:ranks[name]=wt*f.pair_percentile.to_numpy(float)+(1-wt)*f.tail_percentile.to_numpy(float)
    outputs={}
    capture={name:[] for name in [BASE,TAIL]}
    for name,p in ranks.items():
        metrics=[]
        for basket in baskets:
            idx=np.array([where[t] for t in basket],dtype=int)
            order=np.argsort(-p[idx],kind="stable")
            future=truth[idx]
            oracle=np.argsort(-future,kind="stable")
            b0=int(oracle[0])
            selected=int(order[0])
            top=set(order[:3])
            truth_rank=int(np.where(oracle==selected)[0][0])+1
            rel=np.empty(len(idx),float)
            rel[oracle]=np.linspace(1,0,len(idx))
            discount=1/np.log2(np.arange(2,5))
            normal=np.dot(np.sort(rel)[::-1][:3],discount)
            ndcg=float(np.dot(rel[order[:3]],discount)/normal)
            best_in_top=int(b0 in top)
            metrics.append((best_in_top,int(b0==selected),
                            float(future.max()-future[selected]),
                            float(future[selected]-future.mean()),
                            ndcg,float(1/truth_rank)))
            if name in capture:capture[name].append(best_in_top)
        m=np.asarray(metrics,float)
        outputs[name]={"signal_date":f.signal_date.iloc[0],"year":int(f.signal_date.iloc[0].year),
            "variant":name,"basket_top1":float(m[:,1].mean()),
            "basket_top3":float(m[:,0].mean()),
            "basket_regret":float(m[:,2].mean()),
            "basket_selected_excess":float(m[:,3].mean()),
            "basket_ndcg3":float(m[:,4].mean()),
            "basket_mrr_selected":float(m[:,5].mean()),
            "universe_ic":float(spearmanr(p,truth).statistic),
            "n_baskets":len(baskets),"n_tickers":len(f)}
    a=np.array(capture[BASE],bool);b=np.array(capture[TAIL],bool)
    overlap={"signal_date":f.signal_date.iloc[0],
             "both_hit":float(np.mean(a&b)),
             "pair_only":float(np.mean(a&~b)),
             "tail_only":float(np.mean(b&~a)),
             "neither_hit":float(np.mean(~a&~b)),
             "hit_union":float(np.mean(a|b)),
             "score_spearman":float(spearmanr(f.pair_percentile,f.tail_percentile).statistic)}
    return outputs,overlap

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ranker",default="runs/v3_l01_reference")
    p.add_argument("--tail",default="runs/v3_l02_reference")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l04_fusion")
    a=p.parse_args()
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    allpair=pd.read_csv(Path(a.ranker)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    alltail=pd.read_csv(Path(a.tail)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    pair=allpair.loc[allpair.variant=="CORRECTED",
         ["signal_date","ticker","pred","fwd_ret_21"]].rename(columns={"pred":"pair"})
    tail=alltail.loc[alltail.variant=="TAIL_EVENT_LOGIT45",
         ["signal_date","ticker","pred","fwd_ret_21"]].rename(
             columns={"pred":"tail","fwd_ret_21":"tail_future"})
    assert not pair.duplicated(["signal_date","ticker"]).any()
    assert not tail.duplicated(["signal_date","ticker"]).any()
    frame=pair.merge(tail,on=["signal_date","ticker"],validate="one_to_one")
    assert len(frame)==len(pair)==len(tail)==15198
    np.testing.assert_allclose(frame.fwd_ret_21,frame.tail_future,atol=1e-14,rtol=0,equal_nan=True)
    b=read_baskets(a.baskets,frame.ticker.unique())
    frame["pair_percentile"]=frame.groupby("signal_date").pair.rank(method="average",pct=True)
    frame["tail_percentile"]=frame.groupby("signal_date")["tail"].rank(method="average",pct=True)
    results=[];overlaps=[]
    for dt,g in frame.groupby("signal_date",sort=True):
        item,overlap=month_report(g,b)
        if item is None:continue
        results.extend(item.values());overlaps.append(overlap)
    months=pd.DataFrame(results)
    overlap=pd.DataFrame(overlaps)
    assert overlap.shape[0]==101 and len(months)==101*len(ARMS)
    for name in ARMS:
        assert months.variant.eq(name).sum()==101
    months.to_csv(dest/"PAIRED_MONTHLY.csv",index=False)
    overlap.to_csv(dest/"EXPERT_COMPLEMENTARITY.csv",index=False)
    metrics=["basket_top1","basket_top3","basket_regret","basket_selected_excess",
       "basket_ndcg3","basket_mrr_selected","universe_ic"]
    summary=months.groupby("variant")[metrics].mean()
    summary.insert(0,"months",months.groupby("variant").size())
    summary.to_csv(dest/"RESULTS.csv")
    months.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(dest/"YEARLY.csv",index=False)
    boot=[]
    ref=months[months.variant==TAIL].sort_values("signal_date").reset_index(drop=True)
    for name in ["BLEND50","BLEND25PAIR_75TAIL"]:
        curr=months[months.variant==name].sort_values("signal_date").reset_index(drop=True)
        pd.testing.assert_series_equal(ref.signal_date,curr.signal_date)
        for metric in metrics:
            dif=(curr[metric]-ref[metric]).to_numpy(float)
            assert np.isfinite(dif).all()
            n=len(dif);rng=np.random.default_rng(20261021);reps=6000;block=6
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
            ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
            sims=dif[ix].mean(axis=1)
            boot.append({"arm":name,"reference":TAIL,"metric":metric,
              "delta":float(dif.mean()),
              "ci95_low":float(np.quantile(sims,.025)),
              "ci95_high":float(np.quantile(sims,.975)),
              "method":"paired calendar month 6-month circular blocks, 6000 reps"})
    pd.DataFrame(boot).to_csv(dest/"PAIRED_BOOTSTRAP.csv",index=False)
    scoreframe=frame[["signal_date","ticker","fwd_ret_21"]].copy()
    for name,pair_weight in ARMS.items():
        if name==BASE:scoreframe[name]=frame.pair_percentile
        elif name==TAIL:scoreframe[name]=frame.tail_percentile
        else:scoreframe[name]=pair_weight*frame.pair_percentile+(1-pair_weight)*frame.tail_percentile
    scoreframe.to_csv(dest/"OOS_SCORES_ALL_FIXED_BLENDS.csv",index=False)
    (dest/"MANIFEST.json").write_text(json.dumps({
        "layer":"L04 frozen expert fusion",
        "arms":{"RANKER127":1.0,"TAIL_ELITE45":0.0,"BLEND50":0.5,
                "BLEND25PAIR_75TAIL":0.25},
        "weight_definition":"pairwise expert rank percentile weight, complement Tail",
        "selection_weights":"predeclared and NOT learned from OOS results",
        "ranker_source_run":39652989033,"tail_source_run":39655513813,
        "raw_label_snapshot":39482809691,
        "matured_OOS_21day_months":101,
        "train_stage":"none; frozen prequential expert outputs only",
        "model_or_labels_refit":False,"regime_risk_macro_allocation":False,
        "cagr":False,"historical_calendar_not_virgin":True},indent=2))
    print("V3_L04_BLEND_RESULTS\n"+summary.to_string(),flush=True)
    print("V3_L04_EXPERT_COMPLEMENTARITY\n"+overlap.drop(columns=["signal_date"]).mean().to_string(),flush=True)

if __name__=="__main__":main()
