#!/usr/bin/env python3
"""V3 L02 Tail model-objective ablation: Ridge continuous target vs classifier.

BASE: archived refitted 45 distinct Tail fields + Ridge(alpha=30) on
mature 21/42/63D quartic ordinal tailmix. New arm: SAME 45 input fields,
SAME maturity/rows, median imputer + scaler, L2-regularized logistic event
classification of cross-sectional top decile of matured tailmix. NO
Compact, regime, fusion, execution, risk, CAGR or portfolio selection.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"experiments"/"l02_tail"))
from evaluate import read_original, score_tail_month, ALL60, UNIQUE45

MODEL_NAME="TAIL_EVENT_LOGIT45"
REFERENCE="TAIL_DEDUP45"
REF_RUN=39654585994

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--control",default="runs/v3_l02_reference")
    p.add_argument("--out",default="runs/v3_l02_event")
    a=p.parse_args()
    years=[int(y) for y in a.years.split(",")]
    assert years and set(years)<=set(range(2018,2027))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    table,baskets,valid,alias_audit=read_original(a.raw,a.baskets)
    old_scores=pd.read_csv(Path(a.control)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    refs=old_scores.loc[(old_scores.variant==REFERENCE)&
        old_scores.signal_date.dt.year.isin(years)].copy()
    assert len(refs)>500
    old_month=pd.read_csv(Path(a.control)/"PAIRED_MONTHLY.csv")
    old_month.signal_date=pd.to_datetime(old_month.signal_date,format="mixed")
    refmonth=old_month.loc[(old_month.variant==REFERENCE)&
        old_month.signal_date.dt.year.isin(years)].copy()
    scores=[refs];monthly=[refmonth];audits=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        trainmask=(table.signal_date.ge(pd.Timestamp("2012-01-01"))&
            table.signal_date.lt(cutoff)&table.exit_date_63.lt(cutoff)&
            table.y_tailmix.notna()&valid)
        testmask=table.signal_date.dt.year.eq(year)&valid
        tr=table.loc[trainmask].sort_values(["signal_date","ticker"])
        te=table.loc[testmask].sort_values(["signal_date","ticker"])
        assert tr.signal_date.nunique()>=50 and tr.exit_date_63.max()<cutoff
        assert len(te)>0
        # Target derived from fully matured *training* months only.
        threshold=tr.groupby("signal_date").y_tailmix.transform(lambda y:y.quantile(.90))
        y=(tr.y_tailmix>=threshold).astype(int)
        assert y.mean()>.05 and y.mean()<.2
        model=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
            LogisticRegression(C=.2,solver="lbfgs",class_weight="balanced",
                               max_iter=1500))
        model.fit(tr[UNIQUE45],y)
        forecast=te[["signal_date","ticker","fwd_ret_21","y_tailmix"]].copy()
        forecast["pred"]=model.predict_proba(te[UNIQUE45])[:,1]
        forecast.insert(0,"variant",MODEL_NAME)
        scores.append(forecast)
        row=[]
        for dt,g in forecast.groupby("signal_date",sort=True):
            data=score_tail_month(g,baskets)
            if data:row.append({"variant":MODEL_NAME,**data})
        monthly.append(pd.DataFrame(row))
        audits.append({"year":year,"arm":MODEL_NAME,
            "same_feature_list_as_tail_dedup45":UNIQUE45,
            "train_rows":len(tr),"test_rows":len(te),
            "last_mature_63d_label":str(tr.exit_date_63.max()),
            "train_months":int(tr.signal_date.nunique()),
            "tail_class_prevalence_train":float(y.mean()),
            "model":"median/standardize/L2-balanced-logistic(C=0.2)",
            "auc_logloss_not_used_for_trading":True})
        print("V3_L02_CLASSIFIER_FITTED",year,len(tr),len(te),float(y.mean()),flush=True)
    allscore=pd.concat(scores,ignore_index=True)
    allmonth=pd.concat(monthly,ignore_index=True)
    allscore.signal_date=pd.to_datetime(allscore.signal_date,format="mixed")
    allmonth.signal_date=pd.to_datetime(allmonth.signal_date,format="mixed")
    assert not allscore.duplicated(["variant","signal_date","ticker"]).any()
    assert not allmonth.duplicated(["variant","signal_date"]).any()
    ref=allscore[allscore.variant==REFERENCE].sort_values(
        ["signal_date","ticker"]).reset_index(drop=True)
    cand=allscore[allscore.variant==MODEL_NAME].sort_values(
        ["signal_date","ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(ref[["signal_date","ticker"]],
                                  cand[["signal_date","ticker"]])
    np.testing.assert_allclose(ref.y_tailmix,cand.y_tailmix,
        rtol=0,atol=1e-12,equal_nan=True)
    rm=allmonth[allmonth.variant==REFERENCE].sort_values("signal_date").reset_index(drop=True)
    cm=allmonth[allmonth.variant==MODEL_NAME].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(rm.signal_date,cm.signal_date)
    allscore.to_csv(out/"OOS_SCORES.csv",index=False)
    allmonth.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    values=allmonth.groupby("variant").mean(numeric_only=True).drop(columns=["year"],errors="ignore")
    values.insert(0,"months",allmonth.groupby("variant").size())
    values.to_csv(out/"RESULTS.csv")
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "layer":"L02 Tail-classification-only",
        "target":"top-10%-of-mature-y_tailmix training label",
        "reference_run":REF_RUN,"raw_source_run":39482809691,
        "frozen_features":UNIQUE45,"unchanged_sample":True,
        "comparison":"Ridge alpha30 on ordinal Tailmix vs logistic C0.2 on elite event",
        "retuned_feature_set":False,"risk_compact_fusion_alloc":False,
        "cagr":False,"calendar_explored_not_virgin":True},indent=2))
    print("V3_L02_EVENT_SKILL\n",values.to_string(),flush=True)

if __name__=="__main__":main()
