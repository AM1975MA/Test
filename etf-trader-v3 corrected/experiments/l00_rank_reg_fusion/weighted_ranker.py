#!/usr/bin/env python3
"""Counterfactual: multiplicative regression weighting of precomputed OOS ranker scores.

All data are original out-of-year model predictions. No training or target leakage.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from aggregate import read_shards, metric_for_order

LAMS = (0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75)
REGRESSORS = ("REG_REL125", "REG_REL101", "REG_ABS125", "REG_ABS101", "REG_HUBER125")
MEASURES = ("basket_top1", "basket_top3", "basket_ndcg3",
            "basket_regret", "basket_selected_excess")
def arm_name(reg, lam, restrict):
    return f"W{'3' if restrict else 'ALL'}_{reg}_L{int(round(lam*100)):02d}"

def score_month(g, membership):
    g = g.dropna(subset=["fwd_ret_21","CORRECTED"] + list(REGRESSORS)).sort_index()
    assert g.index.is_unique
    lookup = {ticker:i for i,ticker in enumerate(g.index)}
    vals = g["fwd_ret_21"].to_numpy(dtype=float)
    base = g["CORRECTED"].rank(pct=True).to_numpy(dtype=float)
    reg = {name: g[name].rank(pct=True).to_numpy(dtype=float) for name in REGRESSORS}
    # Preserve baseline XGBRanker cross-sectional ordering. Weighting never
    # multiplies raw (possibly negative) decision values.
    assert np.isfinite(base).all()
    assert all(np.isfinite(v).all() for v in reg.values())
    weighted = {
        (name,lam): base * (1.0 + lam * (2.0 * rank - 1.0))
        for name,rank in reg.items() for lam in LAMS
    }
    outputs = {"CORRECTED": []}
    corrections = {}
    for name in REGRESSORS:
        for lam in LAMS:
            for restrict in (False, True):
                key = arm_name(name,lam,restrict)
                outputs[key] = []
                corrections[key] = [0,0,0]
    for basket_id, names in membership.items():
        ids=np.array([lookup[t] for t in names if t in lookup],dtype=int)
        if len(ids)<2:
            continue
        y=vals[ids]
        b=base[ids]
        baseline=np.argsort(-b,kind="stable")
        ori=metric_for_order(baseline,y)
        outputs["CORRECTED"].append(ori[:6])
        for (name,lam), w in weighted.items():
            ww=w[ids]
            full=np.argsort(-ww,kind="stable")
            top3=baseline[:min(3,len(baseline))]
            local=np.concatenate((top3[np.argsort(-ww[top3],kind="stable")], baseline[len(top3):]))
            for restrict, order in ((False,full),(True,local)):
                key=arm_name(name,lam,restrict)
                cur=metric_for_order(order,y)
                outputs[key].append(cur[:6])
                if cur[6] != ori[6]:
                    correction=corrections[key]
                    correction[0]+=1
                    correction[1]+=int(y[cur[6]]>y[ori[6]])
                    correction[2]+=int(y[cur[6]]<y[ori[6]])
    assert all(len(v)==len(outputs["CORRECTED"]) for v in outputs.values())
    return outputs, corrections

def bootstrap(monthly, measures=MEASURES, seed=230026, n_boot=3000):
    rng=np.random.default_rng(seed)
    orig=monthly[monthly.variant=="CORRECTED"].set_index("signal_date").sort_index()
    m=len(orig)
    assert m==101
    blocks=np.concatenate([
        ((rng.integers(0,m,size=((m+5)//6))[:,None]+np.arange(6)[None,:])%m).reshape(-1)[:m][None,:]
        for _ in range(n_boot)
    ],axis=0)
    rows=[]
    for variant in sorted(set(monthly.variant)-{"CORRECTED"}):
        frame=monthly[monthly.variant==variant].set_index("signal_date").sort_index()
        assert frame.index.equals(orig.index),variant
        for measure in measures:
            diff=(frame[measure]-orig[measure]).to_numpy(dtype=float)
            rep=diff[blocks].mean(axis=1)
            rows.append(dict(variant=variant,measure=measure,
                delta=float(diff.mean()),ci025=float(np.quantile(rep,.025)),
                ci975=float(np.quantile(rep,.975)),
                months=m,block_months=6,samples=n_boot))
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shards",required=True)
    p.add_argument("--membership",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    s, ref, audits = read_shards(a.shards,"regression")
    basket_csv=pd.read_csv(a.membership)
    assert set(basket_csv.columns)=={"basket","ticker"}
    assert basket_csv.basket.nunique()==500
    assert (basket_csv.groupby("basket").size()==24).all()
    basket={int(k):list(g.ticker) for k,g in basket_csv.groupby("basket",sort=True)}
    wide=s.pivot(index=["signal_date","ticker"],columns="variant",values="pred")
    target=s[s.variant=="CORRECTED"].set_index(["signal_date","ticker"])["fwd_ret_21"]
    wide=wide.join(target,how="inner")
    assert wide.index.is_unique
    # Original saved scores also include 2026-06, which has no fully matured
    # 21-day outcome. Use EXACTLY the 101 certified evaluation months.
    mature_dates=set(ref.loc[ref.variant=="CORRECTED","signal_date"])
    wide=wide.loc[wide.index.get_level_values("signal_date").isin(mature_dates)]
    assert len(wide.index.get_level_values("signal_date").unique())==101
    result=[]; corrections=[]
    for date,group in wide.groupby(level=0,sort=True):
        dt=pd.Timestamp(date)
        g=group.reset_index(level=0,drop=True)
        outputs, changes=score_month(g,basket)
        for name, obs in outputs.items():
            stats=np.asarray(obs,dtype=float)
            result.append(dict(variant=name,signal_date=dt,year=dt.year,
                n_baskets=len(obs),
                basket_top1=stats[:,0].mean(),
                basket_top3=stats[:,1].mean(),
                basket_ndcg3=stats[:,2].mean(),
                basket_regret=stats[:,3].mean(),
                basket_selected_excess=stats[:,4].mean(),
                basket_loss10_top1=stats[:,5].mean()))
        for key,(changed,better,worse) in changes.items():
            corrections.append(dict(variant=key,signal_date=dt,
                changed=changed,changes_better=better,changes_worse=worse,
                n_baskets=len(outputs["CORRECTED"])))
        print("COMPLETED_MONTH",dt.date(),flush=True)
    m=pd.DataFrame(result);c=pd.DataFrame(corrections)
    assert m.signal_date.nunique()==101
    assert not m.duplicated(["variant","signal_date"]).any()
    assert (m.pivot(index="signal_date",columns="variant",values="n_baskets").nunique(axis=1)==1).all()
    original=m[m.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    reference=ref[ref.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    assert original.signal_date.equals(reference.signal_date)
    np.testing.assert_allclose(original[list(MEASURES)].to_numpy(),
        reference[list(MEASURES)].to_numpy(),atol=1e-12,rtol=0,
        err_msg="Reconstructed original basket scores must EXACTLY match 2026-10-23 validated run")
    for name in [arm_name(r,lam,True) for r in REGRESSORS for lam in LAMS]:
        part=m[m.variant==name].sort_values("signal_date").reset_index(drop=True)
        np.testing.assert_allclose(part.basket_top3,original.basket_top3,atol=1e-12,rtol=0,
            err_msg="Top3-only mode must preserve original ranker Top3 exactly")
    boot=bootstrap(m)
    summary=m.groupby("variant")[list(MEASURES)].mean()
    summary["months"]=m.groupby("variant").size()
    tally=c.groupby("variant")[["changed","changes_better","changes_worse","n_baskets"]].sum()
    summary=summary.join(tally,how="left")
    summary["change_rate"]=summary.changed/summary.n_baskets
    summary["change_winrate"]=summary.changes_better/(summary.changes_better+summary.changes_worse)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/"SUMMARY.csv")
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    boot.to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    c.to_csv(out/"CORRECTIONS.csv",index=False)
    m.groupby(["variant","year"])[list(MEASURES)].mean().to_csv(out/"YEARLY.csv")
    (out/"MANIFEST.json").write_text(json.dumps({
        "algorithm":"Positive ranker cross-sectional percentile multiplied by [1 + lambda*(2*regressor_crosssectional_percentile-1)]",
        "feature_years":"2018-2026",
        "base_run":40016809498,
        "no_retraining":True,
        "regressors":list(REGRESSORS),
        "lambdas":list(LAMS),
        "modes":["ALL: weighted entire basket","3: reorders original Top3 only; original Top3 membership preserved"],
        "lookahead":False,
        "not_pristine_holdout":True,
        "production_modified":False,
        "statistical_unit":"calendar month; 6-month paired circular block bootstrap, 3000 draws"
    },indent=2))
    print("MULTIPLICATIVE_WEIGHTING_COMPLETE",flush=True)
    print(summary.sort_values("basket_top3",ascending=False).head(18).to_string(),flush=True)
    print("BEST_SELECTED_EXCESS",flush=True)
    print(summary.sort_values("basket_selected_excess",ascending=False).head(18).to_string(),flush=True)

if __name__=="__main__":
    main()
