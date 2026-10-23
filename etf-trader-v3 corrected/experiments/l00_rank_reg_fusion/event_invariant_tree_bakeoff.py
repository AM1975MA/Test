#!/usr/bin/env python3
"""V3 meta reranker: novel basket-invariant 23-feature event-level tree architecture.

No first-stage retraining, no policy tuning on future months. Models refit on
unique observed ETF *pairs*, not overlapping basket rows; each month equally
weighted. A 60-calendar-day label maturity embargo before quarterly fits.
Only original ranker Top3 positions may be permuted; the ranking coverage
must never change. This is exploratory previously-researched history.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier,ExtraTreesClassifier,HistGradientBoostingClassifier
from xgboost import XGBClassifier,XGBRegressor
from parallel_meta import load,pair_features,METRICS
from aggregate import metric_for_order

PROB_THRESHOLDS=(.52,.55,.58,.60,.65)
RETURN_THRESHOLDS=(.000,.005,.010,.020)
MODEL_CONFIGS={
 "DT_EVENT":("binary",dict(max_depth=3,min_samples_leaf=100,criterion="log_loss")),
 "RF_EVENT":("binary",dict(n_estimators=120,max_depth=6,min_samples_leaf=50,max_features=.8,n_jobs=2)),
 "XGB_EVENT":("binary",dict(n_estimators=180,max_depth=3,min_child_weight=40,
                        learning_rate=.05,reg_lambda=20,subsample=.85,
                        colsample_bytree=.85,tree_method="hist",n_jobs=2)),
 "CAT_EVENT":("binary",dict(iterations=180,depth=4,learning_rate=.04,l2_leaf_reg=15,
                        loss_function="Logloss",verbose=False,thread_count=2,
                        random_seed=20261024,allow_writing_files=False))
}
def model_factory(name):
    task,kw=MODEL_CONFIGS[name]
    core=name.split("_EVENT")[0]
    if core=="DT":return DecisionTreeClassifier(random_state=20261024,**kw)
    if core=="RF":return RandomForestClassifier(random_state=20261024,**kw)
    if name=="ET":return ExtraTreesClassifier(random_state=20261024,**kw)
    if name=="HGB":return HistGradientBoostingClassifier(random_state=20261024,**kw)
    if core=="XGB":return XGBClassifier(random_state=20261024,objective="binary:logistic",eval_metric="logloss",**kw)
    if name=="LGB":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(random_state=20261024,**kw)
    if core=="CAT":
        from catboost import CatBoostClassifier
        return CatBoostClassifier(**kw)
    if name=="XGB_RET":return XGBRegressor(random_state=20261024,objective="reg:squarederror",**kw)
    if name=="LGB_RET":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(random_state=20261024,**kw)
    raise ValueError(name)

def event_features(v,idx,orig,alternative):
    """Basket-invariant pair features: same ordered ETF pair, identical signal.

    Solve a structural issue in the 14-feature original training: the baseline
    uses 24-instrument basket-local Top3 dispersion and gap, whereas it dedups
    pair training observations on ticker IDs. Here all features are **invariant
    across overlapping basket memberships** for the same ordered ETF pair.
    """
    a=int(idx[orig[0]]);b=int(idx[alternative])
    names=("REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
    rank=v["rank"]
    diff=np.array([v[k][b]-v[k][a] for k in names])
    ra=np.array([v[k][a] for k in names])
    rb=np.array([v[k][b] for k in names])
    score=[
       rank[a]-rank[b],rank[a],rank[b],
       *diff.tolist(),
       float(diff.mean()),float(np.median(diff)),float(np.std(diff)),
       float(np.min(diff)),float(np.max(diff)),
       float((diff>0).mean()),
       float((diff>.10).mean()),
       float(np.mean(ra)),float(np.std(ra)),
       float(np.mean(rb)),float(np.std(rb)),
       float(np.max(ra)-np.min(ra)),
       float(np.max(rb)-np.min(rb)),
       float(diff[0]-diff[1]),
       float(diff[0]-diff[2])
    ]
    assert len(score)==23
    return score

def training_by_month(months):
    data=[]
    for date,v,baskets in months:
        seen={}
        for idx,orig in baskets:
            base=int(idx[orig[0]])
            for alt in orig[1:3]:
                i=int(idx[alt]);key=(base,i)
                if key not in seen:
                    delta=float(v["fwd"][i]-v["fwd"][base])
                    seen[key]=(event_features(v,idx,orig,alt),int(delta>0),np.clip(delta,-.20,.20))
        x=np.asarray([z[0] for z in seen.values()],dtype=float)
        y=np.asarray([z[1] for z in seen.values()],dtype=np.int8)
        dif=np.asarray([z[2] for z in seen.values()],dtype=float)
        assert len(x)>=50 and np.isfinite(x).all()
        data.append((date,x,y,dif))
    return data

def inference_month(v,baskets):
    # Ensure identical feature specification to original meta-tree, including
    # the 24-name basket local ranker dispersion.
    features=[]; eval_choices=[]; bidx=[]
    for idx,orig in baskets:
        features.extend([pair_features(v,idx,orig,a) for a in orig[1:3]])
        bidx.append((idx,orig))
        yy=v["fwd"][idx]
        base=metric_for_order(orig,yy)[:6]
        alts=[]
        for alt in orig[1:3]:
            replace=np.concatenate(([alt],orig[orig!=alt]))
            alts.append(metric_for_order(replace,yy)[:6])
        eval_choices.append((base,*alts))
    x=np.asarray(features,dtype=float)
    metrics=np.asarray(eval_choices,dtype=float)
    assert x.shape==(1000,23) and metrics.shape==(500,3,6)
    return x,metrics

def month_rows(dt,variant,pred,score_baskets,threshold,task):
    p=pred.reshape(500,2)
    best=np.argmax(p,axis=1)
    strength=np.max(p,axis=1)
    take=(strength>threshold)
    which=np.where(take,best+1,0)
    met=score_baskets[np.arange(500),which,:]
    assert np.isfinite(met).all()
    out=dict(signal_date=dt,variant=variant,year=dt.year,n_baskets=500)
    out.update({metric:float(met[:,j].mean()) for j,metric in enumerate(METRICS)})
    changed=int(take.sum())
    b=score_baskets[:,0,4]
    picked=score_baskets[np.arange(500),which,4]
    diff=picked-b
    # Difference in basket_selected_excess == realized return of selected
    # ETF relative to original baseline, since basket mean is unchanged.
    return out,dict(variant=variant,signal_date=dt,changed=changed,
        changes_better=int((diff>0).sum()),changes_worse=int((diff<0).sum()),
        n_baskets=500),dict(variant=variant,signal_date=dt,
        mean_prob_or_return=float(strength.mean()),n_changed=changed,
        event_gain_mean=float(diff.mean()))

def calendar_bootstrap(monthly,reference,n=2500):
    base=reference[reference.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    assert len(base)==101
    out=[];rng=np.random.default_rng(20261024);m=len(base)
    index=((rng.integers(0,m,size=(n,(m+5)//6))[:,:,None]
            +np.arange(6))%m).reshape(n,-1)[:,:m]
    for arm in sorted(set(monthly.variant)-{"CORRECTED"}):
        r=monthly[monthly.variant==arm].sort_values("signal_date").reset_index(drop=True)
        assert r.signal_date.equals(base.signal_date)
        for metric in METRICS[:5]:
            diff=(r[metric]-base[metric]).to_numpy(float)
            boots=diff[index].mean(axis=1)
            out.append(dict(variant=arm,metric=metric,delta=float(diff.mean()),
              ci025=float(np.quantile(boots,.025)),ci975=float(np.quantile(boots,.975)),
              calendar_months=101,block_months=6,reps=n))
    return pd.DataFrame(out)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=tuple(MODEL_CONFIGS),required=True)
    p.add_argument("--shards",required=True)
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    task=MODEL_CONFIGS[a.family][0]
    dates,reference=load(a.shards,a.baskets)
    train=training_by_month(dates)
    score={};audits=[]; corrections=[];uncertainty_proxy=[]
    arms=[f"META_{a.family}_P{t:g}" for t in (RETURN_THRESHOLDS if task=="return" else PROB_THRESHOLDS)]
    months=[]
    current_quarter=None
    model=None
    for i,(dt,v,baskets) in enumerate(dates):
        quarter=(dt.year,(dt.month-1)//3)
        if quarter!=current_quarter:
            eligible=[(d,X,y,z) for d,X,y,z in train if d<dt-pd.Timedelta(days=60)]
            if len(eligible)>=24:
                X=np.concatenate([r[1] for r in eligible])
                binary=np.concatenate([r[2] for r in eligible])
                difference=np.concatenate([r[3] for r in eligible])
                ww=np.concatenate([np.full(len(r[2]),1/len(r[2])) for r in eligible])
                # XGBoost min_child_weight in sample equivalents needs class
                # hist Hessian not normalized to total 24; preserve equal
                # weight per month and rescale globally to avg weight 1.
                ww=ww*(len(ww)/len(eligible))
                model=model_factory(a.family)
                target=binary if task=="binary" else difference
                model.fit(X,target,sample_weight=ww)
                audits.append(dict(quarter=str(dt.date()),family=a.family,
                   training_from=str(eligible[0][0].date()),
                   training_to=str(eligible[-1][0].date()),
                   earliest_evaluation_date=str(dt.date()),
                   history_months=len(eligible),distinct_pair_months=len(X),
                   positivity=float(np.average(binary,weights=ww)),
                   target_kind=task,features=X.shape[1],
                   maturity_embargo_minimum_days=60))
            else:model=None
            current_quarter=quarter
        bx,eval_scores=inference_month(v,baskets)
        base=eval_scores[:,0,:]
        rows=dict(signal_date=dt,variant="CORRECTED",year=dt.year,n_baskets=500)
        rows.update({metric:float(base[:,k].mean()) for k,metric in enumerate(METRICS)})
        months.append(rows)
        if model is not None:
            if task=="binary":
                out=model.predict_proba(bx)
                if out.shape[1]!=2:raise RuntimeError("Binary class model trained on one class")
                prob=out[:,1]
            else:prob=model.predict(bx)
            assert prob.shape==(1000,) and np.isfinite(prob).all()
        else:
            prob=np.full(1000,-np.inf)
        for t,arm in zip((RETURN_THRESHOLDS if task=="return" else PROB_THRESHOLDS),arms):
            r,c,u=month_rows(dt,arm,prob,eval_scores,t,task)
            months.append(r);corrections.append(c);uncertainty_proxy.append(u)
        print("EVAL",a.family,dt.date(),"months_fitted",len(audits),"mean_predictions",
              float(np.mean(prob[np.isfinite(prob)])) if np.isfinite(prob).any() else None,flush=True)
    m=pd.DataFrame(months);c=pd.DataFrame(corrections)
    assert len(m)==101*(len(arms)+1) and m.signal_date.nunique()==101
    assert m.groupby("variant").size().eq(101).all()
    baseline=m[m.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    ctrl=reference[reference.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    assert baseline.signal_date.equals(ctrl.signal_date)
    np.testing.assert_allclose(baseline[list(METRICS[:5])],ctrl[list(METRICS[:5])],
        rtol=0,atol=1e-12,err_msg="EXACT oracle baseline reproduction failed")
    for variant in arms:
        q=m[m.variant==variant].sort_values("signal_date")
        np.testing.assert_allclose(q.basket_top3,ctrl.basket_top3,atol=1e-12,rtol=0,
           err_msg="New algorithm illegally changed Top3 membership")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    summ=m.groupby("variant")[list(METRICS)].mean()
    summ.insert(0,"months",m.groupby("variant").size())
    stats=c.groupby("variant")[["changed","changes_better","changes_worse","n_baskets"]].sum()
    summ=summ.join(stats)
    summ["intervention_rate"]=summ.changed/summ.n_baskets
    summ["intervention_precision"]=summ.changes_better/(summ.changes_better+summ.changes_worse)
    summ.to_csv(out/"SUMMARY.csv")
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    c.to_csv(out/"CORRECTIONS.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"FITTING_AUDIT.csv",index=False)
    pd.DataFrame(uncertainty_proxy).to_csv(out/"CONFIDENCE_TIMELINE.csv",index=False)
    m.groupby(["variant","year"])[list(METRICS)].mean().to_csv(out/"YEARLY.csv")
    calendar_bootstrap(m,reference).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
      family=a.family,task=task,algorithm_config=MODEL_CONFIGS[a.family][1],
      feature_engineering="basket_invariant_regressor_consensus_of_five_OOS_models_23_features",
      frozen_first_stage_run=40016809498,original_tree_run=40031144599,
      original_nested_selector_run=40032282233,original_economic_run=40032693599,
      n_months=101,n_etfs=149,n_baskets=500,basket_members=24,
      pair_deduplicated_by_calendar_month=True,
      sample_weight_equal_calendar_month=True,quarterly_refit=True,
      maturity_embargo_calendar_days=60,
      first_stage_retraining=False,all_predictors_as_of_date=True,
      historical_reuse=True,virgin_holdout=False,production_modified=False,
      use_future_returns_only_for_labels=True,chronological_tuning=False,
      selected_cagr_for_tuning=False),indent=2))
    print("ENSEMBLE_BAKEOFF_SUCCESS",a.family,flush=True)
    print(summ.to_string(),flush=True)
if __name__=="__main__":main()
