#!/usr/bin/env python3
"""V3 L02: freeze strong Tail-event expert, test a separate downside veto head.

Original upper-tail probabilities are frozen OOS predictions from
successful run 39655513813. New single variable: a protective
bottom-decile 21D loss logistic head trained strictly on matured labels
with the same 45 features and year folds; adjusted rank:
  logit(p_upper) - 0.5 * logit(p_worst_21).
The penalty weight 0.5 is fixed before testing; not tuned on evaluation.
This is TAIL ERROR REDUCTION, not allocation, portfolio, stops or CAGR.
"""
from __future__ import annotations
import argparse,sys,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
HERE=Path(__file__).resolve().parent;V3=HERE.parents[1]
sys.path.insert(0,str(V3/"experiments"/"l02_tail"))
from evaluate import read_original,score_tail_month,UNIQUE45

ARM="TAIL_EVENT_DOWNSIDE_GUARD45"
BASE="TAIL_EVENT_LOGIT45"
SOURCE_RUN=39655513813
def logit(p):
    x=np.asarray(p,dtype=float)
    assert np.isfinite(x).all() and np.all((x>=0)&(x<=1))
    x=np.clip(x,1e-5,1-1e-5)
    return np.log(x/(1-x))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--baseline",default="runs/v3_l02_classifier_oracle")
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--out",default="runs/v3_l02_guard")
    args=p.parse_args()
    years=[int(y) for y in args.years.split(",")]
    assert years and set(years)<=set(range(2018,2027))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    tail,baskets,valid,alias=read_original(args.raw,args.baskets)
    old=pd.read_csv(Path(args.baseline)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    old=old[(old.variant==BASE)&old.signal_date.dt.year.isin(years)].copy()
    om=pd.read_csv(Path(args.baseline)/"PAIRED_MONTHLY.csv")
    om.signal_date=pd.to_datetime(om.signal_date,format="mixed")
    om=om[(om.variant==BASE)&om.signal_date.dt.year.isin(years)].copy()
    assert len(old)>500 and len(om)>0
    scores=[old];monthly=[om];audit=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        trmask=tail.signal_date.ge(pd.Timestamp("2012-01-01"))&(
            tail.signal_date.lt(cutoff)&tail.exit_date_63.lt(cutoff)&
            tail.y_tailmix.notna()&valid)
        temask=tail.signal_date.dt.year.eq(year)&valid
        train=tail.loc[trmask].sort_values(["signal_date","ticker"])
        test=tail.loc[temask].sort_values(["signal_date","ticker"])
        assert train.signal_date.nunique()>=50 and train.exit_date_63.max()<cutoff
        # Loss labels are mature before train cutoff because 63D tailmix is mature.
        cutloss=train.groupby("signal_date").fwd_ret_21.transform(lambda x:x.quantile(.10))
        loss=(train.fwd_ret_21<=cutloss).astype(int)
        assert loss.mean()>.05 and loss.mean()<.2
        clf=make_pipeline(SimpleImputer(strategy="median"),
            StandardScaler(),LogisticRegression(C=.2,solver="lbfgs",
            class_weight="balanced",max_iter=1500))
        clf.fit(train[UNIQUE45],loss)
        pred=test[["signal_date","ticker","y_tailmix","fwd_ret_21"]].copy()
        pred=pred.merge(old.loc[old.signal_date.dt.year==year,
                        ["signal_date","ticker","pred"]].rename(columns={"pred":"p_up"}),
                        on=["signal_date","ticker"],how="left",validate="one_to_one")
        assert pred.p_up.notna().all() and len(pred)==len(test)
        p_down=clf.predict_proba(test[UNIQUE45])[:,1]
        pred["pred"]=logit(pred.p_up)-.5*logit(p_down)
        pred=pred.drop(columns=["p_up"])
        pred.insert(0,"variant",ARM)
        scores.append(pred)
        observations=[]
        for _,group in pred.groupby("signal_date",sort=True):
            r=score_tail_month(group,baskets)
            if r:observations.append({"variant":ARM,**r})
        monthly.append(pd.DataFrame(observations))
        audit.append({"year":year,"new_loss_head":"bottom-decile observed 21D forward return",
            "loss_event_prevalence":float(loss.mean()),"n_train":len(train),
            "n_test":len(test),"label_exit_mature":str(train.exit_date_63.max()),
            "same_45_features":UNIQUE45,
            "score":"logit(frozen mature upper-tail event score)-0.5*logit(mature loss classifier)",
            "source_base_run":SOURCE_RUN,"tail_up_head_not_refitted":True})
        print("TAIL_GUARD_DONE",year,len(train),len(test),flush=True)
    sc=pd.concat(scores,ignore_index=True)
    mo=pd.concat(monthly,ignore_index=True)
    sc.signal_date=pd.to_datetime(sc.signal_date,format="mixed")
    mo.signal_date=pd.to_datetime(mo.signal_date,format="mixed")
    assert not sc.duplicated(["variant","signal_date","ticker"]).any()
    assert not mo.duplicated(["variant","signal_date"]).any()
    x=sc[sc.variant==BASE].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    y=sc[sc.variant==ARM].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(x[["signal_date","ticker"]],y[["signal_date","ticker"]])
    np.testing.assert_allclose(x.y_tailmix,y.y_tailmix,equal_nan=True,atol=1e-12,rtol=0)
    x=mo[mo.variant==BASE].sort_values("signal_date").reset_index(drop=True)
    y=mo[mo.variant==ARM].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(x.signal_date,y.signal_date)
    sc.to_csv(out/"OOS_SCORES.csv",index=False)
    mo.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    summary=mo.groupby("variant").mean(numeric_only=True).drop(columns=["year"],errors="ignore")
    summary.insert(0,"months",mo.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    (out/"FIT_AUDIT.json").write_text(json.dumps(audit,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "layer":"L02 Tail negative-tail false selection guardrail",
        "intervention":"only additional separately trained bottom-decile loss head",
        "fixed_combination":"logit(upper) - 0.5*logit(bottom)",
        "upper_expert_frozen_from_run":SOURCE_RUN,
        "corrected_feature_columns":45,"base_source_run":39482809691,
        "conditional_labels_63_mature":True,
        "blended_score_allocation_risk_and_cagr":False,
        "historically_explored_dates":True},indent=2))
    print("TAIL_GUARD_METRICS\n",summary.to_string(),flush=True)

if __name__=="__main__":main()
