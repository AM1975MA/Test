#!/usr/bin/env python3
"""V3 L02: preserve trained elite classifier, add independently fitted bad-selection head.

Control = exact OOS 'TAIL_EVENT_LOGIT45' from successful 39655513813.
New arm = same head (NOT retrained), minus fixed 0.25 * within-month percentile
of a bad-outcome classifier (Ridge schema unchanged: 45 frozen Tail fields).
This is only a second functional task: avoiding the bottom 10% at 21D while
preserving top-tail event capture. Penalization coefficient 0.25 is predeclared,
not chosen on OOS outcomes. No CAGR, L01 ranker, Macro or risk allocation.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"experiments"/"l02_tail"))
from evaluate import read_original,score_tail_month,UNIQUE45

REF="TAIL_EVENT_LOGIT45"
ARM="TAIL_ELITE_BAD25"
WEIGHT=0.25

def risk_month(x):
    x=x.dropna(subset=["p_bad","target_rank_21"])
    if len(x)<30:return None
    bad=x.target_rank_21.le(.10).to_numpy(dtype=int)
    p=x.p_bad.to_numpy(float)
    if bad.min()==bad.max():return None
    return {"signal_date":pd.Timestamp(x.signal_date.iloc[0]),
       "bottom_event_ap":float(average_precision_score(bad,p)),
       "bottom_event_auc":float(roc_auc_score(bad,p)),
       "bottom_event_brier":float(brier_score_loss(bad,p)),
       "bottom_event_rate":float(bad.mean())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--reference",default="runs/v3_l02_elite_reference")
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--out",default="runs/v3_l02_bad")
    args=p.parse_args()
    years=[int(y) for y in args.years.split(",")]
    assert len(years)==len(set(years)) and set(years)<=set(range(2018,2027))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    table,baskets,valid,duplicates=read_original(args.raw,args.baskets)
    ref=pd.read_csv(Path(args.reference)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    ref=ref[(ref.variant==REF)&(ref.signal_date.dt.year.isin(years))].copy()
    assert len(ref)>500 and not ref.duplicated(["signal_date","ticker"]).any()
    controls=[];challengers=[];riskstats=[];audits=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        train=(table.signal_date.ge(pd.Timestamp("2012-01-01"))&
               table.signal_date.lt(cutoff)&
               table.exit_date_63.lt(cutoff)&
               table.y_tailmix.notna()&
               table.target_rank_21.notna()&
               valid)
        test=(table.signal_date.dt.year.eq(year)&valid)
        tr=table.loc[train].sort_values(["signal_date","ticker"])
        te=table.loc[test].sort_values(["signal_date","ticker"])
        assert tr.signal_date.nunique()>=50 and len(te)>0
        assert tr.exit_date_63.max()<cutoff
        # Bottom 10% of all ETFs observed at the same historical signal month.
        # Labels for the train period are fully matured before 1 January.
        bad=tr.target_rank_21.le(.10).astype(int)
        assert .06<float(bad.mean())<.13
        model=make_pipeline(SimpleImputer(strategy="median"),
            StandardScaler(),LogisticRegression(C=.2,solver="lbfgs",
            class_weight=None,max_iter=1500))
        model.fit(tr[UNIQUE45],bad)
        new=te[["signal_date","ticker","y_tailmix","fwd_ret_21",
                "target_rank_21"]].copy()
        new["p_bad"]=model.predict_proba(te[UNIQUE45])[:,1]
        old=ref.loc[ref.signal_date.dt.year.eq(year),
                    ["signal_date","ticker","pred","y_tailmix","fwd_ret_21"]].copy()
        old=old.rename(columns={"pred":"p_elite",
           "y_tailmix":"reference_y_tailmix","fwd_ret_21":"reference_ret_21"})
        new=new.merge(old,on=["signal_date","ticker"],how="left",
                      validate="one_to_one",sort=False)
        assert new.p_elite.notna().all()
        np.testing.assert_allclose(new.y_tailmix,new.reference_y_tailmix,
            rtol=0,atol=1e-12,equal_nan=True)
        np.testing.assert_allclose(new.fwd_ret_21,new.reference_ret_21,
            rtol=0,atol=1e-14,equal_nan=True)
        assert len(new)==len(old)
        new["elite_rank"]=new.groupby("signal_date").p_elite.rank(pct=True,method="average")
        new["risk_rank"]=new.groupby("signal_date").p_bad.rank(pct=True,method="average")
        new["combined"]=new.elite_rank-WEIGHT*new.risk_rank

        base=new[["signal_date","ticker","y_tailmix","fwd_ret_21","p_elite"]].rename(
            columns={"p_elite":"pred"}).copy()
        base.insert(0,"variant",REF)
        alternative=new[["signal_date","ticker","y_tailmix","fwd_ret_21","combined"]].rename(
            columns={"combined":"pred"}).copy()
        alternative.insert(0,"variant",ARM)
        controls.append(base);challengers.append(alternative)
        for dt,group in new.groupby("signal_date",sort=True):
            risk=risk_month(group)
            if risk:riskstats.append(risk)
        audits.append({"year":year,"arm":ARM,"fit_rows":len(tr),"test_rows":len(te),
            "mature_63D_exit_date":str(tr.exit_date_63.max()),
            "class_prevalence":float(bad.mean()),"n_features":len(UNIQUE45),
            "risk_model":"median+standard scaler+logistic(C=0.2, no balancing)",
            "elite_head":"frozen OOS scores from run 39655513813",
            "penalty_on_same_month_percentile_rank":WEIGHT})
        print("L02_BAD_HEAD_FIT",year,len(tr),len(te),flush=True)

    frames=pd.concat(controls+challengers,ignore_index=True)
    frames["signal_date"]=pd.to_datetime(frames.signal_date)
    assert not frames.duplicated(["variant","signal_date","ticker"]).any()
    report=[]
    for arm,one in frames.groupby("variant"):
        for dt,g in one.groupby("signal_date",sort=True):
            result=score_tail_month(g,baskets)
            if result:report.append({"variant":arm,**result})
    result=pd.DataFrame(report)
    result.signal_date=pd.to_datetime(result.signal_date)
    assert not result.duplicated(["variant","signal_date"]).any()
    a=result[result.variant==REF].sort_values("signal_date").reset_index(drop=True)
    b=result[result.variant==ARM].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(a.signal_date,b.signal_date)
    assert len(a)>=25
    # Preserve exact original elite-classifier skill when no penalty is applied.
    prev=pd.read_csv(Path(args.reference)/"PAIRED_MONTHLY.csv")
    prev.signal_date=pd.to_datetime(prev.signal_date,format="mixed")
    oldmonth=prev[(prev.variant==REF)&(prev.signal_date.dt.year.isin(years))]
    oldmonth=oldmonth.sort_values("signal_date").reset_index(drop=True)
    for field in ["signal_date","tail_event_ap","tail_elite_recall_top15",
                  "basket_tail_top3","basket_bottom_decile_false_selection"]:
        if field=="signal_date":pd.testing.assert_series_equal(a[field],oldmonth[field])
        else:np.testing.assert_allclose(a[field],oldmonth[field],
                     atol=1e-12,rtol=0,equal_nan=True)
    frames.to_csv(out/"OOS_SCORES.csv",index=False)
    result.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    pd.DataFrame(riskstats).drop_duplicates("signal_date").to_csv(out/"BAD_HEAD_CALIBRATION.csv",index=False)
    m=result.groupby("variant").mean(numeric_only=True).drop(columns=["year"],errors="ignore")
    m.insert(0,"months",result.groupby("variant").size())
    m.to_csv(out/"RESULTS.csv")
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
      "layer":"L02 Tail, additive false-selection head ONLY",
      "elite_head":"frozen logistic head with exact same scores as successful run 39655513813",
      "risk_target":"bottom decile of fully matured 21-day ETF return rank",
      "risk_head_maturity":"63-day label maturity, same as unchanged elite control",
      "risk_model":"Logistic C=.2, no class weight, 45 inputs",
      "penalty":"rank(elite_score) - 0.25 * rank(bottom_risk_score)",
      "sample":"same 149 ticker/months and controls",
      "cagr":False,"all_other_layers_frozen":True,
      "holdout":"explored historical dates; exploratory"} ,indent=2))
    print("L02_BAD_HEAD_RESULTS\n",m.to_string(),flush=True)

if __name__=="__main__":main()
