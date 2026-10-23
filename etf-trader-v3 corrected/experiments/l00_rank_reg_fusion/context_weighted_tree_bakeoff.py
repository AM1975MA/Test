#!/usr/bin/env python3
"""V3 meta reranker: unique-pair-event-weighted basket-context preserving tree architecture.

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
 "DT_CONTEXT":("binary",dict(max_depth=3,min_samples_leaf=180,criterion="log_loss")),
 "RF_CONTEXT":("binary",dict(n_estimators=120,max_depth=6,min_samples_leaf=90,max_features=.8,n_jobs=2)),
 "XGB_CONTEXT":("binary",dict(n_estimators=160,max_depth=3,min_child_weight=40,
                        learning_rate=.05,reg_lambda=20,subsample=.85,
                        colsample_bytree=.85,tree_method="hist",n_jobs=2)),
 "CAT_CONTEXT":("binary",dict(iterations=160,depth=4,learning_rate=.04,l2_leaf_reg=15,
                        loss_function="Logloss",verbose=False,thread_count=2,
                        random_seed=20261024,allow_writing_files=False))
}
def model_factory(name):
    task,kw=MODEL_CONFIGS[name]
    core=name.split("_CONTEXT")[0]
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

def training_by_month(months):
    """Keep every unique *context*, but weight each repeated ETF pair once.

    The base 14 features include basket-local ranker dispersion. Original meta
    learning dropped all but the first overlapping basket context for each
    ticker pair. This loses information and makes conditional features
    arbitrary. Instead retain all contexts with 1/k weights for k duplicate
    occurrences of the same ordered ETF pair within one month, and finally
    normalize weights to equal total mass per month.
    """
    from collections import Counter
    result=[]
    for date,v,baskets in months:
        xx=[]; yy=[]; dd=[]; pair=[]
        for idx,orig in baskets:
            aa=int(idx[orig[0]])
            for alt in orig[1:3]:
                bb=int(idx[alt])
                diff=float(v["fwd"][bb]-v["fwd"][aa])
                xx.append(pair_features(v,idx,orig,alt))
                yy.append(int(diff>0))
                dd.append(np.clip(diff,-.20,.20))
                pair.append((aa,bb))
        counts=Counter(pair)
        w=np.asarray([1/counts[key] for key in pair],dtype=float)
        w/=w.sum()
        assert len(xx)==1000 and len(counts)>100
        assert abs(w.sum()-1)<1e-12
        # Pair de-overlap exactness: every underlying pair has equal
        # cumulative model fitting weight, regardless of basket multiplicity.
        total={}
        for key,wi in zip(pair,w):
            total[key]=total.get(key,0.)+wi
        np.testing.assert_allclose(list(total.values()),
           np.full(len(total),1/len(total)),atol=1e-12,rtol=0)
        result.append((date,np.asarray(xx,float),np.asarray(yy,np.int8),
                       np.asarray(dd,float),w,len(counts)))
    return result

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
    assert x.shape==(1000,14) and metrics.shape==(500,3,6)
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
            eligible=[(d,X,y,z,w,nunique) for d,X,y,z,w,nunique in train if d<dt-pd.Timedelta(days=60)]
            if len(eligible)>=24:
                X=np.concatenate([r[1] for r in eligible])
                binary=np.concatenate([r[2] for r in eligible])
                difference=np.concatenate([r[3] for r in eligible])
                ww=np.concatenate([r[4] for r in eligible])
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
                   history_months=len(eligible),distinct_pair_months=int(sum(r[5] for r in eligible)),
                   input_basket_context_records=len(X),
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
      feature_engineering="14_original_context_features_with_inverse_pair_frequency_sample_weight",
      frozen_first_stage_run=40016809498,original_tree_run=40031144599,
      original_nested_selector_run=40032282233,original_economic_run=40032693599,
      n_months=101,n_etfs=149,n_baskets=500,basket_members=24,
      pair_deduplicated_by_calendar_month=False,
      overlap_correction="inverse ordered pair multiplicity within each calendar month",
      sample_weight_equal_calendar_month=True,quarterly_refit=True,
      maturity_embargo_calendar_days=60,
      first_stage_retraining=False,all_predictors_as_of_date=True,
      historical_reuse=True,virgin_holdout=False,production_modified=False,
      use_future_returns_only_for_labels=True,chronological_tuning=False,
      selected_cagr_for_tuning=False),indent=2))
    print("ENSEMBLE_BAKEOFF_SUCCESS",a.family,flush=True)
    print(summ.to_string(),flush=True)
if __name__=="__main__":main()
