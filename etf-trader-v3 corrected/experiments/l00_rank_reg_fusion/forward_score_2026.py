#!/usr/bin/env python3
"""Locked 2026 first-stage continuation on append-only price source.

Uses identical 125 originally engineered features, hyperparams/seeds, and
2012–2025 label-matured training set. Reproduce Jan–May 2026 ORIGINAL CORRECTED
AND 5 regression raw predictions before accepting June–Aug forward scores.
Reject lookahead, adjusted-price historical revision, calendar drift,
unmatched incumbent OOS raw scores and changed canonical 500 baskets.
NO alteration of production or of 2026 trained first-stage hyperparams.
"""
from __future__ import annotations
import argparse,sys,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker,XGBRegressor
HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(HERE))
print("FORWARD_IMPORT_EVALUATE", __name__,flush=True)
import evaluate as E
print("FORWARD_IMPORT_AGGREGATE", __name__,flush=True)
from aggregate import read_shards
print("FORWARD_IMPORTED_REFERENCES",__name__,flush=True)
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder
REFERENCE_CUTOFF=pd.Timestamp("2026-05-31")
MATURED_TO=pd.Timestamp("2026-08-31")
YEARS_CUTOFF=pd.Timestamp("2026-01-01")
NAMES=("CORRECTED","REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
TARGET_PARITY_ABS=3e-5
TARGET_PARITY_REL=4e-5
def main():
    print("FORWARD_MAIN_ENTRY",sys.argv,flush=True)
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--old-shards",required=True)
    ap.add_argument("--original-raw",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path("regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv").read_bytes()).hexdigest()==E.BASKET_SHA
    oldinfo=json.loads((Path(args.raw)/"PROVENANCE.json").read_text())
    assert len(oldinfo["rows"])==149
    for t in oldinfo["rows"]:
        assert oldinfo["rows"][t]["original_sha256"]==hashlib.sha256((Path(args.original_raw)/(t+".csv")).read_bytes()).hexdigest()
    original,panel,valid,baskets=E.freeze_data(args.raw,"regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    assert len(baskets)==500 and len(E.ALL)==125 and len(E.NO_VOL)==101
    # Freeze exactly the pretrained source labels with explicitly observed
    # maturity cutoff; no training row in 2026 or from still-immature 2025.
    cut=(original.signal_date>=pd.Timestamp("2012-01-01")) & (
        original.signal_date<YEARS_CUTOFF) & (
        original.exit_date_21<YEARS_CUTOFF)&(
        original.target_rank_21.notna())&valid
    test=original.signal_date.dt.year.eq(2026)&valid
    tr=panel.loc[cut].sort_values(["signal_date","ticker"])
    te=panel.loc[test].sort_values(["signal_date","ticker"])
    assert tr.signal_date.nunique()>=150 and len(te)>=149*8
    assert tr.exit_date_21.max()<YEARS_CUTOFF
    groups=tr.groupby("signal_date",sort=True).size().to_numpy()
    assert groups.sum()==len(tr)
    train_rank=np.rint(100*tr.target_rank_21.to_numpy(float)).astype(int)
    logret=np.log1p(tr.fwd_ret_21.clip(lower=-.95).astype(float))
    absret=100*logret.clip(-.25,.25).to_numpy(float)
    relative=100*(logret-logret.groupby(tr.signal_date).transform("median")).clip(-.25,.25).to_numpy(float)
    assert np.isfinite(relative).all() and np.isfinite(absret).all()
    params=dict(E.v3.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide",max_leaves=127)
    oldscores,oldmonthly,olda=read_shards(args.old_shards,"regression")
    oldscores=oldscores.loc[oldscores.signal_date.dt.year.eq(2026)].copy()
    assert set(NAMES)==set(oldscores.variant) and oldscores.signal_date.max()<=REFERENCE_CUTOFF
    control_dates=sorted(oldscores.signal_date.unique())
    assert len(control_dates)==5 and len(te[te.signal_date.isin(control_dates)])==len(control_dates)*149
    exact_hash={}
    for d in control_dates:
        slice_=te[te.signal_date.eq(d)].sort_values("ticker")
        control=oldscores[(oldscores.signal_date.eq(d))&(oldscores.variant.eq("CORRECTED"))].sort_values("ticker")
        assert slice_.ticker.tolist()==control.ticker.tolist()
        # The historical 21-day adjusted next-open realized outcome is frozen.
        np.testing.assert_allclose(slice_.fwd_ret_21,control.fwd_ret_21,rtol=0,atol=1e-11)
        exact_hash[str(d.date())]=hashlib.sha256(slice_.fwd_ret_21.to_numpy(float).tobytes()).hexdigest()
    rows=[];audits=[]
    for arm in NAMES:
        names=E.ALL if arm not in ("REG_REL101","REG_ABS101") else E.NO_VOL
        xx=tr[names].replace([np.inf,-np.inf],np.nan)
        xt=te[names].replace([np.inf,-np.inf],np.nan)
        predicts=[]
        for seed in E.SEEDS:
            cfg=dict(params)
            if arm=="CORRECTED":
                model=XGBRanker(**cfg,random_state=seed)
                model.fit(xx,train_rank,group=groups,verbose=False)
            else:
                cfg.update(objective="reg:squarederror",eval_metric="rmse")
                if arm=="REG_HUBER125":
                    cfg.update(objective="reg:pseudohubererror",eval_metric="mae",huber_slope=1.0)
                target=relative if arm.startswith("REG_REL") or arm=="REG_HUBER125" else absret
                model=XGBRegressor(**cfg,random_state=seed)
                model.fit(xx,target,verbose=False)
            predicts.append(model.predict(xt))
            print("FROZEN_2026_REFIT",arm,seed,len(tr),len(te),flush=True)
        pred=np.mean(predicts,axis=0)
        df=te[["signal_date","ticker","fwd_ret_21"]].copy()
        df["pred"]=pred
        df.insert(0,"variant",arm)
        old=oldscores[oldscores.variant.eq(arm)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        matching=df.loc[df.signal_date.isin(control_dates)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        assert old[["signal_date","ticker"]].equals(matching[["signal_date","ticker"]]),(arm,"ticker mismatch")
        err=np.abs(matching.pred.to_numpy(float)-old.pred.to_numpy(float))
        tol=TARGET_PARITY_ABS+TARGET_PARITY_REL*np.abs(old.pred.to_numpy(float))
        worst=float(np.max(err))
        fraction=float((err<=tol).mean())
        # Even a very small score displacement can flip closely spaced ETF
        # rankings. Exact 500-basket Top1 parity is therefore independently
        # enforced for all 5 previously certified month ends.
        top_mismatch=0
        canon={pd.Timestamp(d):[] for d in control_dates}
        for date in control_dates:
            mm=matching[matching.signal_date.eq(date)]
            prior=old[old.signal_date.eq(date)]
            x=pd.Series(mm.pred.to_numpy(),index=mm.ticker).rank(pct=True)
            y=pd.Series(prior.pred.to_numpy(),index=prior.ticker).rank(pct=True)
            for basket in baskets:
                chosen=x.reindex(basket).idxmax()
                baseline=y.reindex(basket).idxmax()
                top_mismatch+=int(chosen!=baseline)
        checks=dict(arm=arm,original_months=len(control_dates),raw_mae=float(err.mean()),
            raw_max_abs=worst,within_tolerance_fraction=fraction,
            basket_top1_ranking_mismatch=top_mismatch,
            tolerance_atol=TARGET_PARITY_ABS,tolerance_rtol=TARGET_PARITY_REL)
        audits.append(checks)
        print("RETRAIN_PARITY",checks,flush=True)
        if fraction!=1 or top_mismatch:
            (out/"REPLAY_PARITY_FAILURE.json").write_text(json.dumps(audits,indent=2))
            raise RuntimeError("STOP: original corrected 2026 first-stage prediction reproduction failed "+arm)
        assert np.isfinite(pred).all()
        test_future=df[df.signal_date.gt(REFERENCE_CUTOFF)]
        assert set(test_future.signal_date.unique())>={pd.Timestamp("2026-06-30"),pd.Timestamp("2026-07-31"),pd.Timestamp("2026-08-31")}
        assert test_future[test_future.signal_date.le(MATURED_TO)].fwd_ret_21.notna().all()
        rows.append(df)
    all_2026=pd.concat(rows,ignore_index=True)
    assert not all_2026.duplicated(["variant","signal_date","ticker"]).any()
    assert all_2026.groupby(["variant","signal_date"]).size().eq(149).all()
    dates=sorted(all_2026.signal_date.unique())
    assert dates[-1]>=pd.Timestamp("2026-09-30")
    print("YEAR_2026_SIGNAL_DATES",list(map(str,dates)),flush=True)
    # Never score September as a matured 21-day forward outcome.
    september=all_2026[all_2026.signal_date.ge(pd.Timestamp("2026-09-30"))]
    assert september.fwd_ret_21.isna().all()
    all_2026.to_csv(out/"YEAR2026_ALL_SCORES.csv",index=False)
    all_2026[all_2026.signal_date.gt(REFERENCE_CUTOFF)&all_2026.signal_date.le(MATURED_TO)].to_csv(
        out/"NEW_MATURED_2026_JUN_AUG_SCORES.csv",index=False)
    september[["variant","signal_date","ticker","pred"]].to_csv(out/"SEPTEMBER_2026_UNMATURED_PREDICTIONS.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"REPRODUCTION_AUDIT.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        branch="research-v3-forward-locked-20261024",
        first_stage_source="CORRECTED125 plus five original regression heads",
        frozen_train_before="2026-01-01",
        last_train_label_maturity=str(tr.exit_date_21.max().date()),
        n_train_rows=len(tr),n_train_months=tr.signal_date.nunique(),
        replays_months=list(map(str,control_dates)),
        new_matured_signal_dates=["2026-06-30","2026-07-31","2026-08-31"],
        future_unmatured_signal="2026-09-30",
        floating_raw_score_tolerance=dict(atol=TARGET_PARITY_ABS,rtol=TARGET_PARITY_REL),
        original_rank_head_parity_for_500_baskets=True,
        earliest_prospective_lock="2026-10-24",
        new_months_are_retrospective_holdout_not_prospective=True,
        original_raw_run=39482809691,original_shards_run=40016809498,
        production_modified=False,history_revision_forbidden=True,
        price_provenance_source="forward_raw/PROVENANCE.json",
        outcomes_measured_from_next_open_21_sessions=True,
        parity_checks=audits),indent=2,default=str))
    print("LOCKED_FORWARD_FIRST_STAGE_PASS",len(all_2026),flush=True)
if __name__=="__main__":main()
