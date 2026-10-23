#!/usr/bin/env python3
"""Research-only post-ranker experiments, from the EXACT frozen OOS head predictions.

mode=exponential: strictly positive multiplicative weighting, unconditional or
confidence-gated; mode=tree: meta DecisionTreeClassifier trained only on matured
earlier OOS pairwise decisions, out-of-time evaluation.

No first-stage refitting. No V2/V3 production changes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import timedelta
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from aggregate import read_shards, metric_for_order

REGS=("REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
LAMS=(.05,.10,.20,.35,.50,.75,1.,1.5,2.,3.,4.)
GATE_LAMS=(.2,.5,1.,2.)
GAPS=(.02,.05,.10)
EDGES=(.05,.15)
TREE_DEPTHS=(1,2,3)
TREE_LEAVES=(100,300)
TREE_THRESHOLDS=(.55,.60,.65)
TREE_WINDOWS=("expanding","last36")
METRICS=("basket_top1","basket_top3","basket_ndcg3","basket_regret",
         "basket_selected_excess","basket_loss10_top1")

def load(shards,membership):
    scores, monthly, audit=read_shards(shards,"regression")
    wide=scores.pivot(index=["signal_date","ticker"],columns="variant",values="pred")
    y=scores[scores.variant=="CORRECTED"].set_index(["signal_date","ticker"])["fwd_ret_21"]
    wide=wide.join(y,how="inner")
    assert wide.index.is_unique
    dates=set(monthly.loc[monthly.variant=="CORRECTED","signal_date"])
    wide=wide.loc[wide.index.get_level_values("signal_date").isin(dates)]
    assert wide.index.get_level_values("signal_date").nunique()==101
    baskets=pd.read_csv(membership)
    assert set(baskets.columns)=={"basket","ticker"} and baskets.basket.nunique()==500
    assert (baskets.groupby("basket").size()==24).all()
    bm=[list(g.ticker) for _,g in baskets.groupby("basket",sort=True)]
    months=[]
    for date,group in wide.groupby(level=0,sort=True):
        dt=pd.Timestamp(date)
        g=group.reset_index(level=0,drop=True).sort_index()
        g=g.dropna(subset=["CORRECTED","fwd_ret_21"]+list(REGS))
        names=list(g.index)
        ids={t:i for i,t in enumerate(names)}
        def pct(name):
            return g[name].rank(pct=True).to_numpy(float)
        vals={"rank":pct("CORRECTED"),"fwd":g.fwd_ret_21.to_numpy(float)}
        vals.update({r:pct(r) for r in REGS})
        selections=[]
        for names_b in bm:
            idx=np.array([ids[t] for t in names_b if t in ids],dtype=int)
            if len(idx)<2: continue
            orig=np.argsort(-vals["rank"][idx],kind="stable")
            selections.append((idx,orig))
        assert len(selections)==500,(dt,len(selections))
        months.append((dt,vals,selections))
    assert len(months)==101
    return months,monthly

def run_exp(months):
    arm_keys=["CORRECTED"]
    for lam in LAMS:
        for scope in ("ALL","TOP3"):
            arm_keys.append(f"EXP_{scope}_REL125_{lam:g}")
    for lam in GATE_LAMS:
        for gap in GAPS:
            for edge in EDGES:
                arm_keys.append(f"GATE_TOP3_REL125_{lam:g}_G{gap:g}_E{edge:g}")
    records=[]; corrections=[]
    for date,v,baskets in months:
        cache={lam:v["rank"]*np.exp(lam*(2*v["REG_REL125"]-1)) for lam in LAMS}
        # Predeclared gated weights, no learning/tuning on evaluation targets.
        gc={lam:v["rank"]*np.exp(lam*(2*v["REG_REL125"]-1)) for lam in GATE_LAMS}
        scores={arm:[] for arm in arm_keys}
        changes={arm:[0,0,0] for arm in arm_keys if arm!="CORRECTED"}
        for idx,orig in baskets:
            yy=v["fwd"][idx]
            base=metric_for_order(orig,yy)
            scores["CORRECTED"].append(base[:6])
            top=orig[:min(3,len(orig))]
            b=v["rank"][idx]
            r=v["REG_REL125"][idx]
            candidate=int(top[np.argmax(r[top])])
            margin=float(b[orig[0]]-b[orig[1]])
            edge=float(r[candidate]-r[orig[0]])
            for lam in LAMS:
                weighted=cache[lam][idx]
                entire=np.argsort(-weighted,kind="stable")
                local=np.concatenate((top[np.argsort(-weighted[top],kind="stable")],orig[len(top):]))
                for scope,order in (("ALL",entire),("TOP3",local)):
                    key=f"EXP_{scope}_REL125_{lam:g}"
                    m=metric_for_order(order,yy)
                    scores[key].append(m[:6])
                    if m[6]!=base[6]:
                        z=changes[key];z[0]+=1;z[1]+=int(yy[m[6]]>yy[base[6]]);z[2]+=int(yy[m[6]]<yy[base[6]])
            for lam in GATE_LAMS:
                weighted=gc[lam][idx]
                local=np.concatenate((top[np.argsort(-weighted[top],kind="stable")],orig[len(top):]))
                for gap in GAPS:
                    for minimum in EDGES:
                        key=f"GATE_TOP3_REL125_{lam:g}_G{gap:g}_E{minimum:g}"
                        order=local if (margin<=gap and edge>=minimum and candidate!=orig[0]) else orig
                        m=metric_for_order(order,yy)
                        scores[key].append(m[:6])
                        if m[6]!=base[6]:
                            z=changes[key];z[0]+=1;z[1]+=int(yy[m[6]]>yy[base[6]]);z[2]+=int(yy[m[6]]<yy[base[6]])
        records.extend(make_rows(date,scores))
        corrections.extend(make_changes(date,changes,len(baskets)))
        print("EXP",date.date(),len(baskets),flush=True)
    return pd.DataFrame(records),pd.DataFrame(corrections),{}

def pair_features(v,idx,orig,alternative):
    rank=v["rank"][idx]
    first=int(orig[0]);j=int(alternative)
    top=orig[:min(3,len(orig))]
    rr=v["REG_REL125"][idx]
    ar=v["REG_ABS125"][idx]
    rv=v["REG_REL101"][idx]
    h=v["REG_HUBER125"][idx]
    av=v["REG_ABS101"][idx]
    return [
        float(rank[first]-rank[j]),
        float(rank[first]-rank[orig[1]]),
        float(rank[first]-rank[top[-1]]),
        float(rank[first]),float(rank[j]),
        float(rr[j]-rr[first]),
        float(rv[j]-rv[first]),
        float(ar[j]-ar[first]),
        float(av[j]-av[first]),
        float(h[j]-h[first]),
        float(rr[first]),float(rr[j]),
        float(ar[j]),
        float(np.std(rank[top])),
    ]

def prepare_tree_months(months):
    data=[]
    for dt,v,baskets in months:
        pair_features_unique={}
        for idx,orig in baskets:
            t=orig[0]
            for alt in orig[1:3]:
                a=int(idx[t]);b=int(idx[alt])
                k=(a,b)
                if k not in pair_features_unique:
                    pair_features_unique[k]=(pair_features(v,idx,orig,alt),
                                             int(v["fwd"][b]>v["fwd"][a]))
        X=np.asarray([x for x,y in pair_features_unique.values()],dtype=float)
        y=np.asarray([y for x,y in pair_features_unique.values()],dtype=np.int8)
        assert np.isfinite(X).all() and len(X)>=50
        data.append((dt,X,y))
    return data

def make_rows(date,scores):
    records=[]
    for arm,arr in scores.items():
        a=np.asarray(arr,dtype=float)
        assert a.ndim==2 and a.shape[1]==6 and len(a)>0,(date,arm,a.shape)
        z=dict(variant=arm,signal_date=date,year=date.year,n_baskets=len(a))
        z.update({name:float(a[:,i].mean()) for i,name in enumerate(METRICS)})
        records.append(z)
    return records

def make_changes(date,changes,n):
    return [dict(variant=k,signal_date=date,changed=c[0],changes_better=c[1],
                 changes_worse=c[2],n_baskets=n)
            for k,c in changes.items()]

def run_trees(months):
    prepared=prepare_tree_months(months)
    arms=["CORRECTED"]+[f"TREE_{window}_D{depth}_N{leaf}_P{threshold:g}"
        for window in TREE_WINDOWS for depth in TREE_DEPTHS
        for leaf in TREE_LEAVES for threshold in TREE_THRESHOLDS]
    records=[];changes=[];fits=[]
    models={}
    latest_quarter=None
    for i,(dt,v,baskets) in enumerate(months):
        quarter=(dt.year,(dt.month-1)//3)
        if quarter!=latest_quarter:
            historical=[(d,x,y) for d,x,y in prepared
                        if d < dt-pd.Timedelta(days=60)]
            if len(historical)>=24:
                models={}
                for window in TREE_WINDOWS:
                    selected=historical if window=="expanding" else historical[-36:]
                    XX=np.concatenate([a[1] for a in selected])
                    yy=np.concatenate([a[2] for a in selected])
                    # Equal weight for each month after deduplicating ticker pairs;
                    # do not pretend overlapping baskets are independent.
                    ww=np.concatenate([np.full(len(a[2]),1./len(a[2])) for a in selected])
                    for depth in TREE_DEPTHS:
                        for leaf in TREE_LEAVES:
                            model=DecisionTreeClassifier(criterion="log_loss",max_depth=depth,
                                min_samples_leaf=leaf,random_state=20261024)
                            model.fit(XX,yy,sample_weight=ww)
                            models[(window,depth,leaf)]=model
                            fits.append(dict(model=f"{window}_D{depth}_N{leaf}",date=str(dt.date()),
                                train_first=str(selected[0][0].date()),
                                train_last=str(selected[-1][0].date()),
                                matured_lag_min_days=60,train_months=len(selected),
                                unique_pairs=len(yy),positive_rate=float(np.average(yy,weights=ww)),
                                nodes=int(model.tree_.node_count),depth_fitted=model.get_depth()))
            else:
                models={}
            latest_quarter=quarter
        score={arm:[] for arm in arms}
        changed={arm:[0,0,0] for arm in arms if arm!="CORRECTED"}
        for idx,orig in baskets:
            yy=v["fwd"][idx]
            baseline=metric_for_order(orig,yy)
            score["CORRECTED"].append(baseline[:6])
            top=orig[:min(3,len(orig))]
            alternatives=list(top[1:])
            xx=np.asarray([pair_features(v,idx,orig,alt) for alt in alternatives],dtype=float)
            assert np.isfinite(xx).all()
            for window in TREE_WINDOWS:
                for depth in TREE_DEPTHS:
                    for leaf in TREE_LEAVES:
                        model=models.get((window,depth,leaf))
                        if model is not None and len(model.classes_)==2:
                            p=model.predict_proba(xx)[:,list(model.classes_).index(1)]
                            take=int(np.argmax(p))
                            chosen=int(alternatives[take])
                            prob=float(p[take])
                        else:
                            chosen=int(orig[0]);prob=0.
                        for threshold in TREE_THRESHOLDS:
                            key=f"TREE_{window}_D{depth}_N{leaf}_P{threshold:g}"
                            if prob>threshold and chosen!=orig[0]:
                                order=np.concatenate(([chosen],orig[orig!=chosen]))
                            else:
                                order=orig
                            m=metric_for_order(order,yy)
                            score[key].append(m[:6])
                            if m[6]!=baseline[6]:
                                z=changed[key];z[0]+=1;z[1]+=int(yy[m[6]]>yy[baseline[6]]);z[2]+=int(yy[m[6]]<yy[baseline[6]])
        records.extend(make_rows(dt,score))
        changes.extend(make_changes(dt,changed,len(baskets)))
        print("TREE",dt.date(),"fit_history",sum(1 for d,_,_ in prepared if d<dt-pd.Timedelta(days=60)),
              "model_count",len(models),flush=True)
    return pd.DataFrame(records),pd.DataFrame(changes),{"fitting_audit":fits}

def bootstrap(monthly,seed=240026,n=2000):
    rng=np.random.default_rng(seed)
    ctrl=monthly[monthly.variant=="CORRECTED"].set_index("signal_date").sort_index()
    assert len(ctrl)==101
    m=len(ctrl); results=[]
    idxs=np.concatenate([
        np.concatenate([(np.arange(6)+s)%m for s in rng.integers(0,m,size=(m+5)//6)])[:m][None,:]
        for _ in range(n)
    ])
    for arm in sorted(set(monthly.variant)-{"CORRECTED"}):
        t=monthly[monthly.variant==arm].set_index("signal_date").sort_index()
        assert t.index.equals(ctrl.index)
        for metric in METRICS[:-1]:
            dx=(t[metric]-ctrl[metric]).to_numpy(float)
            draws=dx[idxs].mean(axis=1)
            results.append(dict(variant=arm,metric=metric,delta=float(dx.mean()),
                ci025=float(np.quantile(draws,.025)),ci975=float(np.quantile(draws,.975)),
                months=m,block_months=6,replicates=n))
    return pd.DataFrame(results)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("exponential","tree"),required=True)
    p.add_argument("--shards",required=True)
    p.add_argument("--membership",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--reference",default=None)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    months, reference=load(a.shards,a.membership)
    if a.mode=="exponential":
        m,c,additional=run_exp(months)
    else:
        m,c,additional=run_trees(months)
    assert not m.duplicated(["signal_date","variant"]).any()
    assert m.signal_date.nunique()==101
    original=m[m.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    baseline=reference[reference.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    assert original.signal_date.equals(baseline.signal_date)
    np.testing.assert_allclose(original[list(METRICS[:-1])],baseline[list(METRICS[:-1])],
        rtol=0,atol=1e-12,err_msg="MUST reproduce validated oracle exactly")
    assert not (m.n_baskets!=500).any()
    if a.mode=="tree":
        top=m.pivot(index="signal_date",columns="variant",values="basket_top3")
        assert np.allclose(top.to_numpy(),top.CORRECTED.to_numpy()[:,None],atol=1e-12)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    summary=m.groupby("variant")[list(METRICS)].mean()
    summary.insert(0,"months",m.groupby("variant").size())
    agg=c.groupby("variant")[["changed","changes_better","changes_worse","n_baskets"]].sum()
    summary=summary.join(agg,how="left")
    summary["change_rate"]=summary.changed/summary.n_baskets
    summary["change_winrate"]=summary.changes_better/(summary.changes_better+summary.changes_worse)
    summary.to_csv(out/"SUMMARY.csv")
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    bootstrap(m).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    c.to_csv(out/"CORRECTIONS.csv",index=False)
    m.groupby(["variant","year"])[list(METRICS)].mean().to_csv(out/"YEARLY.csv")
    (out/"AUDIT.json").write_text(json.dumps(additional,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       mode=a.mode,base_run=40016809498,months=101,etfs=149,baskets=500,
       basket_size=24,forward_horizon="21 trading days next open",
       no_first_stage_refitting=True,meta_maturity_lag_days=60,
       tree_training_pair_unique_by_month_tickers=True,
       meta_fit_every_three_months=True,strict_oos=True,
       exploratory_not_pristine_holdout=True,
       production_modified=False),indent=2))
    print("PARALLEL_META_SUCCESS",a.mode,len(summary),"variants",flush=True)
    print(summary.sort_values("basket_top1",ascending=False).head(20).to_string(),flush=True)
    print("SELECTED_EXCESS",flush=True)
    print(summary.sort_values("basket_selected_excess",ascending=False).head(20).to_string(),flush=True)
if __name__=="__main__":
    main()
