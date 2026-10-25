#!/usr/bin/env python3
"""Apples-to-apples actual native V3 127-leaf ranker, same as-of 101 months.

2 markets x 9 annual training vintages; 125 real corrected native V3 features,
2012+ strictly matured labels, 3 original seeds and 360 boosting rounds.
DO NOT optimize model or choose hyperparameters on these results.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker
from etf_trader_v3.source_only import kernel as K

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--market",choices=["US149","EU148"],required=True)
    p.add_argument("--year",type=int,required=True)
    p.add_argument("--panel",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    assert 2018<=a.year<=2026
    z=pd.read_parquet(Path(a.panel)/a.market/"CORRECTED125_PANEL.parquet")
    z["signal_date"]=pd.to_datetime(z.signal_date)
    z["exit_date_21"]=pd.to_datetime(z.exit_date_21)
    assert z.ticker.nunique()==(149 if a.market=="US149" else 148)
    first=pd.Timestamp(f"{a.year}-01-01")
    tr=z[z.signal_date.lt(first)&z.signal_date.ge("2012-01-01")&
         z.exit_date_21.lt(first)&z.fwd_ret_21.notna()].copy()
    te=z[z.signal_date.dt.year.eq(a.year)&z.signal_date.between("2018-01-01","2026-05-31")].copy()
    tr=tr.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    te=te.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert len(tr)>1000 and len(te)>60
    assert tr.exit_date_21.max()<first
    assert te.signal_date.nunique()==(5 if a.year==2026 else 12)
    assert te.groupby("signal_date").ticker.nunique().ge(25).all()
    assert len(K.F2D_FEATURES)==125
    # Identical ranker target transformation in original paired V3 model.
    pct=tr.groupby("signal_date").fwd_ret_21.rank(method="average",pct=True)
    yrank=np.rint(100*pct.to_numpy(float)).astype(int)
    group=tr.groupby("signal_date",sort=True).size().to_numpy(int)
    assert group.sum()==len(tr)
    kw=dict(K.COMPACT_PARAMS)
    kw.update(max_depth=0,grow_policy="lossguide",max_leaves=127)
    X=tr[list(K.F2D_FEATURES)].replace([np.inf,-np.inf],np.nan)
    Xt=te[list(K.F2D_FEATURES)].replace([np.inf,-np.inf],np.nan)
    vals=[]
    for seed in (101,202,303):
        m=XGBRanker(**kw,random_state=seed)
        m.fit(X,yrank,group=group,verbose=False)
        yp=m.predict(Xt)
        assert len(yp)==len(te) and np.isfinite(yp).all()
        vals.append(yp)
        print("PAIRED_MODEL_SEED_DONE",a.market,a.year,seed,flush=True)
    te=te[["signal_date","ticker","fwd_ret_21","entry_date","exit_date_21"]].copy()
    te["pred"]=np.mean(vals,axis=0)
    te["market"]=a.market;te["variant"]="V3_LEAF127"
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    te.to_csv(out/"PAIRED_127_PREDICTIONS.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(dict(
       market=a.market,year=a.year,variant="V3_LEAF127",
       feature_kernel="etf_trader_v3.source_only.kernel",
       features=125,max_leaves=127,n_train=len(tr),n_test=len(te),
       train_months=len(group),test_months=te.signal_date.nunique(),
       asof_2012plus=True,mature_label_cutoff=str(first.date()),
       last_train_exit=str(tr.exit_date_21.max().date()),
       exclude_future_labels_from_test=False,
       random_seeds=[101,202,303],ranker_kw=kw
    ),indent=2,default=str))
    print("PAIRED_V3_127_YEAR_PASS",a.market,a.year,len(te),te.signal_date.nunique(),flush=True)
if __name__=="__main__":main()
