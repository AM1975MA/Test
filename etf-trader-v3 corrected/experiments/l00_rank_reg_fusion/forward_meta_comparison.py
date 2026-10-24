#!/usr/bin/env python3
"""Three first-stage-frozen new matured months: original selector and locked challengers.

June 2026 OOS raw scores were ALREADY archived unlabeled on original run.
July and August are new retrospective signal extensions with exact January–
June first-stage raw-score parity before use. 60-day maturity embargo, quarter
refits and asof choice rules are reproduced from immutable source only.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from collections import defaultdict
import numpy as np,pandas as pd
from sklearn.tree import DecisionTreeClassifier
from parallel_meta import load,prepare_tree_months,pair_features,METRICS,REGS
from aggregate import metric_for_order
import hurdle_expected_regret as H

MONTHS=[pd.Timestamp("2026-06-30"),pd.Timestamp("2026-07-31"),pd.Timestamp("2026-08-31")]
ARMS=("CORRECTED","NESTED_24_TOP1_GUARD","UTILITY_DT14_L1.5",
      "UTILITY_RF_REGIME_L1","UTILITY_HGB_REGIME_L1.5")
UT={"UTILITY_DT14_L1.5":("DT14",1.5),
    "UTILITY_RF_REGIME_L1":("RF_REGIME",1.0),
    "UTILITY_HGB_REGIME_L1.5":("HGB_REGIME",1.5)}
NAMEPAT=re.compile(r"^TREE_(expanding|last36)_D([123])_N(100|300)_P(0\.(?:55|6|65))$")
def newmonths(path,baskets_path):
    score=pd.read_csv(path,parse_dates=["signal_date"])
    assert set(score.variant)==set(("CORRECTED",)+REGS)
    assert sorted(score.signal_date.unique())==MONTHS
    assert len(score)==len(MONTHS)*149*6
    membership=pd.read_csv(baskets_path)
    bm=[list(g.ticker) for _,g in membership.groupby("basket",sort=True)]
    out=[];symbols={}
    for date,group in score.groupby("signal_date",sort=True):
        wide=group.pivot(index="ticker",columns="variant",values="pred").sort_index()
        labels=group[group.variant.eq("CORRECTED")].set_index("ticker").fwd_ret_21
        wide["fwd"]=labels
        assert len(wide)==149 and np.isfinite(wide.to_numpy()).all()
        names=list(wide.index); ids={t:i for i,t in enumerate(names)}
        vals={"rank":wide.CORRECTED.rank(pct=True).to_numpy(float),
              "fwd":wide.fwd.to_numpy(float)}
        vals.update({r:wide[r].rank(pct=True).to_numpy(float) for r in REGS})
        selections=[]
        for b in bm:
            idx=np.array([ids[t] for t in b],dtype=int)
            order=np.argsort(-vals["rank"][idx],kind="stable")
            selections.append((idx,order))
        assert len(selections)==500
        symbols[pd.Timestamp(date)]=names
        out.append((pd.Timestamp(date),vals,selections))
    return out,symbols

def evaluate_tree(models,v,baskets):
    values={};changes={}
    for window in ("expanding","last36"):
        for depth in (1,2,3):
            for leaf in (100,300):
                model=models[(window,depth,leaf)]
                for cut in (.55,.60,.65):
                    arm=f"TREE_{window}_D{depth}_N{leaf}_P{cut:g}"
                    values[arm]=[];changes[arm]=[0,0,0]
    for idx,orig in baskets:
        actual=v["fwd"][idx];baseline=metric_for_order(orig,actual)
        xx=np.array([pair_features(v,idx,orig,alt) for alt in orig[1:3]],float)
        for (window,depth,leaf),model in models.items():
            p=model.predict_proba(xx)[:,list(model.classes_).index(1)]
            best=int(np.argmax(p));alt=int(orig[best+1])
            for cut in (.55,.60,.65):
                arm=f"TREE_{window}_D{depth}_N{leaf}_P{cut:g}"
                order=np.concatenate(([alt],orig[orig!=alt])) if p[best]>cut else orig
                metr=metric_for_order(order,actual)
                values[arm].append(metr[:6])
                if metr[6]!=baseline[6]:
                    changes[arm][0]+=1
                    changes[arm][1]+=int(actual[metr[6]]>actual[baseline[6]])
                    changes[arm][2]+=int(actual[metr[6]]<actual[baseline[6]])
    means={arm:dict(zip(METRICS,np.asarray(vv,float).mean(axis=0))) for arm,vv in values.items()}
    return means,changes

def train_trees(prepared,quarter_start):
    historical=[(d,x,y) for d,x,y in prepared if d<quarter_start-pd.Timedelta(days=60)]
    assert len(historical)>=24
    cache={}
    for win in ("expanding","last36"):
        h=historical if win=="expanding" else historical[-36:]
        X=np.concatenate([z[1] for z in h]);yy=np.concatenate([z[2] for z in h])
        w=np.concatenate([np.full(len(z[2]),1/len(z[2])) for z in h])
        for d in (1,2,3):
            for n in (100,300):
                model=DecisionTreeClassifier(criterion="log_loss",max_depth=d,
                    min_samples_leaf=n,random_state=20261024)
                model.fit(X,yy,sample_weight=w)
                cache[(win,d,n)]=model
    return cache

def choose_nested(old,new,dt):
    # Exact previously committed 24-month, 60-day gap, Top1 guard policy.
    d=pd.concat([old,new],ignore_index=True)
    dates=sorted(d.signal_date.unique())
    dates=[date for date in dates if date<dt-pd.Timedelta(days=60)]
    dates=dates[-24:]
    assert len(dates)==24
    hist=d[d.signal_date.isin(dates)]
    ctrl=hist[hist.variant.eq("CORRECTED")].sort_values("signal_date")
    assert len(ctrl)==24
    best="CORRECTED";value=0.
    for arm,g in hist[hist.variant.ne("CORRECTED")].groupby("variant",sort=True):
        ordered=g.sort_values("signal_date")
        assert ordered.signal_date.tolist()==dates
        dex=float((ordered.basket_selected_excess.to_numpy()-ctrl.basket_selected_excess.to_numpy()).mean())
        dh=float((ordered.basket_top1.to_numpy()-ctrl.basket_top1.to_numpy()).mean())
        if dex>value and dh>=0:
            best=arm;value=dex
    return best,value,dates[-1]

def utility_one(modelset,family,penalty,dt,v,baskets,raw_features,tickers):
    xx,xreg,metr,pairs,orig_names=H.make_metrics(v,baskets,tickers,raw_features,dt)
    X=xx if family=="DT14" else xreg
    preds=H.infer(modelset,X).reshape(500,2,3)
    u=preds[:,:,0]*preds[:,:,1]-penalty*(1-preds[:,:,0])*preds[:,:,2]-H.EXTRA_SWITCH_COST
    best=np.argmax(u,axis=1)
    opt=np.where(u[np.arange(500),best]>0,best+1,0)
    met=metr[np.arange(500),opt,:]
    names=(orig_names,pairs)
    changed=[]
    for k in np.flatnonzero(opt):
        index=int(k)*2+int(opt[k])-1
        changed.append(dict(basket=int(k),source=orig_names[k],alternative=pairs[index][1],
            realized_gain=float(met[k,4]-metr[k,0,4]),
            utility_estimate=float(u[k,opt[k]-1]),
            confidence=float(preds[k,opt[k]-1,0])))
    result=dict(zip(METRICS,met.mean(axis=0)))
    corrections=[len(changed),int(sum(vv["realized_gain"]>0 for vv in changed)),
                 int(sum(vv["realized_gain"]<0 for vv in changed))]
    return result,corrections,changed

def metrics_row(dt,arm,metrics,changes):
    return dict(signal_date=dt,year=dt.year,variant=arm,n_baskets=500,
       **{k:float(metrics[k]) for k in METRICS},
       changed=int(changes[0]),better=int(changes[1]),worse=int(changes[2]))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--old-shards",required=True)
    ap.add_argument("--original-tree",required=True)
    ap.add_argument("--original-nested",required=True)
    ap.add_argument("--original-utility",required=True)
    ap.add_argument("--first-stage",required=True)
    ap.add_argument("--extended-raw",required=True)
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    orig,original_source=load(a.old_shards,a.baskets)
    new,names_future=newmonths(a.first_stage,a.baskets)
    assert len(orig)==101 and len(new)==3
    assert orig[-1][0]==pd.Timestamp("2026-05-29")
    old_scores=pd.read_csv(Path(a.old_shards)/"regression"/"s3"/"OOS_SCORES.csv",parse_dates=["signal_date"])
    # Truly stored June predictions pre-date June forward targets.
    old_june=old_scores[old_scores.signal_date.eq(MONTHS[0])]
    assert len(old_june)==149*6 and old_june.fwd_ret_21.isna().all()
    original_tree=pd.read_csv(Path(a.original_tree)/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
    assert len(original_tree.signal_date.unique())==101
    original_choice=pd.read_csv(Path(a.original_nested)/"NESTED_SELECTION_AUDIT.csv",parse_dates=["signal_date"])
    inc=original_choice[original_choice.strategy.eq("NESTED_24_TOP1_GUARD")].sort_values("signal_date")
    assert len(inc)==101
    original_utility={}
    for family in ("DT14","RF_REGIME","HGB_REGIME"):
        d=pd.read_csv(Path(a.original_utility)/family/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
        original_utility[family]=d
    months=orig+new; prepared=prepare_tree_months(months)
    price,category,_=H.load_ticker_csv_folder(a.extended_raw)
    assert len(category)==149
    names={}
    for dt,v,basket in orig:
        names[dt]=sorted(old_scores.loc[old_scores.signal_date.eq(dt),"ticker"].unique()) if dt.year==2026 else None
    # Get missing historical ticker identities directly from canonical old
    # first-stage predictions, required by deterministic train H.
    old_all,_,_=H.read_shards(a.old_shards,"regression")
    for d in set(dt for dt,_,_ in orig):
        names[d]=sorted(old_all.loc[old_all.signal_date.eq(d),"ticker"].unique())
        assert len(names[d])==149
    names.update(names_future)
    features=H.trailing(price["Close"],[d for d,_,_ in months],names)
    hurdles=H.training(months,names,features)
    assert len(hurdles)==104
    years=[2026]
    old_compare=pd.DataFrame()
    for dt in orig[-5:]:
        date=dt[0]
        expected=inc[inc.signal_date.eq(date)].chosen.iloc[0]
        got,_,_=choose_nested(original_tree,old_compare,date)
        assert expected==got,(date,expected,got)
    print("ORIGINAL_NESTED_CHOICE_PARITY",flush=True)
    m=[];audits=[];changed_events=[]
    extra_monthly=pd.DataFrame(columns=original_tree.columns)
    cached_tree={};cached_utility={}
    for date,v,baskets in [orig[-1]]+new:
        q=(date.year,(date.month-1)//3)
        first_date=next(d for d,_,_ in months if (d.year,(d.month-1)//3)==q)
        if q not in cached_tree:
            cached_tree[q]=train_trees(prepared,first_date)
            cached_utility[q]={}
            hist=[t for t in hurdles if t[0]<first_date-pd.Timedelta(days=60)]
            assert len(hist)>=24
            for family in ("DT14","RF_REGIME","HGB_REGIME"):
                cached_utility[q][family]=H.train_hurdle(family,hist)
        tmonth,changes=evaluate_tree(cached_tree[q],v,baskets)
        control=np.asarray([metric_for_order(orig_order,v["fwd"][idx])[:6]
                 for idx,orig_order in baskets],float).mean(axis=0)
        base=dict(zip(METRICS,control))
        # Ensure old same-quarter decision trees and outcome do not change.
        if date==pd.Timestamp("2026-05-29"):
            for variant,mt in tmonth.items():
                oldrow=original_tree[(original_tree.signal_date.eq(date))&
                                  (original_tree.variant.eq(variant))]
                assert len(oldrow)==1
                np.testing.assert_allclose(list(mt.values()),
                    oldrow.iloc[0][list(METRICS)].to_numpy(float),
                    rtol=0,atol=1e-12,err_msg="MAY 2026 ORIGINAL TREE POLICY PARITY BROKEN")
            print("ORIGINAL_MAY_ALL36_META_TREE_PARITY",flush=True)
        source={}
        for arm,(family,penalty) in UT.items():
            rec,corr,events=utility_one(cached_utility[q][family],family,penalty,
                date,v,baskets,features,names)
            source[arm]=(rec,corr,events)
            if date==pd.Timestamp("2026-05-29"):
                prior=original_utility[family]
                old=prior[(prior.signal_date.eq(date))&(prior.variant.eq(arm))]
                assert len(old)==1
                np.testing.assert_allclose([rec[k] for k in METRICS],
                    old.iloc[0][list(METRICS)].to_numpy(float),
                    atol=1e-12,rtol=0,err_msg="PREEXISTING UTILITY MODEL MAY PARITY")
        if date==pd.Timestamp("2026-05-29"):
            print("ORIGINAL_MAY_UTILITY_PARITY",flush=True)
            continue
        # Candidate tree score at t is already generated, but selected solely
        # from historic metrics dated strictly earlier than t-60 calendar days.
        today=pd.DataFrame([dict(signal_date=date,variant=k,n_baskets=500,year=date.year,**v)
                   for k,v in tmonth.items()] +
                    [dict(signal_date=date,variant="CORRECTED",n_baskets=500,
                       year=date.year,**base)])
        choice,objective,last_history=choose_nested(original_tree,extra_monthly,date)
        picked=base if choice=="CORRECTED" else tmonth[choice]
        ch=(0,0,0) if choice=="CORRECTED" else changes[choice]
        m.append(metrics_row(date,"CORRECTED",base,(0,0,0)))
        m.append(metrics_row(date,"NESTED_24_TOP1_GUARD",picked,ch))
        for arm,(sc,chg,events) in source.items():
            m.append(metrics_row(date,arm,sc,chg))
            for row in events:changed_events.append(dict(variant=arm,signal_date=date,**row))
        audits.append(dict(signal_date=str(date.date()),chosen=choice,
            historic_60day_max=str(last_history.date()),
            selector_objective=float(objective),
            n_tree_candidates=len(tmonth),n_baskets=500,
            q_start=str(first_date.date()),
            trained_before=str((first_date-pd.Timedelta(days=60)).date())))
        extra_monthly=pd.concat([extra_monthly,today],ignore_index=True)
        print("NEW_FORWARD_MONTH",str(date.date()),"incumbent_choice",choice,
             "basket_base_excess",base["basket_selected_excess"],
             "incumbent_excess",picked["basket_selected_excess"],
             "challenger_DT14",source["UTILITY_DT14_L1.5"][0]["basket_selected_excess"],
             "challenger_RF",source["UTILITY_RF_REGIME_L1"][0]["basket_selected_excess"],flush=True)
    result=pd.DataFrame(m)
    assert len(result)==3*len(ARMS) and result.groupby("variant").size().eq(3).all()
    assert result.groupby("signal_date").size().eq(len(ARMS)).all()
    assert result.n_baskets.eq(500).all()
    assert np.allclose(result.basket_top3,result[result.variant.eq("CORRECTED")].set_index("signal_date").loc[result.signal_date,"basket_top3"].to_numpy(float),rtol=0,atol=1e-12)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    result.to_csv(out/"THREE_NEW_MONTHS.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"SELECTION_AUDIT.csv",index=False)
    pd.DataFrame(changed_events).to_csv(out/"CHANGED_PAIR_EVENTS.csv",index=False)
    agg=result.groupby("variant")[list(METRICS)].mean()
    agg=agg.join(result.groupby("variant")[["changed","better","worse"]].sum())
    agg["correct_rate"]=agg.better/agg.changed.replace(0,np.nan)
    agg["difference_vs_incumbent_excess_21d"]=agg.basket_selected_excess-agg.loc["NESTED_24_TOP1_GUARD","basket_selected_excess"]
    agg.to_csv(out/"THREE_MONTHS_SUMMARY.csv")
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        first_stage_parity_6_months=True,first_stage_frozen_june_pre_label=True,
        incumbent_selection_replayed_for_may_original_exact=True,
        incumbent_all_36_may_metrics_identical=True,
        prior_hurdle_may_metrics_identical=True,
        meta_months=["2026-06-30","2026-07-31","2026-08-31"],
        pure_june_original_pred_already_archived_unlabeled=True,
        first_stage_new_predictions=["2026-07-31","2026-08-31"],
        n_etfs=149,n_baskets=500,
        target_maturity=21,meta_refit_quarterly=True,
        embargo_calendar_days=60,
        research_only=True,retro_holdout_not_prospective=True,
        evaluate_three_months_not_significant=True,
        production_changed=False),indent=2))
    print("FORWARD_JUNE_AUG_2026_COMPLETE",flush=True)
    print(agg.to_string(),flush=True)
if __name__=="__main__":main()
