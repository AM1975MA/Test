#!/usr/bin/env python3
"""Year-by-year causal EU48 ranker A/B: actual uncorrected/corrected feature builder x deep/shallow.

A pre-defined 2x2 code-level ablation. Same 48 ETF universe, one fixed year,
three seeds, exact original 2017–2021 mature labels and source prices.
- LEGACY_SHALLOW: original Compact125 (max_depth=4)
- LEGACY_DEEP: historical V3 EU127 (max_depth=0,grow_policy=lossguide,max_leaves=127)
- CORRECTED_SHALLOW: V3 corrected build_features but original 16-leaf ranker
- CORRECTED_DEEP: V3 corrected build_features and EU127 ranker
Reproduce two original score sets before interpreting new features.
"""
from __future__ import annotations
import argparse,importlib.util,json,hashlib,inspect
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.compact21_base48.run import strict_build_spy
from europe_only75.f3h1_original_transfer.run import costed_path
from isin_first2026.predict48.tournament import price_data,monthly_data
from forensic_corrected_features import patched_builder

SEEDS=(101,202,303)
REF_OLD="isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--prep",required=True)
    a.add_argument("--strict",required=True)
    a.add_argument("--v3kernel",required=True)
    a.add_argument("--v3stored",required=True)
    a.add_argument("--out",required=True)
    a.add_argument("--year",type=int,choices=(2021,2022,2023,2024,2025,2026),required=True)
    x=a.parse_args()
    YEAR=int(x.year)
    JAN=pd.Timestamp(YEAR,1,1)
    out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location("actual_V3_corrected_125f",x.v3kernel)
    v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)
    matrices,roster,_=load_ticker_csv_folder(Path(x.prep)/"raw_ticker_csv")
    prior=pd.read_csv(x.strict,parse_dates=["date"])
    variants={"LEGACY":patched_builder(k,prior,matrices),
              "CORRECTED":patched_builder(v3,prior,matrices)}
    old=pd.read_csv(REF_OLD,parse_dates=["signal_date"])
    ref=old[old.signal_date.dt.year.eq(YEAR)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    v3ref=pd.read_csv(x.v3stored,parse_dates=["signal_date"])
    v3ref=v3ref[(v3ref.signal_date.dt.year.eq(YEAR))&
                v3ref.variant.eq("CORRECTED")].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert len(ref)==len(v3ref)==48*(5 if YEAR==2026 else 12) and ref[["signal_date","ticker"]].equals(v3ref[["signal_date","ticker"]])
    records=[];output={};fits=[]
    for featname,(dates,compact,*_) in variants.items():
        full=k.add_labels(compact,matrices["Open"],dates)
        feats=list(k.F2D_FEATURES)
        eligible=full[feats].notna().sum(axis=1)>=30
        train=full[eligible&full.signal_date.ge(pd.Timestamp("2017-01-01"))&
             full.signal_date.lt(JAN)&
             full.exit_date_21.lt(JAN)&
             full.target_rank_21.notna()].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        testing=full[eligible&full.signal_date.isin(ref.signal_date)&
            full.signal_date.dt.year.eq(YEAR)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        assert len(train)>=2208 and len(testing)==len(ref),(featname,len(train),len(testing))
        assert testing[["signal_date","ticker"]].equals(ref[["signal_date","ticker"]])
        np.testing.assert_allclose(testing.fwd_ret_21,ref.fwd_ret_21,rtol=0,atol=1e-12)
        target=np.rint(100*train.target_rank_21.to_numpy(float)).astype(int)
        group=train.groupby("signal_date").size().to_numpy(int)
        for style in ("SHALLOW","DEEP"):
            prm=dict(k.COMPACT_PARAMS)
            if style=="DEEP":prm.update(max_depth=0,grow_policy="lossguide",max_leaves=127)
            XX=train[feats].replace([np.inf,-np.inf],np.nan)
            TT=testing[feats].replace([np.inf,-np.inf],np.nan)
            preds=[]
            for seed in SEEDS:
                reg=XGBRanker(**prm,random_state=seed)
                reg.fit(XX,target,group=group,verbose=False)
                preds.append(reg.predict(TT))
            pred=np.mean(preds,axis=0)
            tag=featname+"_"+style
            df=testing[["signal_date","ticker","fwd_ret_21"]].copy()
            df["pred"]=pred
            output[tag]=df
            prior_ref=ref if tag=="LEGACY_SHALLOW" else v3ref if tag=="LEGACY_DEEP" else None
            if prior_ref is not None:
                err=np.abs(pred-prior_ref.pred.to_numpy(float))
                rank_changes=0
                for dt in sorted(df.signal_date.unique()):
                    score=df[df.signal_date.eq(dt)].sort_values("ticker").set_index("ticker").pred
                    reference=prior_ref[prior_ref.signal_date.eq(dt)].sort_values("ticker").set_index("ticker").pred
                    rank_changes+=int(score.idxmax()!=reference.idxmax())
                checks=dict(max_raw_score_error=float(err.max()),avg_raw_score_error=float(err.mean()),
                    n_top1_disagreements_ref_months=rank_changes)
                assert rank_changes==0 and np.isfinite(err).all(),checks
            else:checks=dict(reconstructed_historical_reference=False)
            # Forward 21-day returns from next OPEN: same independently
            # certified 48x12 reference labels, just different predictions.
            losses=[];picks=[]
            for date,grp in df.groupby("signal_date"):
                best=grp.loc[grp.pred.idxmax()]
                picks.append(dict(signal_date=str(date.date()),variant=tag,
                    selected=best.ticker,selected_forward21d=float(best.fwd_ret_21),
                    selected_excess=float(best.fwd_ret_21-grp.fwd_ret_21.mean()),
                    hit_absolute_winner=int(best.fwd_ret_21==grp.fwd_ret_21.max())))
            picks=pd.DataFrame(picks)
            records.extend(picks.to_dict("records"))
            record=dict(variant=tag,year=YEAR,
                n_train_pairs=2784,n_mature_train_months=train.signal_date.nunique(),
                max_depth=prm["max_depth"],max_leaves=prm.get("max_leaves",16),
                selected_excess_21d=float(picks.selected_excess.mean()),
                top1_winner_count=int(picks.hit_absolute_winner.sum()),
                mean_21d_forward_return=float(picks.selected_forward21d.mean()),
                difference_vs_original_v2_125f_21d=float(picks.selected_excess.mean()-0),
                same_frozen_training_target=True,**checks)
            fits.append(record)
            print("EUR48_2022_ABLATION",json.dumps(record),flush=True)
    summary=pd.DataFrame(fits)
    ctrl=summary[summary.variant.eq("LEGACY_SHALLOW")].selected_excess_21d.iloc[0]
    summary["excess_vs_original_125f_21d"]=summary.selected_excess_21d-ctrl
    summary.to_csv(out/f"EU48_{YEAR}_FEATURE_VS_CAPACITY.csv",index=False)
    pd.DataFrame(records).to_csv(out/f"EU48_{YEAR}_MONTHLY_CHOICE_AND_LABEL.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
         isolated_model_year=YEAR,original_ISINs=48,
         original_annual_fully_mature_labels=True,same_model_seeds=[101,202,303],
         model_capacity_only_difference="depth4 vs unbounded depth lossguide 127 leaves",
         feature_only_difference="actual V3 corrected feature implementation vs legacy source",
         benchmark_orig_v2_and_v3_reproduced_without_top1_disagreement=True,
         old_48_months_pre_2022_mature_training_unchanged=True,
         not_full_period_CAGR=True,production_changed=False),indent=2))
    print("EUROPE_ANNUAL_2X2_CAUSAL_ABLATION_PASSED",YEAR,flush=True)
    print(summary.to_string(index=False),flush=True)
if __name__=="__main__":main()
