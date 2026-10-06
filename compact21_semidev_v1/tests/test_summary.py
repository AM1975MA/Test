"""Synthetic retained-vector checks; no financial fit or cloud action."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from compact21_semidev_v1 import summarize as summary


def numeric_contract():
    active=["SSE","SSE2","SSE3","SSSE3","SSE41","POPCNT","SSE42","AVX","F16C","FMA3","AVX2"]
    inactive=["AVX512F","AVX512CD","AVX512_KNL","AVX512_KNM","AVX512_SKX","AVX512_CLX","AVX512_CNL","AVX512_ICL","AVX512_SPR"]
    return dict(python="synthetic",machine="synthetic",numpy="2.3.5",pandas="synthetic",scipy="synthetic",
        sklearn="synthetic",execution_env={},numpy_build_config={"SIMD Extensions":{
            "baseline":active[:3],"found":active[3:],"not found":inactive}},
        effective_cpu_features={**{v:True for v in active},**{v:False for v in inactive}},threadpools=[])


class AnnualValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/"RESULT.json"
        ref_path=self.root/"REFERENCE.json";ref_path.write_text("Synthetic original BASE metadata")
        names=[f"T{i:03d}" for i in range(149)]
        original=pd.DataFrame(dict(signal_date=pd.Timestamp("2017-01-31"),ticker=names,
            pred=np.arange(149,dtype=float),target_rank_21=np.arange(1,150)/149,
            exit_date_21=pd.Timestamp("2017-03-02"),target_ret_21=np.arange(149)/1000.))
        old_native=pd.concat([original.assign(vintage=v) for v in (1,2,3)],ignore_index=True)
        old_common=old_native[summary.VECTOR_KEYS+["pred"]].copy()
        self.frames={summary.FILES[0]:old_native.assign(pred=old_native.pred+.125),
            summary.FILES[1]:old_common.assign(pred=old_common.pred+.125),
            summary.FILES[2]:old_native.copy(),summary.FILES[3]:old_common.copy()}
        digests={}
        for name in summary.FILES:
            (self.root/name).write_bytes(("synthetic evidence "+name).encode())
            digests[name]=summary.sha(self.root/name)
        features=summary.CHANGED+[f"other{i}" for i in range(116)]
        old_transforms={};candidate_transforms={};refits={};controls={};views={}
        for v in (1,2,3):
            old=dict(maturity_PASS=True,cutoff="2017-01-01",max_signal_date="2016-11-30",max_exit_date_21="2016-12-30",
                train_matrix_sha256=f"old-matrix-{v}",train_labels_sha256=f"labels-{v}",train_groups_sha256=f"groups-{v}",
                train_rows=149*60,feature_names=features,
                prediction_sha256=[summary.array_hash(f.loc[f.vintage==v,"pred"].to_numpy()) for f in (old_common,old_native)])
            new=deepcopy(old);new["train_matrix_sha256"]=f"new-matrix-{v}"
            new["prediction_sha256"]=[summary.array_hash(self.frames[name].loc[self.frames[name].vintage==v,"pred"].to_numpy()) for name in summary.FILES[:2][::-1]]
            old_transforms[str(v)]=old;candidate_transforms[str(v)]=new
            refits[str(v)]=dict(native_bytes_exact=True,common_bytes_exact=True,learned_audit_exact=True,
                refit_audit=deepcopy(new),prediction_sha256=deepcopy(new["prediction_sha256"]))
            controls[str(v)]=dict(native_bytes_exact=True,common_bytes_exact=True,metadata_exact=True,legacy_hashes_exact=True,fit_seconds=.01)
            checks={feature:dict(missing_mask_exact=True,max_abs_finite_difference=0.,finite_rows=100,
                absolute_tolerance=0. if feature.endswith("_pct") else 1e-10 if feature.endswith("_dev") else 1e-12,
                finite_values_bit_exact_claimed=feature.endswith("_pct")) for feature in summary.CHANGED}
            views[str(v)]=dict(unchanged_columns_exact=True,baseline_cohorts_exact=True,maturity_PASS=True,raw_hashes_PASS=True,
                donor_repeat=v,population_count=149,population=names,common_donor_repeat=2,
                changed_columns=summary.CHANGED,preserved_features=116,population_equal_to_original_ti=True,
                cohort_selection="original_TI_only_never_new_view",normalization="canonical149_full_date_before_original_eligibility",
                raw_files_verified=151,raw_file_sha256={f"raw{i}.csv":"synthetic" for i in range(151)},
                raw_contract_sha256=f"raw-contract-{v}",original_downvol_reconstruction=dict(PASS=True,checks=checks))
        coverage=dict(test_keys_sha256={str(v):summary.keys_hash(original) for v in (1,2,3)},
            train_keys_sha256={str(v):f"train-{v}" for v in (1,2,3)},common_keys_sha256=summary.keys_hash(original))
        fit_sources={name:f"frozen-source-{i}" for i,name in enumerate(summary.FIT_SOURCES)}
        baseline_input=dict(protocol="original BASE")
        br=dict(input_sha256={str(v):f"TI-{v}" for v in (1,2,3)},input_contract=baseline_input,
            sources=fit_sources,numeric_contract=numeric_contract(),LEGACY_PARITY_PASS=True,
            files_sha256={name:f"old-{name}" for name in summary.FILES[:2]},
            per_year={"2017":dict(transforms=old_transforms,evaluation_coverage=coverage)})
        self.base=dict(result=br,native=old_native,common=old_common,path=str(ref_path),sha256=summary.sha(ref_path))
        qualities={str(v):summary.quality(self.frames[summary.FILES[0]].loc[self.frames[summary.FILES[0]].vintage==v],
            self.frames[summary.FILES[0]].loc[self.frames[summary.FILES[0]].vintage==v,"pred"].to_numpy()) for v in (1,2,3)}
        self.r=dict(status=summary.LINE+"_COMPLETE",line=summary.LINE,variant=summary.VARIANT,years=[2017],
            per_year={"2017":dict(transforms=candidate_transforms,control_transforms=deepcopy(old_transforms),
                independent_refits=refits,legacy_control=controls,view_audit=views,determinism_PASS=True,
                quality=qualities,evaluation_coverage=deepcopy(coverage))},
            ALL_DETERMINISM_PASS=True,LEGACY_PARITY_PASS=True,files_sha256=digests,
            negative_feedback_changed=False,portfolio_evaluation=False,production_adoption=False,
            input_sha256=deepcopy(br["input_sha256"]),baseline_input_contract=deepcopy(baseline_input),
            numeric_contract=numeric_contract(),fit_sources=deepcopy(fit_sources),sources=deepcopy(fit_sources),
            preregistration_sha256="synthetic-science-protocol",build_protocol_sha256="synthetic-build-protocol",
            input_contract=dict(line=summary.LINE,original_ti_sha256=deepcopy(br["input_sha256"]),
                signal_cutoff="2026-06-30",quality_exit_cutoff="2026-07-01",common_inference_repeat=2,
                train_cohorts="original_native_frozen_before_view",changed_columns=summary.CHANGED,
                ref_base_result_sha256=self.base["sha256"],reference_prediction_sha256=deepcopy(br["files_sha256"]),
                raw_contract_sha256={str(v):f"raw-contract-{v}" for v in (1,2,3)}))

    def call(self):
        self.path.write_text(json.dumps(self.r,allow_nan=False))
        with patch.object(summary.pd,"read_parquet",side_effect=lambda p:self.frames[Path(p).name].copy()):
            return summary.load_year(self.path,self.base)

    def test_valid_job_accepts_real_control_fit_timing_but_rebuilds_arrays(self):
        result=self.call()
        self.assertEqual(result["year"],2017)
        self.assertEqual(len(result["native"]),447)

    def test_row_order_is_sorted_explicitly_before_bit_comparisons(self):
        for name in self.frames:
            self.frames[name]=self.frames[name].sample(frac=1,random_state=11)
        result=self.call()
        expected=self.frames[summary.FILES[0]].sort_values(summary.VECTOR_KEYS).reset_index(drop=True)
        pd.testing.assert_frame_equal(result["native"],expected)

    def test_missing_cohort_or_nonfinite_candidate_fails(self):
        original=deepcopy(self.frames)
        for kind in ("cohort","nonfinite"):
            with self.subTest(kind=kind):
                self.frames=deepcopy(original)
                if kind=="cohort":
                    self.frames[summary.FILES[0]]=self.frames[summary.FILES[0]].iloc[1:]
                else:
                    self.frames[summary.FILES[1]].loc[0,"pred"]=np.inf
                with self.assertRaises(ValueError):self.call()

    def test_original_outcome_signed_zero_bits_cannot_change(self):
        self.frames[summary.FILES[0]].loc[0,"target_ret_21"]=-0.
        with self.assertRaisesRegex(ValueError,"float bits"):
            self.call()

    def test_original_control_pred_signed_zero_bits_cannot_change(self):
        self.frames[summary.FILES[2]].loc[0,"pred"]=-0.
        with self.assertRaisesRegex(ValueError,"float bits"):
            self.call()

    def test_control_flags_failed_refit_or_metadata_disagreement_block(self):
        original=deepcopy(self.r)
        for kind in ("control","refitflag","refitaudit","controlmetadata","targetlabels"):
            with self.subTest(kind=kind):
                self.r=deepcopy(original);a=self.r["per_year"]["2017"]
                if kind=="control":a["legacy_control"]["1"]["native_bytes_exact"]=False
                elif kind=="refitflag":a["independent_refits"]["1"]["learned_audit_exact"]=False
                elif kind=="refitaudit":a["independent_refits"]["1"]["refit_audit"]["train_matrix_sha256"]="wrong"
                elif kind=="controlmetadata":a["control_transforms"]["1"]["train_matrix_sha256"]="wrong"
                else:a["transforms"]["1"]["train_labels_sha256"]="wrong"
                with self.assertRaises(ValueError):self.call()

    def test_declared_candidate_prediction_hashes_rederived(self):
        self.r["per_year"]["2017"]["transforms"]["1"]["prediction_sha256"][0]="wrong"
        with self.assertRaisesRegex(ValueError,"prediction hashes"):
            self.call()

    def test_nat_and_cutoff_training_boundaries_fail(self):
        original=deepcopy(self.r)
        for field,value in (("max_signal_date","NaT"),("max_exit_date_21","NaT"),("cutoff","NaT"),
                ("max_signal_date","2017-01-01"),("max_exit_date_21","2017-01-01")):
            with self.subTest(field=field,value=value):
                self.r=deepcopy(original)
                self.r["per_year"]["2017"]["transforms"]["1"][field]=value
                with self.assertRaisesRegex(ValueError,"immature"):
                    self.call()

    def test_legacy_fit_source_and_original_input_contract_are_frozen(self):
        original=deepcopy(self.r)
        for kind in ("source","baselinecontract","commonrepeat","registeredcolumn","numeric"):
            with self.subTest(kind=kind):
                self.r=deepcopy(original)
                if kind=="source":self.r["fit_sources"][summary.FIT_SOURCES[0]]="different"
                elif kind=="baselinecontract":self.r["baseline_input_contract"]["protocol"]="different"
                elif kind=="commonrepeat":self.r["input_contract"]["common_inference_repeat"]=1
                elif kind=="registeredcolumn":self.r["input_contract"]["changed_columns"]=["other"]
                else:self.r["numeric_contract"]["pandas"]="different"
                with self.assertRaises(ValueError):self.call()

    def test_original_feature_reconstruction_tolerances_not_relaxable(self):
        original=deepcopy(self.r)
        for feature,tol in (("downvol21",1e-12),("downvol21_pct",0.),("downvol21_dev",1e-10)):
            with self.subTest(feature=feature):
                self.r=deepcopy(original)
                check=self.r["per_year"]["2017"]["view_audit"]["1"]["original_downvol_reconstruction"]["checks"][feature]
                check["absolute_tolerance"]=tol+1e-9
                with self.assertRaisesRegex(ValueError,"reconstruction"):
                    self.call()
                self.r=deepcopy(original)
                check=self.r["per_year"]["2017"]["view_audit"]["1"]["original_downvol_reconstruction"]["checks"][feature]
                check["max_abs_finite_difference"]=tol+1e-14
                with self.assertRaisesRegex(ValueError,"reconstruction"):
                    self.call()

    def test_pct_requires_bit_exact_reconstruction_claim(self):
        self.r["per_year"]["2017"]["view_audit"]["1"]["original_downvol_reconstruction"]["checks"]["downvol21_pct"]["finite_values_bit_exact_claimed"]=False
        with self.assertRaisesRegex(ValueError,"reconstruction"):
            self.call()

    def test_population_original_mask_or_raw_hash_contract_tamper_fail(self):
        original=deepcopy(self.r)
        for field,value in (("population_count",148),("common_donor_repeat",1),("preserved_features",115),
                ("cohort_selection","new_view"),("raw_files_verified",150),("raw_contract_sha256","different")):
            with self.subTest(field=field):
                self.r=deepcopy(original)
                self.r["per_year"]["2017"]["view_audit"]["1"][field]=value
                with self.assertRaises(ValueError):self.call()

    def test_reported_quality_not_trusted_over_vectors(self):
        self.r["per_year"]["2017"]["quality"]["1"]["ndcg5"] += .001
        with self.assertRaisesRegex(ValueError,"Reported quality"):
            self.call()

    def test_retained_file_digest_or_year_status_invalid_fails(self):
        original=deepcopy(self.r)
        for field,value in (("status","RUNNING"),("years",[2017,2018]),("production_adoption",True)):
            with self.subTest(field=field):
                self.r=deepcopy(original);self.r[field]=value
                with self.assertRaises(ValueError):self.call()
        self.r=deepcopy(original)
        self.r["files_sha256"][summary.FILES[0]]="wrong"
        with self.assertRaisesRegex(ValueError,"Altered"):
            self.call()

    def test_incomplete_annual_matrix_cannot_produce_a_candidate(self):
        self.path.write_text(json.dumps(self.r))
        with patch.object(summary,"load_variant",return_value=self.base), \
                patch.object(summary,"load_year",return_value=self.call()):
            with self.assertRaisesRegex(ValueError,"Incomplete 10-job"):
                summary.summarize(self.root,self.root,self.root/"summary-output")

    def test_two_jobs_for_same_year_are_rejected(self):
        self.path.write_text(json.dumps(self.r));duplicate=self.root/"duplicate";duplicate.mkdir()
        (duplicate/"RESULT.json").write_text(json.dumps(self.r))
        job=self.call()
        with patch.object(summary,"load_variant",return_value=self.base),patch.object(summary,"load_year",return_value=job):
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                summary.summarize(self.root,self.root,self.root/"summary-output")


if __name__=="__main__":unittest.main()
