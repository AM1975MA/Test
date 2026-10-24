#!/usr/bin/env python3
"""June 2026 out-of-time single-month check using ALREADY FROZEN June signals.

Original first-stage scores were archived with missing future label on run
40016809498; only realized July next-open OHLCV is added. No ranker retrain.
The V3 meta selector is selected using prior matured months only; exact
historical decision tree fits using historical pair labels and 60d embargo.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.tree import DecisionTreeClassifier
from parallel_meta import load,prepare_tree_months,pair_features,METRICS,REGS
from aggregate import metric_for_order
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder
DATE=pd.Timestamp("2026-06-30")
PAT=re.compile(r"^TREE_(expanding|last36)_D([123])_N(100|300)_P(0\.(?:55|6|65))$")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shards",required=True)
    ap.add_argument("--raw",required=True)
    ap.add_argument("--tree",required=True)
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    old,ref=load(a.shards,a.baskets)
    assert old[-1][0]==pd.Timestamp("2026-05-29") and len(old)==101
    scores=pd.read_csv(Path(a.shards)/"regression"/"s3"/"OOS_SCORES.csv",parse_dates=["signal_date"])
    june=scores[scores.signal_date.eq(DATE)]
    assert len(june)==6*149 and june.fwd_ret_21.isna().all()
    assert set(june.variant)=={"CORRECTED",*REGS}
    raw,cat,_=load_ticker_csv_folder(a.raw)
    op=raw["Open"];days=op.index
    p=int(days.get_indexer([DATE])[0]);assert p>=0
    entry=days[p+1];exit=days[p+1+21];assert exit<=pd.Timestamp("2026-08-03")
    realized=op.loc[exit]/op.loc[entry]-1
    assert np.isfinite(realized).all() and len(realized)==149
    g=june.pivot(index="ticker",columns="variant",values="pred").sort_index()
    y=realized.reindex(g.index)
    assert np.isfinite(y).all()
    v={"rank":g.CORRECTED.rank(pct=True).to_numpy(float),"fwd":y.to_numpy(float)}
    v.update({r:g[r].rank(pct=True).to_numpy(float) for r in REGS})
    names=list(g.index);ids={t:i for i,t in enumerate(names)}
    m=pd.read_csv(a.baskets)
    selections=[]
    for _,b in m.groupby("basket",sort=True):
        idx=np.array([ids[t] for t in b.ticker],dtype=int)
        orig=np.argsort(-v["rank"][idx],kind="stable")
        selections.append((idx,orig))
    assert len(selections)==500
    tree_month=pd.read_csv(Path(a.tree)/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
    dates=sorted(d for d in tree_month.signal_date.unique() if d<DATE-pd.Timedelta(days=60))[-24:]
    assert len(dates)==24
    hist=tree_month[tree_month.signal_date.isin(dates)]
    baseline=hist[hist.variant.eq("CORRECTED")].sort_values("signal_date")
    choice="CORRECTED";best=0.
    for arm,df in hist[hist.variant.ne("CORRECTED")].groupby("variant",sort=True):
        df=df.sort_values("signal_date")
        dex=(df.basket_selected_excess.to_numpy()-baseline.basket_selected_excess.to_numpy()).mean()
        dt1=(df.basket_top1.to_numpy()-baseline.basket_top1.to_numpy()).mean()
        if dex>best and dt1>=0:choice=arm;best=float(dex)
    fitted=None;threshold=None
    if choice!="CORRECTED":
        match=PAT.fullmatch(choice);assert match,choice
        window,depth,leaf,cut=match.groups()
        prepared=prepare_tree_months(old)
        qstart=pd.Timestamp("2026-04-30")
        prior=[(d,X,z) for d,X,z in prepared if d<qstart-pd.Timedelta(days=60)]
        assert len(prior)>=24
        prior=prior if window=="expanding" else prior[-36:]
        X=np.concatenate([z[1] for z in prior]);label=np.concatenate([z[2] for z in prior])
        weight=np.concatenate([np.full(len(z[2]),1/len(z[2])) for z in prior])
        fitted=DecisionTreeClassifier(criterion="log_loss",max_depth=int(depth),
            min_samples_leaf=int(leaf),random_state=20261024).fit(X,label,sample_weight=weight)
        threshold=float(cut)
    baseline_out=[];tree_out=[];changed=[]
    for basketid,(idx,orig) in enumerate(selections):
        yy=v["fwd"][idx]
        initial=metric_for_order(orig,yy)
        alt=orig
        if fitted is not None:
            candidates=list(orig[1:3])
            features=np.array([pair_features(v,idx,orig,c) for c in candidates])
            pp=fitted.predict_proba(features)[:,list(fitted.classes_).index(1)]
            best_ind=int(np.argmax(pp))
            if pp[best_ind]>threshold:
                c=int(candidates[best_ind]);alt=np.r_[c,orig[orig!=c]]
        after=metric_for_order(alt,yy)
        baseline_out.append(initial[:6]);tree_out.append(after[:6])
        if after[6]!=initial[6]:
            changed.append(dict(basket=basketid,
              original=names[int(idx[orig[0]])],selected=names[int(idx[alt[0]])],
              realized_relative_21d=float(yy[after[6]]-yy[initial[6]])))
    results=[]
    for arm,values in (("CORRECTED",baseline_out),("NESTED_24_TOP1_GUARD",tree_out)):
        rec=dict(variant=arm,signal_date=DATE,n_baskets=500,
            **dict(zip(METRICS,np.mean(values,axis=0))))
        results.append(rec)
    pd.DataFrame(results).to_csv(out/"JUNE_FROZEN_PRELABEL.csv",index=False)
    pd.DataFrame(changed).to_csv(out/"INCUMBENT_JUNE_CHANGED_PAIRS.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       score_generated_in_old_snapshot_before_21d_labels=True,
       source_run=40016809498,original_scores_forward_21d_missing=True,
       signal_date=str(DATE.date()),entry=str(entry.date()),exit=str(exit.date()),
       n_etfs=149,canonical_baskets=500,incumbent_tree_variant=choice,
       historical_selector_latest_eligible=str(pd.Timestamp(dates[-1]).date()),
       decision_model_fit_quarter_start="2026-04-30",monthly_horizon_trading_days=21,
       new_labels_from_appended_only_149_OHLCV=True,
       source_calendar_already_past_research_date="2026-10-24",
       production_changed=False),indent=2))
    print("FROZEN_JUNE_PRELABEL_OOS_PASS",choice,flush=True)
    print(pd.DataFrame(results).to_string(index=False),flush=True)
    print("N_JUNE_CHANGES",len(changed),flush=True)
if __name__=="__main__":main()
