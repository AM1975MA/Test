#!/usr/bin/env python3
"""Precommitted EU148 actual V3 corrected rank/regression annual retraining.

Train label-matured strictly before Jan1 each year from 2012, test 2018-
May2026. Four rankers: V2-like depth4, V3 lossguide 15/31/127 (no cherry pick).
Five regression predictions per original V3 meta architecture (125/101F).
The selected ISIN cohort evolves as products actually launch. Six EUR
macro-cluster group sizes and label ranks are recomputed only on eligible
genuinely quoted ISIN at each as-of date. NO 2026 membership backfill.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker,XGBRegressor
from etf_trader_v3.source_only import kernel as K
SEEDS=(101,202,303)
ALL=list(K.F2D_FEATURES)
VOLBASE={"vol21","vol63","vol126","downvol21","downvol63","downvol126","vol_ratio_21_126","gkvol21"}
SHORT=[c for c in ALL if c.replace("_pct","").replace("_dev","") not in VOLBASE]
RANKERS=dict(V2LIKE_DEPTH4=("depth",4),V3_LEAF15=("leaf",15),V3_LEAF31=("leaf",31),V3_LEAF127=("leaf",127))
REGS=("REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,required=True)
    p.add_argument("--panel",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    assert 2018<=a.year<=2026
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert len(ALL)==125 and len(SHORT)==101,(len(ALL),len(SHORT))
    z=pd.read_parquet(Path(a.panel)/"CORRECTED125_PANEL.parquet")
    z["signal_date"]=pd.to_datetime(z.signal_date)
    z["exit_date_21"]=pd.to_datetime(z.exit_date_21)
    assert z.ticker.nunique()==148
    first=pd.Timestamp(f"{a.year}-01-01")
    tr=z[z.signal_date.lt(first)&z.signal_date.ge("2012-01-01")&
         z.exit_date_21.lt(first)&z.fwd_ret_21.notna()].copy()
    # Eligibility must never depend on a yet-to-be-realized forward label.
    # Keep all ex-ante feature-eligible ISIN in the prediction set.
    te=z[z.signal_date.dt.year.eq(a.year)&
         z.signal_date.between("2018-01-01","2026-05-31")].copy()
    tr=tr.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    te=te.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    # The 125-feature pack's original target rank includes other partial-
    # feature instruments. Recompute the OOS learning label strictly on
    # the dynamic, truly mature eligible universe of each signal date.
    tr["train_pct"]=tr.groupby("signal_date").fwd_ret_21.rank(method="average",pct=True)
    group=tr.groupby("signal_date",sort=True).size().to_numpy(int)
    assert len(tr)>1000 and len(te)>60 and group.sum()==len(tr)
    assert tr.signal_date.min().year==2012
    assert tr.exit_date_21.max()<first
    assert te.groupby("signal_date").size().ge(24).all()
    valid_dates=sorted(te.signal_date.unique())
    if a.year==2026: assert len(valid_dates)==5,(a.year,valid_dates)
    else:assert len(valid_dates)==12,(a.year,len(valid_dates))
    yf=100*pd.to_numeric(tr.train_pct).to_numpy(float)
    yrank=np.rint(yf).astype(int)
    ret=np.log1p(tr.fwd_ret_21.clip(lower=-.95))
    abs_y=100*ret.clip(-.25,.25).to_numpy(float)
    rel_y=100*(ret-ret.groupby(tr.signal_date).transform("median")).clip(-.25,.25).to_numpy(float)
    assert np.isfinite(abs_y).all() and np.isfinite(rel_y).all()
    cfg=dict(K.COMPACT_PARAMS)
    rows=[];aud=[]
    x125=tr[ALL].replace([np.inf,-np.inf],np.nan)
    xt125=te[ALL].replace([np.inf,-np.inf],np.nan)
    for name,(style,level) in RANKERS.items():
        kw=dict(cfg)
        if style=="leaf":kw.update(max_depth=0,grow_policy="lossguide",max_leaves=level)
        predictions=[]
        for seed in SEEDS:
            mdl=XGBRanker(**kw,random_state=seed)
            mdl.fit(x125,yrank,group=group,verbose=False)
            predictions.append(mdl.predict(xt125))
        yp=np.mean(predictions,axis=0)
        result=te[["signal_date","ticker","fwd_ret_21"]].copy()
        result["variant"]=name;result["pred"]=yp
        rows.append(result)
        print("EU148_RANKER_FIT",a.year,name,len(tr),len(te),flush=True)
        aud.append(dict(year=a.year,variant=name,train_rows=len(tr),
            train_months=len(group),test_rows=len(te),
            test_months=len(valid_dates),n_train_unique_isin=tr.ticker.nunique(),
            n_test_unique_isin=te.ticker.nunique(),last_matured_train_label=str(tr.exit_date_21.max().date()),
            feature_count=125,seed_list=list(SEEDS),n_estimators=kw["n_estimators"],model_parameters=kw))
    for name in REGS:
        selected=ALL if name not in ("REG_REL101","REG_ABS101") else SHORT
        yy=rel_y if name.startswith("REG_REL") or name=="REG_HUBER125" else abs_y
        kw=dict(cfg, max_depth=0,grow_policy="lossguide",max_leaves=127,
                objective="reg:squarederror",eval_metric="rmse")
        if name=="REG_HUBER125":
            kw.update(objective="reg:pseudohubererror",eval_metric="mae",huber_slope=1.0)
        X=tr[selected].replace([np.inf,-np.inf],np.nan)
        Xt=te[selected].replace([np.inf,-np.inf],np.nan)
        predictions=[]
        for seed in SEEDS:
            mdl=XGBRegressor(**kw,random_state=seed)
            mdl.fit(X,yy,verbose=False)
            predictions.append(mdl.predict(Xt))
        yp=np.mean(predictions,axis=0)
        result=te[["signal_date","ticker","fwd_ret_21"]].copy()
        result["variant"]=name;result["pred"]=yp
        rows.append(result)
        print("EU148_REGRESSOR_FIT",a.year,name,len(tr),len(te),flush=True)
        aud.append(dict(year=a.year,variant=name,train_rows=len(tr),
            train_months=len(group),test_rows=len(te),test_months=len(valid_dates),
            n_train_unique_isin=tr.ticker.nunique(),
            n_test_unique_isin=te.ticker.nunique(),last_matured_train_label=str(tr.exit_date_21.max().date()),
            feature_count=len(selected),seed_list=list(SEEDS),model_parameters=kw))
    result=pd.concat(rows,ignore_index=True)
    assert result.groupby(["variant","signal_date"]).ticker.nunique().ge(24).all()
    assert not result.duplicated(["variant","signal_date","ticker"]).any()
    assert set(result.variant)==set(RANKERS)|set(REGS)
    result.to_csv(out/"YEARLY_EU148_ALL_HEADS.csv",index=False)
    (out/"YEAR_FIT_AUDIT.json").write_text(json.dumps(aud,indent=2,default=str))
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        year=a.year,source_kernel="etf_trader_v3.source_only.kernel",
        n_etfs_at_max=148,currency="EUR",warmup_252=True,
        ranker_challengers=list(RANKERS),regressors=list(REGS),
        source_reference="2010-2026 exact legal ISIN venue data with listings",
        annual_mature_label_cutoff=str(first.date()),
        training_only_2012_or_later=True,
        months=len(valid_dates),test_rows=len(te),
       test_missing_future_label_count=int(te.fwd_ret_21.isna().sum()),
       test_universe_selected_without_using_future_labels=True,
        model_seeds=list(SEEDS),
        no_models_promoted_to_production=True),indent=2))
    print("EU148_CORRECTED_V3_ANNUAL_PASS",a.year,len(te),len(group),flush=True)
if __name__=="__main__":main()
