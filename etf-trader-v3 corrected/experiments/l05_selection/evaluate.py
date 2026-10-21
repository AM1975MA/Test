#!/usr/bin/env python3
"""V3 L05: portfolio selection quality with FIXED Tail expert ranks.

One policy-layer intervention: compare four predeclared weight schedules
applied to identical fully OOS monthly Tail45 scores for 500 canonical baskets:
  V2_LIKE: 100% Top1 if score-percentile gap>=0.12, else Top2 75/25
  TOP1_100: 100% Top1
  TOP3_EQUAL: each Top3 1/3
  TOP3_DECAY: Top1 50%, Top2 30%, Top3 20%.

NO CAGR or long-run returns, no cash/stop, no change in expert, regime, risk or
execution. Competing policy "skill" is measured by future within-basket
quality percentile, weighted winner capture, selection regret, bottom-decile
exposure, position concentration and target-weight turnover/churn.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd

POLICIES=("V2_LIKE","TOP1_100","TOP3_EQUAL","TOP3_DECAY")
BASKET_SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def weights(scores,policy):
    if policy=="V2_LIKE":
        # This is the original hard-coded 75/25 vs top1 override.
        if scores[0]-scores[1]>=.12:return np.array([1.,0.,0.])
        return np.array([.75,.25,0.])
    if policy=="TOP1_100":return np.array([1.,0.,0.])
    if policy=="TOP3_EQUAL":return np.array([1/3,1/3,1/3])
    if policy=="TOP3_DECAY":return np.array([.50,.30,.20])
    raise ValueError(policy)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--predictions",default="runs/v3_l04_static/OOS_SCORES_ALL_FIXED_BLENDS.csv")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l05_selection")
    a=p.parse_args()
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==BASKET_SHA
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    labels=pd.read_csv(a.predictions,parse_dates=["signal_date"])
    assert len(labels)==15198 and not labels.duplicated(["signal_date","ticker"]).any()
    assert {"TAIL_ELITE45","fwd_ret_21","signal_date","ticker"}<=set(labels.columns)
    raw=pd.read_csv(a.baskets)
    raw.ticker=raw.ticker.astype(str).str.upper()
    b=[g.ticker.tolist() for _,g in raw.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(b)==500 and all(len(x)==24 for x in b)
    assert set(raw.ticker)<=set(labels.ticker.unique())
    # Basket holdings tracked by target weights, not prices, to separate
    # selection churn from actual execution costs and price drift.
    prev={name:[None]*len(b) for name in POLICIES}
    rows=[]
    for dt,group in labels.groupby("signal_date",sort=True):
        if group.fwd_ret_21.isna().any():continue
        g=group.sort_values("ticker").reset_index(drop=True)
        assert len(g)==149
        lookup={t:i for i,t in enumerate(g.ticker)}
        future=g.fwd_ret_21.to_numpy(float)
        score=g.TAIL_ELITE45.to_numpy(float)
        day={name:[] for name in POLICIES}
        for j,basket in enumerate(b):
            idx=np.array([lookup[t] for t in basket],dtype=int)
            yy=future[idx];ss=score[idx]
            order=np.argsort(-ss,kind="stable")
            top=idx[order[:3]]
            f=yy[order[:3]]
            raworder=np.argsort(-yy,kind="stable")
            true_best=int(raworder[0])
            value=np.empty(len(idx),float);value[raworder]=np.linspace(1,0,len(idx))
            bottom_three=set(raworder[-3:].tolist())
            for policy in POLICIES:
                w=weights(ss[order[:3]],policy)
                assert np.isclose(w.sum(),1)
                rank_quality=float(np.dot(w,value[order[:3]]))
                weighted_regret=float(yy.max()-np.dot(w,f))
                weighted_excess=float(np.dot(w,f)-yy.mean())
                weight_best=float(w[np.where(order[:3]==true_best)[0][0]]) if true_best in order[:3] else 0.
                bottom_weight=float(np.sum([w[k] for k,x in enumerate(order[:3]) if int(x) in bottom_three]))
                positions={g.ticker.iloc[top[k]]:float(w[k]) for k in range(3) if w[k]>0}
                old=prev[policy][j]
                churn=np.nan if old is None else float(sum(abs(positions.get(t,0)-old.get(t,0))
                        for t in set(positions)|set(old))/2)
                prev[policy][j]=positions
                day[policy].append((rank_quality,weighted_regret,weighted_excess,
                    weight_best,bottom_weight,float(1/np.sum(w**2)),churn,
                    float(len(positions)),float(max(w))))
        for policy in POLICIES:
            z=np.array(day[policy],float)
            rows.append({"signal_date":dt,"year":int(dt.year),"variant":policy,
                "n_baskets":len(b),"weighted_true_rank_quality":float(z[:,0].mean()),
                "weighted_oracle_regret21":float(z[:,1].mean()),
                "weighted_basket_excess21":float(z[:,2].mean()),
                "weighted_winner_capture":float(z[:,3].mean()),
                "bottom_three_weight":float(z[:,4].mean()),
                "effective_n_holdings":float(z[:,5].mean()),
                "target_weight_churn":float(np.nanmean(z[:,6])) if np.isfinite(z[:,6]).any() else np.nan,
                "mean_n_holdings":float(z[:,7].mean()),
                "max_position_weight":float(z[:,8].mean())})
    df=pd.DataFrame(rows)
    assert len(df)==101*len(POLICIES)
    assert not df.duplicated(["signal_date","variant"]).any()
    df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    metrics=["weighted_true_rank_quality","weighted_oracle_regret21",
        "weighted_basket_excess21","weighted_winner_capture",
        "bottom_three_weight","effective_n_holdings",
        "target_weight_churn","mean_n_holdings","max_position_weight"]
    summary=df.groupby("variant")[metrics].mean()
    summary.insert(0,"months",df.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    df.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
    ref=df[df.variant=="V2_LIKE"].sort_values("signal_date").reset_index(drop=True)
    boot=[]
    for policy in POLICIES[1:]:
        challenger=df[df.variant==policy].sort_values("signal_date").reset_index(drop=True)
        pd.testing.assert_series_equal(ref.signal_date,challenger.signal_date)
        for col in metrics:
            diff=(challenger[col]-ref[col]).to_numpy(float)
            if col=="target_weight_churn":diff=diff[1:]
            assert np.isfinite(diff).all()
            n=len(diff);rng=np.random.default_rng(20261021);block=6;reps=6000
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
            ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
            sim=diff[ix].mean(axis=1)
            boot.append({"policy":policy,"reference":"V2_LIKE","metric":col,
                "mean_delta":float(diff.mean()),
                "ci95_lower":float(np.quantile(sim,.025)),
                "ci95_upper":float(np.quantile(sim,.975)),
                "unit":"paired signal month, 6-month circular block bootstrap"})
    pd.DataFrame(boot).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
        "layer":"L05 allocation policy intrinsic selection fitness",
        "expert":"frozen corrected Tail45 top-decile logistic OOS score from run 39655513813",
        "score_source":"frozen paired L04 run 39659903643",
        "outcomes":"same-next-21-trading-day observed ETF returns used for conditional quality diagnostics",
        "selection_functions":POLICIES,
        "score_weights_and_model_frozen":True,
        "risk_turned_on":False,"regime_turned_on":False,
        "no_CAGR":True,
        "turnover_caveat":"Target-weight position churn, NOT execution turnover including price drift",
        "historical_calendar":"repeatedly examined 101 OOS months, not untouched future test"},indent=2))
    print("V3_L05_SELECTION_RESULTS\n"+summary.to_string(),flush=True)

if __name__=="__main__":main()
