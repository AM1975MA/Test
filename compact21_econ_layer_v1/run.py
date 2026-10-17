"""Annual OOS-only economic layer on untouched BASE, source-only comparison."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from compact21_econ_layer_v1.core import VARIANT,KEYS,AUX_FEATURES,learn,predict,array_hash,MIN_DATES
from compact21_predictive_v2.run import numerical_gate,predictions_frame
from compact21_predictive_v2.metrics import evaluate,paired_compare
from etf_trader.source_only import kernel as k
from paper_ltr_v1 import learner as v1
from paper_ltr_v1.run import annual_frames,verified_baseline
from pls_xgb_v1.run import verify_keys,disagreement
from paper_ltr_v2.replay import sha

def merge_base(frame, archive):
    """Constrain BASE score join to strictly identical indexed forecast keys."""
    base=archive[list(KEYS)+["pred"]].rename(columns={"pred":"_base_pred"})
    if base.duplicated(list(KEYS)).any():raise ValueError("Duplicate BASE archive")
    a=frame.sort_values(list(KEYS)).reset_index(drop=True)
    b=base.sort_values(list(KEYS)).reset_index(drop=True)
    if not a[list(KEYS)].equals(b[list(KEYS)]):raise ValueError("BASE OOS coverage not exact")
    merged=a.merge(base,on=list(KEYS),how="left",validate="one_to_one")
    if len(merged)!=len(a) or merged["_base_pred"].isna().any():raise ValueError("BASE score mismatch")
    return merged

def fingerprint_full_train(train,year):
    sub,val,_=v1.split_training(train,year)
    return dict(train_keys_sha256=v1.keys_hash(train),subtrain_keys_sha256=v1.keys_hash(sub),
       validation_keys_sha256=v1.keys_hash(val),
       train_matrix_sha256=v1.array_hash(v1.raw_matrix(train)),
       train_labels_sha256=v1.array_hash(v1.decile_labels(train)))

def main():
    p=argparse.ArgumentParser()
    for i in (1,2,3):p.add_argument(f"--r{i}",required=True)
    p.add_argument("--baseline",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();numeric=numerical_gate()
    panels={};hashes={}
    for i in (1,2,3):
        f=Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet"
        hashes[str(i)]=sha(f)
        panels[i]=pd.read_parquet(f).copy()
        for col in ("signal_date","exit_date_21"):panels[i][col]=pd.to_datetime(panels[i][col])
        for col in AUX_FEATURES:
            if col not in panels[i]:raise ValueError("Missing frozen source feature "+col)
    base_result,base_audit=verified_baseline(a.baseline,hashes,panels)
    native_base=pd.read_parquet(Path(a.baseline)/"NATIVE_PREDICTIONS.parquet").copy()
    common_base=pd.read_parquet(Path(a.baseline)/"COMMON_PREDICTIONS.parquet").copy()
    for frame in (native_base,common_base):
        frame["signal_date"]=pd.to_datetime(frame["signal_date"])
        frame["vintage"]=frame["vintage"].astype(str)
    # All archived BASE annual forecasts were genuinely OOS and match exact native source rows.
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError("Output must be new")
    out.mkdir(parents=True)
    meta={};native=[];common=[];trained=0;fallback=0
    record=dict(status="RUNNING",variant=VARIANT,
        input_sha256=hashes,baseline_audit=base_audit,
        baseline_result_sha256=sha(Path(a.baseline)/"RESULT.json"),
        numerical_contract=numeric,protocol_sha256=sha(ROOT/"compact21_econ_layer_v1/PROTOCOL.md"),
        source_sha256={f.name:sha(f) for f in sorted((ROOT/"compact21_econ_layer_v1").glob("*.py"))},
        production_adoption=False,baseline_seed_fits=0,layer_trainings=0)
    (out/"INPUT_CONTRACT.json").write_text(json.dumps(record,indent=2)+"\n")
    try:
        for year in range(2017,2027):
            cutoff=pd.Timestamp(year,1,1)
            trains,tests,shared=annual_frames(panels,year)
            meta[str(year)]={}
            for i in (1,2,3):
                archive_nat=native_base[native_base.vintage.eq(str(i))].copy()
                archive_com=common_base[common_base.vintage.eq(str(i))].copy()
                nn=archive_nat[archive_nat.signal_date.dt.year.eq(year)]
                cc=archive_com[archive_com.signal_date.dt.year.eq(year)]
                native_frame=merge_base(tests[i],nn)
                common_frame=merge_base(shared,cc)
                historical_archive=archive_nat[archive_nat.signal_date<cutoff]
                hist=panels[i].merge(historical_archive[list(KEYS)+["pred"]].rename(
                    columns={"pred":"_base_pred"}),on=list(KEYS),how="inner",validate="one_to_one")
                hist=hist.sort_values(list(KEYS)).reset_index(drop=True)
                hist=hist[(hist.signal_date<cutoff)&hist.exit_date_21.notna()&
                    (hist.exit_date_21<cutoff)&hist.fwd_ret_21.notna()].reset_index(drop=True)
                if (hist.signal_date.dt.year<2017).any() or (hist.signal_date>=cutoff).any():
                    raise ValueError("Layer historical OOS training dates invalid")
                # A mature label at this cutoff can only come from previously evaluated
                # original XGB annual forecasts; every source/row must be in immutable BASE.
                keys=hist[list(KEYS)].merge(historical_archive[list(KEYS)],on=list(KEYS),
                    how="left",indicator=True,validate="one_to_one")
                if (keys["_merge"]!="both").any():raise ValueError("Historical BASE provenance invalid")
                model,details=learn(hist,cutoff)
                if model is None:fallback+=1
                else:trained+=1
                predictions=[predict(frame,model) for frame in (common_frame,native_frame)]
                # Independent refit / byte-identical layer scores guards deterministic behavior.
                model2,_=learn(hist,cutoff)
                rerun=[predict(frame,model2) for frame in (common_frame,native_frame)]
                if any(a.tobytes()!=b.tobytes() for a,b in zip(predictions,rerun)):
                    raise ValueError("Economic layer nondeterministic")
                if model is None and not np.array_equal(predictions[1],native_frame["_base_pred"].to_numpy(float)):
                    raise ValueError("BASE fallback not exact")
                cn,nn_out=predictions
                cf=shared[list(KEYS)].copy();cf["pred"]=cn;cf["vintage"]=str(i);common.append(cf)
                native.append(predictions_frame(tests[i],nn_out,i))
                detail=fingerprint_full_train(trains[i],year)
                detail.update(kind=VARIANT,meta_learning=details,
                    baseline_inference_native_hash=array_hash(native_frame["_base_pred"].to_numpy(float)),
                    baseline_inference_common_hash=array_hash(common_frame["_base_pred"].to_numpy(float)),
                    layer_native_prediction_sha256=array_hash(nn_out),
                    layer_common_prediction_sha256=array_hash(cn),
                    baseline_model_retraining=False,layer_prediction_determinism_PASS=True)
                meta[str(year)][str(i)]=detail
            record["year_complete"]=year
            (out/"PROGRESS.json").write_text(json.dumps(dict(year=year,layer_fit_count=trained,
                base_fallback_count=fallback))+"\n")
            print(json.dumps(dict(year=year,layer_fit_count=trained,base_fallback_count=fallback)),flush=True)
        if trained+fallback!=30:raise ValueError("Missing annual source combinations")
        folder=out/VARIANT;folder.mkdir()
        nat=pd.concat(native,ignore_index=True)
        com=pd.concat(common,ignore_index=True)
        verify_keys(nat,native_base)
        verify_keys(com,common_base)
        left=nat.assign(vintage=nat.vintage.astype(str)).sort_values(
            ["vintage","signal_date","ticker"]).reset_index(drop=True)
        right=native_base.sort_values(["vintage","signal_date","ticker"]).reset_index(drop=True)
        for col in ("target_rank_21","target_ret_21"):
            if col not in left or col not in right or not left[col].equals(right[col]):
                raise ValueError("Realized outcome differs from BASE "+col)
        nat.to_parquet(folder/"NATIVE_PREDICTIONS.parquet",index=False)
        com.to_parquet(folder/"COMMON_PREDICTIONS.parquet",index=False)
        qa=evaluate(nat,quality_exit_cutoff="2026-07-01")
        qbase=evaluate(native_base,quality_exit_cutoff="2026-07-01")
        if qa["coverage"]!=qbase["coverage"]:raise ValueError("Evaluation coverage changed")
        stability=disagreement(com)
        paired=paired_compare(qa,qbase,block_lengths=(3,6,12),n_bootstrap=1000,seed=20261017)
        candidate=dict(status="PAPER_LTR_V2_COMPLETE",variant=VARIANT,
            input_sha256=hashes,per_year={year:dict(transforms=detail,maturity_PASS=True)
                for year,detail in meta.items()},
            ALL_MATURITY_PASS=True,baseline=base_audit,baseline_model_retraining=False,
            layer_trainings=trained,base_fallbacks=fallback,
            training_source="verified BASE annual out_of_sample predictions 2017 onwards",
            predictive=qa,stability=stability,production_adoption=False,
            protocol_sha256=record["protocol_sha256"],
            files_sha256={name:sha(folder/name) for name in
              ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet")})
        (folder/"RESULT.json").write_text(json.dumps(candidate,indent=2,allow_nan=False)+"\n")
        summary=dict(status="ECON_LAYER_PREDICTIVE_COMPLETE",variant=VARIANT,
            baseline=qbase["aggregate_by_date"],candidate=qa["aggregate_by_date"],
            per_year=qa["per_year"],paired=paired,
            base_stability=disagreement(common_base),candidate_stability=stability,
            baseline_fits_executed=0,layer_fits=trained,exact_base_fallbacks=fallback,
            no_future_meta_labels=True,source_vintages_correlated=True,
            historical_data_reused=True,production_adoption=False)
        (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
        print(json.dumps({key:summary[key] for key in ("status","baseline","candidate",
             "base_stability","candidate_stability","layer_fits","exact_base_fallbacks")},indent=2),flush=True)
    except Exception as e:
        record.update(status="FAILED",error=str(e))
        (out/"FAILURE.json").write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")
        raise
if __name__=="__main__":main()
