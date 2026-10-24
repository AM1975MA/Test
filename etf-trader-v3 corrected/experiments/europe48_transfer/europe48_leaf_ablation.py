#!/usr/bin/env python3
"""Isolate effect of 127 XGB leaves in Europe's original 48 ETF universe.

Causal yearly 2017+ full-maturity refit, same 125 features, market reference,
same 360 boosting rounds, other params and three seeds. Compare max leaves
[15,31,63,127] without tuning ANY risk/position/candidate selection layer.
LEAF 127 must reproduce the previous original 127 result exactly in both
top-ranked ETF selection and nextopen 21-session labels; fail if not.
Results are diagnostic only; date 2021-2026 already inspected repeatedly.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.compact21_base48.run import strict_build_spy
from isin_first2026.v2_usref48.original_us_references import asof_quotes
from etf_trader.source_only.kernel import add_labels
LEAVES=(15,31,63,127)
SEEDS=(101,202,303)
V2REF="isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,required=True)
    p.add_argument("--prep",required=True)
    p.add_argument("--us",required=True)
    p.add_argument("--fx",required=True)
    p.add_argument("--prior-v3",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    year=args.year
    assert 2021<=year<=2026
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,names,_=load_ticker_csv_folder(Path(args.prep)/"raw_ticker_csv")
    assert len(names)==48
    refout=out/"SPY_REF"
    asof_quotes(args.us,mats["Close"].index,args.fx,refout)
    market=pd.read_csv(refout/"STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",parse_dates=["date"])
    dates,features,_,_=strict_build_spy(mats,market)
    allframe=add_labels(features,mats["Open"],dates)
    fields=list(k.F2D_FEATURES)
    assert len(fields)==125
    good=allframe[fields].notna().sum(axis=1)>=30
    cutoff=pd.Timestamp(f"{year}-01-01")
    train=allframe[(allframe.signal_date>=pd.Timestamp("2017-01-01"))&
      (allframe.signal_date<cutoff)&(allframe.exit_date_21<cutoff)&
       allframe.target_rank_21.notna()&good].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    reference=pd.read_csv(V2REF,parse_dates=["signal_date"])
    test=allframe[allframe.signal_date.dt.year.eq(year)&
      allframe.signal_date.isin(reference.signal_date)&good].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    expected=reference[reference.signal_date.dt.year.eq(year)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert len(test)>=48 and test[["signal_date","ticker"]].equals(expected[["signal_date","ticker"]])
    np.testing.assert_allclose(test.fwd_ret_21,expected.fwd_ret_21,atol=1e-12,rtol=0)
    groups=train.groupby("signal_date").size().to_numpy(int)
    assert groups.sum()==len(train) and all(groups==48)
    X=train[fields].replace([np.inf,-np.inf],np.nan)
    Xt=test[fields].replace([np.inf,-np.inf],np.nan)
    y=np.rint(100*train.target_rank_21.to_numpy(float)).astype(int)
    cfg=dict(k.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide")
    prior=pd.read_csv(Path(args.prior_v3)/str(year)/"EU48_V3_FIRSTSTAGE_SCORES.csv",parse_dates=["signal_date"])
    old=prior[prior.variant.eq("CORRECTED")].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert old[["signal_date","ticker"]].equals(test[["signal_date","ticker"]])
    audits=[];parts=[]
    for leaf in LEAVES:
        predictions=[]
        for seed in SEEDS:
            model=XGBRanker(**dict(cfg,max_leaves=leaf),random_state=seed)
            model.fit(X,y,group=groups,verbose=False)
            predictions.append(model.predict(Xt))
        pred=np.mean(predictions,axis=0)
        if leaf==127:
            ae=np.abs(pred-old.pred.to_numpy(float))
            diff=int(sum(pd.Series(pred[test.signal_date.eq(dt)].copy()).idxmax() != pd.Series(
                  old.loc[old.signal_date.eq(dt),"pred"].to_numpy(float)).idxmax()
                  for dt in sorted(test.signal_date.unique())))
            print("LEAF127_REFERENCE_PARITY",year,"maxerr",float(ae.max()),"meanerr",float(ae.mean()),
                  "different_monthly_top1",diff,flush=True)
            assert np.allclose(pred,old.pred.to_numpy(float),rtol=1e-5,atol=2e-5)
            assert diff==0
        z=test[["signal_date","ticker","fwd_ret_21"]].copy()
        z["leaf"]=leaf
        z["pred"]=pred
        parts.append(z)
        audits.append(dict(year=year,leaf=leaf,n_train=len(train),n_train_months=train.signal_date.nunique(),
           n_test=len(test),n_test_months=test.signal_date.nunique(),seed_count=len(SEEDS),
           seed_list=str(SEEDS),last_matured_train=str(train.exit_date_21.max().date()),
           train_feature_count=len(fields),actual_boost_rounds=cfg["n_estimators"]))
        print("EU48_LEAF_ABLATION_DONE",year,leaf,len(train),len(test),flush=True)
    data=pd.concat(parts,ignore_index=True)
    assert data.groupby(["signal_date","leaf"]).ticker.nunique().eq(48).all()
    data.to_csv(out/"YEAR_OOS_ALL_LEAVES.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"TRAIN_AUDIT.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(year=year,leaf_values=LEAVES,
       immutable_125F=True,yearly_walkforward=True,training_from="2017-01-01",
       original_euro48_label_ticker_parity=True,original_v3_127_reference_parity_passed=True,
       previous_2021_2026_historical_data_reused=True,independent_holdout=False,
       production_unchanged=True),indent=2))
    print("EU48_LEAF_ABLATION_PASS",year,flush=True)
if __name__=="__main__":main()
