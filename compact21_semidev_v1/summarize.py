"""Independent retained-vector validation for the single frozen semidev view.

Uses original V2 outcomes and its unchanged predictive/stability gates. The
same history has already been explored; passing a development gate never
authorizes deployment or establishes untouched holdout generalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from compact21_learner_swap_v1.learners import array_hash
from compact21_predictive_v2.metrics import evaluate, paired_compare
from compact21_predictive_v2.summarize import load_variant, normalized_numeric, stability_by_date, gate
from ranker_stability_v1.run_ranker_benchmark_full import quality

LINE = "COMPACT21_SEMIDEV_V1"
VARIANT = "BASE_SEMIDEV"
YEARS = tuple(range(2017,2027))
KEYS = ["signal_date", "ticker"]
VECTOR_KEYS = ["vintage", *KEYS]
OUTCOMES = ["target_rank_21", "exit_date_21", "target_ret_21"]
FILES = ("NATIVE_PREDICTIONS.parquet", "COMMON_PREDICTIONS.parquet",
    "CONTROL_NATIVE_PREDICTIONS.parquet", "CONTROL_COMMON_PREDICTIONS.parquet")
CHANGED = [f"downvol{h}{suffix}" for h in (21,63,126) for suffix in ("","_pct","_dev")]
FIT_SOURCES = ("compact21_learner_swap_v1/learners.py", "ranker_stability_v1/run_ranker_benchmark_full.py",
    "vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py", "vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py",
    "vendor/etf_trader_v2/src/etf_trader/source_only/raw_io.py", "compact21_predictive_v2/run.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def keys_hash(frame):
    data=frame[KEYS].sort_values(KEYS).to_csv(index=False,date_format="%Y-%m-%dT%H:%M:%S",lineterminator="\n")
    return hashlib.sha256(data.encode()).hexdigest()


def exact_frame(actual, expected, columns, context):
    """Strict dtype/value equality, also retaining float sign and NaN bits."""
    try:
        a,b=actual[columns].reset_index(drop=True),expected[columns].reset_index(drop=True)
        pd.testing.assert_frame_equal(a,b,check_exact=True)
        for column in columns:
            if pd.api.types.is_float_dtype(a[column].dtype):
                aa,bb=a[column].to_numpy(),b[column].to_numpy()
                if aa.tobytes()!=bb.tobytes():
                    raise ValueError(f"{context}: float bits differ in {column}")
    except (AssertionError,KeyError) as error:
        raise ValueError(f"{context}: schema, dtype or values differ") from error


def sorted_vectors(frame,year,context,require_outcomes=False):
    required=VECTOR_KEYS+["pred"]+(OUTCOMES if require_outcomes else [])
    if not set(required).issubset(frame) or frame.empty:
        raise ValueError(f"{context}: missing vector schema/rows")
    if frame[VECTOR_KEYS].isna().any().any() or frame.duplicated(VECTOR_KEYS).any():
        raise ValueError(f"{context}: duplicate/missing keys")
    if set(frame.vintage)!={1,2,3} or not frame.groupby("signal_date").vintage.nunique().eq(3).all():
        raise ValueError(f"{context}: missing vintage/date")
    if not pd.api.types.is_datetime64_any_dtype(frame.signal_date.dtype) or frame.signal_date.dt.tz is not None:
        raise ValueError(f"{context}: invalid session date dtype")
    if not frame.signal_date.eq(frame.signal_date.dt.normalize()).all():
        raise ValueError(f"{context}: unnormalized session date")
    if not frame.signal_date.dt.year.eq(year).all() or (frame.signal_date>pd.Timestamp("2026-06-30")).any():
        raise ValueError(f"{context}: wrong annual inference dates")
    if not np.isfinite(frame.pred.to_numpy(float)).all():
        raise ValueError(f"{context}: nonfinite predictions")
    return frame.sort_values(VECTOR_KEYS).reset_index(drop=True)


def validate_maturity(audit,year,context):
    dates=[pd.Timestamp(audit[key]) for key in ("cutoff","max_signal_date","max_exit_date_21")]
    cutoff=pd.Timestamp(year,1,1)
    if any(pd.isna(date) or date.tz is not None for date in dates) or audit["maturity_PASS"] is not True or dates[0]!=cutoff or dates[1]>=cutoff or dates[2]>=cutoff:
        raise ValueError(f"{context}: immature fit")


def prediction_audit(audit,common,native,repeat,context):
    hashes=[array_hash(frame.loc[frame.vintage==repeat,"pred"].to_numpy()) for frame in (common,native)]
    if audit.get("prediction_sha256")!=hashes:
        raise ValueError(f"{context}: retained prediction hashes differ")


def load_year(path,base):
    """Verify one annual job independently against original BASE evidence."""
    path=Path(path);r=json.loads(path.read_text())
    if r.get("line")!=LINE or r.get("variant")!=VARIANT or r.get("status")!=LINE+"_COMPLETE":
        raise ValueError("Wrong semidev registry/status")
    years=r.get("years")
    if not isinstance(years,list) or len(years)!=1 or years[0] not in YEARS:
        raise ValueError("Semidev job must contain one registered annual fold")
    year=years[0]
    if set(r.get("per_year",{}))!={str(year)}:
        raise ValueError("Annual audit coverage mismatch")
    if r.get("negative_feedback_changed") is not False or r.get("production_adoption") is not False or r.get("portfolio_evaluation") is not False:
        raise ValueError("Semidev scope changed")
    if r.get("ALL_DETERMINISM_PASS") is not True or r.get("LEGACY_PARITY_PASS") is not True:
        raise ValueError("Declared refit/BASE control failure")
    if set(r.get("files_sha256",{}))!=set(FILES):
        raise ValueError("Missing retained candidate/control vectors")
    for name in FILES:
        if sha(path.parent/name)!=r["files_sha256"][name]:
            raise ValueError("Altered annual vector evidence")
    br=base["result"]
    if r["input_sha256"]!=br["input_sha256"] or r["baseline_input_contract"]!=br["input_contract"]:
        raise ValueError("Frozen inputs/cutoffs changed")
    if set(r["fit_sources"])!=set(FIT_SOURCES) or any(r["fit_sources"][name]!=br["sources"][name] or r["sources"].get(name)!=br["sources"][name] for name in FIT_SOURCES):
        raise ValueError("Original BASE fit sources changed")
    contract=r["input_contract"]
    if contract["line"]!=LINE or contract["original_ti_sha256"]!=br["input_sha256"] or contract["signal_cutoff"]!="2026-06-30" or contract["quality_exit_cutoff"]!="2026-07-01" or contract["common_inference_repeat"]!=2 or contract["train_cohorts"]!="original_native_frozen_before_view" or contract["changed_columns"]!=CHANGED:
        raise ValueError("Registered semidev view contract changed")
    if contract["ref_base_result_sha256"]!=base["sha256"] or contract["reference_prediction_sha256"]!=br["files_sha256"]:
        raise ValueError("Original BASE reference identity changed")
    if normalized_numeric(r["numeric_contract"])!=normalized_numeric(br["numeric_contract"]):
        raise ValueError("Old BASE numerical contract differs")
    vectors={name:sorted_vectors(pd.read_parquet(path.parent/name),year,name,
        require_outcomes="NATIVE" in name) for name in FILES}
    native=vectors[FILES[0]];common=vectors[FILES[1]]
    control_native=vectors[FILES[2]];control_common=vectors[FILES[3]]
    old_native=base["native"].loc[base["native"].signal_date.dt.year==year].sort_values(VECTOR_KEYS).reset_index(drop=True)
    old_common=base["common"].loc[base["common"].signal_date.dt.year==year].sort_values(VECTOR_KEYS).reset_index(drop=True)
    for candidate,control,old,context in ((native,control_native,old_native,"native"),(common,control_common,old_common,"common")):
        exact_frame(candidate,old,VECTOR_KEYS,context+" candidate keys")
        exact_frame(control,old,VECTOR_KEYS+["pred"],context+" BASE control")
        if context=="native":
            exact_frame(candidate,old,OUTCOMES,"Original quality outcomes")
            exact_frame(control,old,OUTCOMES,"BASE quality outcomes")
    audit=r["per_year"][str(year)];old_audit=br["per_year"][str(year)]
    if audit["evaluation_coverage"]!=old_audit["evaluation_coverage"]:
        raise ValueError("Native/common/training coverage changed")
    for field in ("transforms","control_transforms","independent_refits","legacy_control","view_audit"):
        if set(audit[field])!={"1","2","3"}:
            raise ValueError("Missing vintage audit: "+field)
    if audit["determinism_PASS"] is not True:
        raise ValueError("Independent annual refit failure")
    for repeat in (1,2,3):
        key=str(repeat);ca=audit["transforms"][key];ba=audit["control_transforms"][key]
        old=old_audit["transforms"][key]
        validate_maturity(ca,year,"Candidate "+key);validate_maturity(ba,year,"BASE "+key)
        prediction_audit(ca,common,native,repeat,"Candidate "+key)
        prediction_audit(ba,control_common,control_native,repeat,"BASE "+key)
        if ba!=old:
            raise ValueError("Original BASE learned metadata differs")
        for field in ("train_labels_sha256","train_groups_sha256","train_rows","feature_names","cutoff","max_signal_date","max_exit_date_21"):
            if ca[field]!=old[field]:
                raise ValueError("Unchanged target/cohort/feature registry differs: "+field)
        refit=audit["independent_refits"][key]
        for field in ("native_bytes_exact","common_bytes_exact","learned_audit_exact"):
            if refit.get(field) is not True:
                raise ValueError("Candidate refit evidence failed")
        validate_maturity(refit["refit_audit"],year,"Candidate refit "+key)
        if refit["refit_audit"]!=ca:
            raise ValueError("Independent candidate learned metadata differs")
        if refit.get("prediction_sha256")!=ca["prediction_sha256"]:
            raise ValueError("Independent candidate prediction hashes differ")
        controls=audit["legacy_control"][key]
        if any(controls.get(field) is not True for field in ("native_bytes_exact","common_bytes_exact","metadata_exact","legacy_hashes_exact")):
            raise ValueError("Original BASE controls failed")
        view=audit["view_audit"][key]
        for field in ("unchanged_columns_exact","baseline_cohorts_exact","maturity_PASS","raw_hashes_PASS"):
            if view.get(field) is not True:
                raise ValueError("Semidev view contract failed: "+field)
        if view["donor_repeat"]!=repeat or view["population_count"]!=149 or len(set(view["population"]))!=149 or sorted(view["population"])!=sorted(old_native.ticker.unique()) or view["common_donor_repeat"]!=2:
            raise ValueError("Semidev donor/population changed")
        if view["changed_columns"]!=CHANGED or view["preserved_features"]!=116 or view["population_equal_to_original_ti"] is not True or view["cohort_selection"]!="original_TI_only_never_new_view" or view["normalization"]!="canonical149_full_date_before_original_eligibility":
            raise ValueError("Unregistered feature/membership intervention")
        if view["raw_files_verified"]!=151 or len(view["raw_file_sha256"])!=151 or view["raw_contract_sha256"]!=contract["raw_contract_sha256"][key]:
            raise ValueError("Incomplete frozen raw evidence")
        recon=view["original_downvol_reconstruction"]
        if recon["PASS"] is not True or set(recon["checks"])!=set(CHANGED):
            raise ValueError("Missing original downside reconstruction")
        for feature,check in recon["checks"].items():
            difference=check["max_abs_finite_difference"]
            tolerance=0. if feature.endswith("_pct") else 1e-10 if feature.endswith("_dev") else 1e-12
            bit_claim=feature.endswith("_pct")
            if check["missing_mask_exact"] is not True or check["absolute_tolerance"]!=tolerance or difference is None or not np.isfinite(difference) or difference<0 or difference>tolerance or check["finite_rows"]<0 or check["finite_values_bit_exact_claimed"] is not bit_claim:
                raise ValueError("Original downside reconstruction failed")
        f=native.loc[native.vintage==repeat]
        mask=f.exit_date_21.notna()&f.target_rank_21.notna()&(f.exit_date_21<=pd.Timestamp("2026-07-01"))
        if audit["quality"][key]!=quality(f.loc[mask],f.loc[mask,"pred"].to_numpy()):
            raise ValueError("Reported quality differs from retained candidate vectors")
        cov=audit["evaluation_coverage"]
        if keys_hash(f)!=cov["test_keys_sha256"][key] or keys_hash(common.loc[common.vintage==repeat])!=cov["common_keys_sha256"]:
            raise ValueError("Retained annual cohort hashes differ")
    return dict(result=r,native=native,common=common,control_native=control_native,
        control_common=control_common,path=str(path),sha256=sha(path),year=year)


def summarize(root,reference_root,out):
    base=load_variant(reference_root,"BASE")
    if base["result"]["LEGACY_PARITY_PASS"] is not True:
        raise ValueError("Original BASE legacy controls failed")
    paths=[]
    for path in Path(root).rglob("RESULT.json"):
        if json.loads(path.read_text()).get("line")==LINE:
            paths.append(path)
    jobs={}
    invariant=None
    for path in paths:
        job=load_year(path,base);year=job["year"]
        if year in jobs:
            raise ValueError("Duplicate semidev annual job")
        r=job["result"]
        contract={key:r[key] for key in ("input_sha256","input_contract","baseline_input_contract","fit_sources","sources","preregistration_sha256","build_protocol_sha256")}
        contract["numeric_contract"]=normalized_numeric(r["numeric_contract"])
        if invariant is None:
            invariant=contract
        if contract!=invariant:
            raise ValueError("Mixed annual source/protocol/numerical contracts")
        jobs[year]=job
    if set(jobs)!=set(YEARS):
        raise ValueError("Incomplete 10-job annual matrix")
    native=pd.concat([jobs[y]["native"] for y in YEARS],ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
    common=pd.concat([jobs[y]["common"] for y in YEARS],ignore_index=True).sort_values(VECTOR_KEYS).reset_index(drop=True)
    old_native=base["native"].sort_values(VECTOR_KEYS).reset_index(drop=True)
    old_common=base["common"].sort_values(VECTOR_KEYS).reset_index(drop=True)
    exact_frame(native,old_native,VECTOR_KEYS+OUTCOMES,"Combined original native cohort/outcomes")
    exact_frame(common,old_common,VECTOR_KEYS,"Combined original common cohort")
    ev=evaluate(native,quality_exit_cutoff="2026-07-01",expected_keys=old_native[VECTOR_KEYS])
    if ev["coverage"]!=base["eval"]["coverage"] or ev["coverage"]["mature_dates"]!=113:
        raise ValueError("Original 113 mature-date coverage changed")
    comparison=paired_compare(ev,base["eval"])
    comparison["lower98_75_interpretation"]="Retained conservative one-sided 1.25% percentile bound for this single post-V2 development candidate; not membership in V2's original four-challenger family and not familywise control over previous research. Bootstrap calculations are unchanged."
    sc,sn=stability_by_date(common),stability_by_date(native)
    bc,bn=stability_by_date(old_common),stability_by_date(old_native)
    candidate={"eval":ev}
    qualification=gate(candidate,base,comparison,sc,sn,bc,bn,True)
    result=dict(status=LINE+"_SUMMARY_COMPLETE",variant=VARIANT,years=list(YEARS),
        all_controls_reproduced=True,all_independent_refits_PASS=True,
        models={"BASE":dict(predictive=base["eval"],common_stability=bc,native_stability=bn,gate=None),
            VARIANT:dict(predictive=ev,common_stability=sc,native_stability=sn,paired_vs_BASE=comparison,gate=qualification)},
        reference=dict(path=base["path"],sha256=base["sha256"]),contract=invariant,
        annual_jobs={str(year):dict(path=jobs[year]["path"],sha256=jobs[year]["sha256"]) for year in YEARS},
        registry=dict(annual_jobs=10,candidate_vintage_fits=30,independent_candidate_refits=30),
        production_adoption=False,negative_feedback_changed=False,portfolio_evaluation=False,
        uncertainty_registry=dict(candidate_count=1,post_v2_trial=True,retained_one_sided_alpha=.0125,
            original_v2_gate_field_name="primary_familywise_lower_positive",
            familywise_claim_over_post_v2_or_prior_research=False),
        interpretation="Single preregistered post-V2 development view on already explored original outcomes; unchanged V2 gate calculations and conservatively retained one-sided lower 98.75% bootstrap bound. This trial is separate from V2's original four-challenger family; no familywise control over past research, production adoption, or fresh holdout claim.")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    native.to_parquet(out/FILES[0],index=False);common.to_parquet(out/FILES[1],index=False)
    result["files_sha256"]={name:sha(out/name) for name in FILES[:2]}
    (out/"SUMMARY.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--inputs",required=True)
    parser.add_argument("--references",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    result=summarize(args.inputs,args.references,args.out)
    print(json.dumps(result["models"][VARIANT]["gate"],indent=2))
