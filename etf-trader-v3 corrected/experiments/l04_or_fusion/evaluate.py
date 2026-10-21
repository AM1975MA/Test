#!/usr/bin/env python3
"""V3 L04.3: One OR/union-rank aggregation hypothesis, all experts frozen.

Primary hypothesis: the two frozen experts miss different actual winners;
a MAX of each cross-universe percentile may preserve disjoint top signals
better than a static arithmetic blend. Compare Tail and existing 50/50
on identical 101 fully matured 21D months. No optimized weights, no model
fit, no CAGR, no other layers active.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr

SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
ARMS=["TAIL_ELITE45","BLEND50","OR_MAX","RRF_K10"]
METRICS=["basket_top1","basket_top3","basket_ndcg3","basket_regret","universe_ic"]

def month_results(group,baskets):
    a=group.sort_values("ticker")
    assert len(a)==149 and a.fwd_ret_21.notna().all()
    lookup={name:i for i,name in enumerate(a.ticker)}
    y=a.fwd_ret_21.to_numpy(float)
    preds={k:a[k].to_numpy(float) for k in ARMS}
    out=[]
    for name,score in preds.items():
        vals=[]
        for basket in baskets:
            idx=np.array([lookup[t] for t in basket],int)
            predicted=np.argsort(-score[idx],kind="stable")
            future=y[idx]
            oracle=np.argsort(-future,kind="stable")
            ranks=np.empty(len(idx),float);ranks[oracle]=np.linspace(1,0,len(idx))
            discount=1/np.log2(np.arange(2,5))
            ndcg=np.dot(ranks[predicted[:3]],discount)/np.dot(np.sort(ranks)[::-1][:3],discount)
            vals.append((float(int(oracle[0])==int(predicted[0])),
                float(int(oracle[0]) in predicted[:3]),
                float(ndcg),float(future.max()-future[predicted[0]])))
        v=np.array(vals)
        out.append({"signal_date":pd.Timestamp(a.signal_date.iloc[0]),"year":int(a.signal_date.iloc[0].year),
             "variant":name,"basket_top1":float(v[:,0].mean()),
             "basket_top3":float(v[:,1].mean()),
             "basket_ndcg3":float(v[:,2].mean()),
             "basket_regret":float(v[:,3].mean()),
             "universe_ic":float(spearmanr(score,y).statistic),
             "n_baskets":len(baskets)})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prior",default="runs/v3_l04_reference")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l04_or")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    original=pd.read_csv(a.baskets)
    original.ticker=original.ticker.astype(str).str.upper()
    baskets=[g.ticker.tolist() for _,g in original.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(baskets)==500 and all(len(q)==24 for q in baskets)
    df=pd.read_csv(Path(a.prior)/"OOS_SCORES_ALL_FIXED_BLENDS.csv",parse_dates=["signal_date"])
    assert len(df)==15198 and not df.duplicated(["signal_date","ticker"]).any()
    assert set(original.ticker)<=set(df.ticker)
    ranker=df.RANKER127.to_numpy(float);tail=df.TAIL_ELITE45.to_numpy(float)
    # No look-ahead: both scores are already truly historical OOS signals.
    df["OR_MAX"]=np.maximum(ranker,tail)
    # Predeclared reciprocal rank fusion with k=10. Alternative aggregation,
    # not a tuned parameter; RRF gives consensus higher priority.
    p=df.groupby("signal_date")["RANKER127"].rank(ascending=False,method="average")
    t=df.groupby("signal_date")["TAIL_ELITE45"].rank(ascending=False,method="average")
    df["RRF_K10"]=1/(10+p)+1/(10+t)
    rows=[]
    for date,g in df.groupby("signal_date",sort=True):
        if g.fwd_ret_21.isna().any():continue
        rows.extend(month_results(g,baskets))
    monthly=pd.DataFrame(rows)
    assert len(monthly)==101*len(ARMS)
    assert not monthly.duplicated(["variant","signal_date"]).any()
    summary=monthly.groupby("variant")[METRICS].mean()
    summary.insert(0,"months",monthly.groupby("variant").size())
    monthly.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    summary.to_csv(out/"RESULTS.csv")
    monthly.groupby(["year","variant"],as_index=False)[METRICS].mean().to_csv(out/"YEARLY.csv",index=False)
    df[["signal_date","ticker","fwd_ret_21","TAIL_ELITE45","BLEND50","OR_MAX","RRF_K10"]].to_csv(out/"OOS_SCORES.csv",index=False)
    boot=[]
    for reference in ["TAIL_ELITE45","BLEND50"]:
        ref=monthly[monthly.variant==reference].sort_values("signal_date").reset_index(drop=True)
        for cand in ["OR_MAX","RRF_K10"]:
            x=monthly[monthly.variant==cand].sort_values("signal_date").reset_index(drop=True)
            pd.testing.assert_series_equal(ref.signal_date,x.signal_date)
            for metric in METRICS:
                delta=(x[metric]-ref[metric]).to_numpy(float)
                assert np.isfinite(delta).all()
                n=len(delta);rng=np.random.default_rng(20261021);reps=5000;block=6
                starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
                indices=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
                sim=delta[indices].mean(axis=1)
                boot.append({"arm":cand,"reference":reference,"metric":metric,
                    "delta":float(delta.mean()),"ci95_low":float(np.quantile(sim,.025)),
                    "ci95_high":float(np.quantile(sim,.975)),
                    "resample_unit":"calendar month, 6-month circular blocks"})
    pd.DataFrame(boot).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
       "layer":"L04.3 expert OR and reciprocal rank aggregation",
       "all_models_frozen":True,"source_score_run":39659903643,
       "rff_parameter_k_fixed":10,"no_weight_or_model_tuning":True,
       "same_149_etfs_500_baskets":True,"101_matured_months":True,
       "objective":"paired upper-winner Top3, nDCG, regret; no CAGR",
       "no_risk_regime_allocation":True,
       "historical_test_reused_exploratory":True},indent=2))
    print("L04_OR_RESULTS\n"+summary.to_string(),flush=True)

if __name__=="__main__":main()
