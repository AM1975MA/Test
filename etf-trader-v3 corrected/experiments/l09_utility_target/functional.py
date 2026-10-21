#!/usr/bin/env python3
"""L09 function-first audit: do corrected125 utility labels improve selected ETFs?

Use only archived OOS scores, one future 21D evaluation target, 500 original
canonical baskets and both previously frozen Top2/Top3 selection policies.
No price replay or CAGR is needed for this intrinsic test.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
MODELS={"LEGACY":"old","CORRECTED":"old",
        "L09_EXCESS21":"new","L09_DOWNSIDE21":"new"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--old",required=True)
    p.add_argument("--new",required=True)
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    b=pd.read_csv(a.baskets);b.ticker=b.ticker.astype(str).str.upper()
    baskets=[g.ticker.tolist() for _,g in b.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(baskets)==500 and all(len(x)==24 for x in baskets)
    df_old=pd.read_csv(a.old,parse_dates=["signal_date"])
    df_new=pd.read_csv(a.new,parse_dates=["signal_date"])
    frames={}
    for name,source in MODELS.items():
        f=(df_old if source=="old" else df_new)
        s=f[f.variant==name][["signal_date","ticker","pred","fwd_ret_21"]].copy()
        assert len(s)==15198 and not s.duplicated(["signal_date","ticker"]).any()
        frames[name]=s
    dates=sorted(frames["LEGACY"].signal_date.unique())
    data=[]
    for date in dates:
        chunks={name:frame[frame.signal_date.eq(date)].sort_values("ticker")
                for name,frame in frames.items()}
        standard=chunks["LEGACY"]
        if standard.fwd_ret_21.isna().any():continue
        lookup={t:i for i,t in enumerate(standard.ticker)}
        ix=np.array([[lookup[t] for t in basket] for basket in baskets],int)
        yy=standard.fwd_ret_21.to_numpy(float)[ix]
        actual=np.argsort(-yy,axis=1,kind="stable")
        worst=set() # computed rowwise below
        truebest=actual[:,0]
        quality=np.empty_like(yy)
        quality[np.arange(500)[:,None],actual]=np.linspace(1,0,24)
        for name,g in chunks.items():
            pd.testing.assert_series_equal(g.ticker.reset_index(drop=True),
                                           standard.ticker.reset_index(drop=True))
            np.testing.assert_allclose(g.fwd_ret_21,standard.fwd_ret_21,atol=1e-14,rtol=0)
            all_pct=g.pred.rank(method="average",pct=True).to_numpy(float)
            pval=all_pct[ix]
            rank=np.argsort(-pval,axis=1,kind="stable")
            chosen=np.take_along_axis(yy,rank[:,:3],axis=1)
            chosen_q=np.take_along_axis(quality,rank[:,:3],axis=1)
            chosen_idx=rank[:,:3]
            truebottom3=(actual[:,-3:,None]==chosen_idx[:,None,:]).any(axis=1)
            truebest3=(truebest[:,None]==chosen_idx)
            predicted_pct=np.take_along_axis(pval,rank[:,:3],axis=1)
            is_best3=(truebest3[:,0]|truebest3[:,1]|truebest3[:,2]).mean()
            for policy in ["TOP2","TOP3"]:
                if policy=="TOP2":
                    weight1=np.where(predicted_pct[:,0]-predicted_pct[:,1]>=.12,1.,.75)
                    weights=np.stack([weight1,1-weight1,np.zeros(500)],axis=1)
                else:
                    weights=np.broadcast_to(np.array([.5,.3,.2]),(500,3))
                data.append({
                    "signal_date":date,"year":int(date.year),"variant":name,
                    "policy":policy,"n_baskets":500,
                    "weighted_realized_rank":float((weights*chosen_q).sum(axis=1).mean()),
                    "weighted_realized_21d_excess":float(((weights*chosen).sum(axis=1)-yy.mean(axis=1)).mean()),
                    "weighted_regret_21d":float((yy.max(axis=1)-(weights*chosen).sum(axis=1)).mean()),
                    "abs_loss10_weight":float((weights*(chosen<=-.10)).sum(axis=1).mean()),
                    "basket_bottom3_weight":float((weights*truebottom3).sum(axis=1).mean()),
                    "weight_on_best":float((weights*truebest3).sum(axis=1).mean()),
                    "top3_best_event":float(is_best3)
                })
    d=pd.DataFrame(data);assert len(d)==101*4*2
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    d.to_csv(out/"FUNCTIONAL_MONTHLY.csv",index=False)
    metrics=["weighted_realized_rank","weighted_realized_21d_excess",
        "weighted_regret_21d","abs_loss10_weight","basket_bottom3_weight",
        "weight_on_best","top3_best_event"]
    d.groupby(["variant","policy"])[metrics].mean().to_csv(out/"FUNCTIONAL_SUMMARY.csv")
    paired=[]
    for policy in ["TOP2","TOP3"]:
        ref=d[(d.variant=="CORRECTED")&(d.policy==policy)].sort_values("signal_date").reset_index(drop=True)
        excess=d[(d.variant=="L09_EXCESS21")&(d.policy==policy)].sort_values("signal_date").reset_index(drop=True)
        penalty=d[(d.variant=="L09_DOWNSIDE21")&(d.policy==policy)].sort_values("signal_date").reset_index(drop=True)
        for trial,base in [(excess,ref),(penalty,ref),(penalty,excess)]:
            for col in metrics:
                x=(trial[col]-base[col]).to_numpy(float)
                rng=np.random.default_rng(20261022)
                n=len(x);block=6;reps=4000
                starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
                idx=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
                z=x[idx].mean(axis=1)
                paired.append({"policy":policy,"trial":trial.variant.iloc[0],
                    "reference":base.variant.iloc[0],"metric":col,"delta":float(x.mean()),
                    "ci95_low":float(np.quantile(z,.025)),
                    "ci95_high":float(np.quantile(z,.975))})
    pd.DataFrame(paired).to_csv(out/"FUNCTIONAL_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
        "layer":"L09 functional only 21D selected-invested ETF quality",
        "models":list(MODELS),"holdings_policies":["TOP2","TOP3"],
        "n_months":101,"n_etfs":149,"original_500_baskets":True,
        "same_mature_outcomes":True,"source_model_retrained_here":False,
        "target_asymmetric_loss_threshold":-.10,
        "cagr_used":False,"historical_period_repeatedly_researched":True},indent=2))
    print("L09_FUNCTIONAL",d.groupby(["variant","policy"])[metrics].mean().to_string(),flush=True)
if __name__=="__main__":main()
