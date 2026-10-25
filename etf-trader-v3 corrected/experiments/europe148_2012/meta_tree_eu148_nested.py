#!/usr/bin/env python3
"""EUR148 genuine V3 corrected meta decision tree, causal nested replay.

Predictor inputs: genuine corrected 31-leaf first-stage rank and five 125/101
regression heads, 2018..2026-05 OOS. 500 dynamic category-balanced 24-ISIN
baskets each signal date are dependent TRAINING contexts, NOT independent NAVs.
Use globally unique (top1,alternative) pair events per date for fit. Frozen
prior V3 families: expanding/last36, depths 1/2/3, min leaf 100/300, .55/.60/.65.
Quarterly tree fit only on signals whose labels matured >=60 calendar days ago.
24 older matured OOS months select challenger only if basket top1 not worse
and 21-day selected excess improves. Real EUR single portfolio executes after
the signal at next Xetra Open with 10bp one-way and daily valuation.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.tree import DecisionTreeClassifier
from evaluate_corrected_economics import nav_sim,load_predictions,REF

BASE="V3_LEAF31"
REGS=("REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
WINDOWS=("expanding","last36")
DEPTHS=(1,2,3)
LEAVES=(100,300)
THRESHOLDS=(.55,.60,.65)
FAMILIES=[(w,d,l) for w in WINDOWS for d in DEPTHS for l in LEAVES]
TREE_NAMES=[f"TREE_{w}_D{d}_N{l}_P{p:g}" for w,d,l in FAMILIES for p in THRESHOLDS]
CLUSTERS=("EU_EQUITY_BROAD","EU_EQUITY_SECTOR","EU_EQUITY_COUNTRY",
          "EU_EQUITY_FACTOR","SOVEREIGN_EUR","EU_PROPERTY")

def pair_features(v,idx,orig,alternative):
    rank=v["rank"][idx];first=int(orig[0]);j=int(alternative)
    top=orig[:min(3,len(orig))]
    rr=v["REG_REL125"][idx];ar=v["REG_ABS125"][idx]
    rv=v["REG_REL101"][idx];h=v["REG_HUBER125"][idx];av=v["REG_ABS101"][idx]
    z=np.array([rank[first]-rank[j],rank[first]-rank[orig[1]],
      rank[first]-rank[top[-1]],rank[first],rank[j],
      rr[j]-rr[first],rv[j]-rv[first],ar[j]-ar[first],
      av[j]-av[first],h[j]-h[first],rr[first],rr[j],ar[j],
      np.std(rank[top])],dtype=float)
    assert len(z)==14 and np.isfinite(z).all()
    return z

def build_months(heads,roster):
    p=load_predictions(heads)
    expect={BASE,*REGS}
    p=p[p.variant.isin(expect)]
    wide=p.pivot(index=["signal_date","ticker"],columns="variant",values="pred")
    assert set(wide.columns)==expect
    label=p[p.variant.eq(BASE)].set_index(["signal_date","ticker"]).fwd_ret_21
    wide=wide.join(label.rename("fwd"))
    assert wide.index.get_level_values("signal_date").nunique()==101
    cat=roster.set_index("ticker").macro_category
    out=[]
    for ix,(date,g) in enumerate(wide.groupby(level="signal_date",sort=True)):
        g=g.droplevel("signal_date")
        assert g.index.is_unique and len(g)>=24
        g=g.sort_index()
        assert g.notna().all().all(),(date,g.isna().sum())
        n=len(g)
        names=g.index.to_numpy()
        y=g.fwd.to_numpy(dtype=float)
        rank_raw=g[BASE].to_numpy(float)
        order=np.argsort(-rank_raw,kind="stable")
        value={"rank":g[BASE].rank(pct=True).to_numpy(float),"fwd":y}
        for r in REGS:value[r]=g[r].rank(pct=True).to_numpy(float)
        by_category={k:np.flatnonzero(cat.loc[names].to_numpy()==k) for k in CLUSTERS}
        assert all(len(j)>=4 for j in by_category.values()),(date, {c:len(x) for c,x in by_category.items()})
        rng=np.random.default_rng(20261025+ix)
        baskets=[]
        pairs={}
        for j in range(500):
            index=np.concatenate([rng.choice(by_category[k],size=4,replace=False)
                                  for k in CLUSTERS])
            orig=np.argsort(-rank_raw[index],kind="stable")
            baskets.append((index,orig))
            first=int(index[orig[0]])
            for alt_local in orig[1:3]:
                alt=int(index[alt_local])
                key=(first,alt)
                if key not in pairs:
                    pairs[key]=(pair_features(value,index,orig,alt_local),
                        int(y[alt]>y[first]))
        X=np.asarray([x for x,_ in pairs.values()],float)
        Y=np.asarray([int(v) for _,v in pairs.values()],np.int8)
        assert X.ndim==2 and X.shape[1]==14 and len(Y)>15
        out.append(dict(date=pd.Timestamp(date),names=names,y=y,raw=rank_raw,
                        v=value,full_order=order,
                        baskets=baskets,X=X,Y=Y,
                        unique_pair_count=len(pairs),
                        basket_memberships_sha256=hashlib.sha256(
                            np.asarray([ix for ix,_ in baskets],np.int16).tobytes()).hexdigest()))
    assert len(out)==101 and out[0]["date"]==pd.Timestamp("2018-01-31")
    assert out[-1]["date"]==pd.Timestamp("2026-05-29")
    return out

def fit_models(hist,dt):
    prev=[m for m in hist if m["date"]<dt-pd.Timedelta(days=60)]
    if len(prev)<24:return {},len(prev),0
    models={}
    for window in WINDOWS:
        use=prev if window=="expanding" else prev[-36:]
        X=np.concatenate([m["X"] for m in use])
        Y=np.concatenate([m["Y"] for m in use])
        weight=np.concatenate([np.full(len(m["Y"]),1/len(m["Y"])) for m in use])
        for d in DEPTHS:
            for l in LEAVES:
                t=DecisionTreeClassifier(criterion="log_loss",max_depth=d,
                       min_samples_leaf=l,random_state=20261024)
                t.fit(X,Y,sample_weight=weight)
                models[(window,d,l)]=t
    return models,len(prev),len(X)

def assess(chosen,order,index,y):
    f=y[index]
    winner=int(np.argmax(f))
    return np.array([float(chosen==winner),float(f[chosen]-f.mean())])

def choose_tree(monthly_history,dt):
    prior=sorted(d for d in monthly_history if d<dt-pd.Timedelta(days=60))[-24:]
    if len(prior)<24:return "CORRECTED",0, len(prior)
    control=np.array([monthly_history[d]["CORRECTED"] for d in prior])
    best="CORRECTED";value=0.
    for arm in TREE_NAMES:
        trial=np.array([monthly_history[d][arm] for d in prior])
        gain=float((trial[:,1]-control[:,1]).mean())
        hit=float((trial[:,0]-control[:,0]).mean())
        if gain>value and hit>=0:
            best=arm;value=gain
    return best,value,len(prior)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--heads",required=True);ap.add_argument("--raw",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    roster=pd.read_csv(Path(a.raw)/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    assert len(roster)==roster["isin"].nunique()==148
    months=build_months(a.heads,roster)
    results=[];meta_history={};fit_audit=[];pair_audit=[];modified=[]
    fitted={};q_last=None
    for m in months:
        dt=m["date"]
        key=(dt.year,(dt.month-1)//3)
        if key!=q_last:
            fitted,n_mature,events=fit_models(months,dt)
            q_last=key
            fit_audit.append(dict(quarter_start=str(dt.date()),
                train_months=n_mature,unique_event_rows_last_fit=events,
                fitted_families=len(fitted)))
        v=m["v"];raw=m["raw"];y=m["y"]
        basket=m["baskets"]
        x=np.asarray([pair_features(v,idx,orig,z)
                  for idx,orig in basket for z in orig[1:3]],float)
        assert x.shape==(1000,14)
        probs={}
        for k,t in fitted.items():
            if len(t.classes_)==2:
                probs[k]=t.predict_proba(x)[:,list(t.classes_).index(1)].reshape(500,2)
        scores={arm:[] for arm in ["CORRECTED"]+TREE_NAMES}
        for bi,(index,orig) in enumerate(basket):
            f=y[index]
            scores["CORRECTED"].append(assess(int(orig[0]),orig,index,y))
            for w,d,l in FAMILIES:
                val=probs.get((w,d,l))
                if val is None:alt=int(orig[0]);conf=0.
                else:
                    loc=int(np.argmax(val[bi]))
                    alt=int(orig[loc+1]);conf=float(val[bi,loc])
                for threshold in THRESHOLDS:
                    arm=f"TREE_{w}_D{d}_N{l}_P{threshold:g}"
                    chosen=alt if conf>threshold else int(orig[0])
                    scores[arm].append(assess(chosen,orig,index,y))
        meta_history[dt]={arm:np.asarray(x).mean(axis=0)
                          for arm,x in scores.items()}
        selected,gain,older=choose_tree(meta_history,dt)
        global_order=m["full_order"].copy()
        chosen_index=int(global_order[0])
        chosen_prob=0.
        if selected!="CORRECTED":
            import re
            match=re.fullmatch(r"TREE_(expanding|last36)_D([123])_N(100|300)_P(0\.\d+)",selected)
            assert match,selected
            family=(match.group(1),int(match.group(2)),int(match.group(3)))
            cutoff=float(match.group(4))
            t=fitted.get(family)
            if t is not None and len(t.classes_)==2:
                original_top=global_order[:3]
                full_idx=np.arange(len(raw))
                features=np.asarray([pair_features(v,full_idx,original_top,j)
                   for j in original_top[1:]],float)
                pr=t.predict_proba(features)[:,list(t.classes_).index(1)]
                i=int(np.argmax(pr))
                chosen_prob=float(pr[i])
                if chosen_prob>cutoff:chosen_index=int(original_top[i+1])
        source_order=global_order.copy()
        if chosen_index!=int(global_order[0]):
            global_order=np.r_[chosen_index,global_order[global_order!=chosen_index]]
        assert set(global_order)==set(source_order)
        assert chosen_index in source_order[:3]
        modified.append(dict(date=dt,variant="META31",ticker=m["names"][chosen_index],
               pred=float(np.max(raw)+1.) if chosen_index!=int(source_order[0])
                   else float(raw[chosen_index]),
               chosen_rank_original=int(np.flatnonzero(source_order==chosen_index)[0]+1),
               root_ticker=m["names"][source_order[0]]))
        pair_audit.append(dict(signal_date=str(dt.date()),
            unique_pair_events=m["unique_pair_count"],
            basket_contexts=500,raw_isin=len(m["names"])))
        results.append(dict(signal_date=str(dt.date()),selected=selected,
            mature_months_for_selection=older,selection_gain_past21d=gain,
            unique_pair_events=m["unique_pair_count"],
            ranked_first=m["names"][source_order[0]],
            tree_top1=m["names"][chosen_index],
            top1_changed=int(chosen_index!=int(source_order[0])),
            selected_candidate_rank_original=int(np.flatnonzero(source_order==chosen_index)[0]+1),
            tree_confidence=chosen_prob,
            base_return21=float(y[source_order[0]]),meta_return21=float(y[chosen_index]),
            delta_return21=float(y[chosen_index]-y[source_order[0]]),
            max_forward21=float(y.max()),base_true_winner=int(source_order[0]==np.argmax(y)),
            meta_true_winner=int(chosen_index==np.argmax(y)),
            base_excess21=float(y[source_order[0]]-y.mean()),
            meta_excess21=float(y[chosen_index]-y.mean())))
    log=pd.DataFrame(results)
    assert len(log)==101
    log.to_csv(out/"EUR148_101M_NESTED_TREE_DECISIONS.csv",index=False)
    pd.DataFrame(pair_audit).to_csv(out/"EUR148_UNIQUE_PAIR_EVENTS.csv",index=False)
    pd.DataFrame(fit_audit).to_csv(out/"EUR148_META_FIT_AUDIT.csv",index=False)
    # Economic simulator sorts per ISIN raw predictions. Force selected
    # top1 score only when a tree swap occurred; other ETF score unchanged.
    preds=load_predictions(a.heads)
    base=preds[preds.variant.eq(BASE)].copy()
    meta=base.copy()
    meta["variant"]="EU148_NESTED_TREE_ON_LEAF31"
    overrides=pd.DataFrame(modified)
    changed=overrides[overrides.ticker.ne(overrides.root_ticker)]
    for row in changed.itertuples():
        mask=meta.signal_date.eq(row.date)&meta.ticker.eq(row.ticker)
        assert mask.sum()==1
        meta.loc[mask,"pred"]=row.pred
    tests=pd.concat([meta],ignore_index=True)
    quotes={};vol={}
    for isin in roster.ticker:
        q=pd.read_csv(Path(a.raw)/"raw_ticker_csv"/(isin+".csv"),parse_dates=["date"]).set_index("date")
        quotes[isin]=q.Open;vol[isin]=q.Volume
    O=pd.concat(quotes,axis=1).sort_index()
    V=pd.concat(vol,axis=1).sort_index()
    cal=O[REF].dropna().index
    O=O.reindex(cal);V=V.reindex(cal)
    sc=[];navs=[];ledger=[]
    for top in (1,2,3,5):
        s,n,l=nav_sim(tests,O,V,cal,"EU148_NESTED_TREE_ON_LEAF31",top)
        sc.append(s);navs.append(n);ledger.append(l)
    pd.DataFrame(sc).to_csv(out/"EUR148_META_TREE_ECONOMICS.csv",index=False)
    pd.concat(navs).to_csv(out/"EUR148_META_TREE_NAV.csv",index=False)
    pd.concat(ledger).to_csv(out/"EUR148_META_TREE_TRADES.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        research_only=True,months=101,legal_isin_count=148,
        cohort_dynamic=True,monthly_baskets=500,isin_per_basket=24,
        balanced_six_categories=True,
        training_unique_pair_events_deduped=True,
        no_holdout_independence_500_contexts=True,
        tree_family_n=36,quarterly_refits=True,embargo_days=60,
        selector_24_mature_months=True,selection_observable_asof=True,
        leaf31_prior_candidate_from_EU48_not_preregistered_fresh_holdout=True,
        EUR_next_open_single_portfolio=True,
        one_way_fee_bps=10,no_stage19_risk=True,
        original_operation_untouched=True),indent=2))
    print("EU148_META_TREE_EUR_PASS",pd.DataFrame(sc).to_string(index=False),flush=True)
    print("EU148_META_TOP1_CHANGES",int(log.top1_changed.sum()),
           "TREE_MONTHS",int(log.selected.ne("CORRECTED").sum()),flush=True)

if __name__=="__main__":main()
