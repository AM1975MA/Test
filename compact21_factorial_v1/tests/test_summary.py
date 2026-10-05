"""Synthetic aggregation/registry tests; no real outcomes or models are loaded."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]
from compact21_factorial_v1 import summarize as summary
from compact21_learner_swap_v1.learners import array_hash


def pair_fixture(mad=.2, spearman=.5, effect=.1):
    contrasts = {name: dict(rank_mad=mad, spearman=spearman, top1_flip=.1, top5_jaccard=.9)
        for name in ("AA-BA", "AB-BB", "AA-AB", "BA-BB", "AA-BB")}
    return {"aggregate": {"effects": {"feature_mean_abs": effect}, "contrasts": contrasts},
        "coverage": {"dates": 1}}


class PairAggregationTests(unittest.TestCase):
    def test_pairs_have_equal_weight_independent_of_coverage_count(self):
        pairs = {"1-2": pair_fixture(.2, .2, .1), "1-3": pair_fixture(.4, .5, .4), "2-3": pair_fixture(.6, .8, .7)}
        pairs["2-3"]["coverage"]["dates"] = 100
        result = summary.aggregate_pairs(pairs)
        self.assertAlmostEqual(result["effects"]["feature_mean_abs"], .4)
        self.assertAlmostEqual(result["contrasts"]["AA-BB"]["rank_mad"], .4)
        self.assertAlmostEqual(result["contrasts"]["AA-BB"]["spearman"], .5)

    def test_undefined_spearman_is_excluded_and_coverage_reported(self):
        pairs = {"1-2": pair_fixture(spearman=.2), "1-3": pair_fixture(spearman=None), "2-3": pair_fixture(spearman=.8)}
        result = summary.aggregate_pairs(pairs)
        for contrast in result["contrasts"].values():
            self.assertAlmostEqual(contrast["spearman"], .5)
            self.assertEqual(contrast["defined_spearman_pairs"], 2)

    def test_all_spearman_undefined_remain_none(self):
        result = summary.aggregate_pairs({p: pair_fixture(spearman=None) for p in ("1-2", "1-3", "2-3")})
        self.assertIsNone(result["contrasts"]["AA-BB"]["spearman"])
        self.assertEqual(result["contrasts"]["AA-BB"]["defined_spearman_pairs"], 0)

    def test_nonfinite_effect_or_non_spearman_contrast_fails(self):
        for field in ("effect", "rank_mad", "top1_flip", "top5_jaccard"):
            with self.subTest(field=field):
                pairs = {p: pair_fixture() for p in ("1-2", "1-3", "2-3")}
                if field == "effect":
                    pairs["1-2"]["aggregate"]["effects"]["feature_mean_abs"] = np.nan
                else:
                    pairs["1-2"]["aggregate"]["contrasts"]["AA-BB"][field] = np.inf
                with self.assertRaises(ValueError):
                    summary.aggregate_pairs(pairs)


class LoadCellTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.root = root
        prepared_dir = root/"compact21_factorial_v1"
        prepared_dir.mkdir()
        self.prepared_path = prepared_dir/"PREPARED_CONTRACT.json"
        prepared = {"training": {f"2017_r{v}": dict(rows=12, matrix_sha256=f"matrix-{v}",
            continuous_labels_sha256=f"continuous-{v}", integer_labels_sha256=f"integer-{v}") for v in (1,2,3)}}
        self.prepared_path.write_text(json.dumps(prepared))
        self.path = root / "RESULT.json"
        self.ref_path = root / "REFERENCE.json"
        self.ref_path.write_text("synthetic reference")
        self.pred_path = root / "PREDICTIONS.parquet"
        self.pred_path.write_bytes(b"synthetic parquet bytes, loader mocked")
        self.p = pd.DataFrame(dict(signal_date=pd.Timestamp("2017-01-31"), ticker=["A","B","C"],
            target_rank_21=[1/3,2/3,1.], exit_date_21=pd.Timestamp("2017-03-02"), target_ret_21=[0.,.01,.02]))
        cells = {}
        for x in (1,2,3):
            for y in (1,2,3):
                name = f"X{x}Y{y}"
                self.p[name] = np.arange(3.) + x*10 + y
                digest = array_hash(self.p[name].to_numpy())
                audit = dict(maturity_PASS=True, cutoff="2017-01-01", max_signal_date="2016-11-30",
                    max_exit_date_21="2016-12-30", prediction_sha256=[digest],
                    train_matrix_sha256=f"matrix-{x}", train_labels_sha256=f"integer-{y}",
                    train_rows=12, feature_names=["synthetic_feature"])
                cells[name] = dict(feature_repeat=x, target_repeat=y, determinism_PASS=True,
                    diagonal_control_PASS=True if x==y else None, prediction_sha256=digest,
                    audit=deepcopy(audit), refit_audit=deepcopy(audit))
        inputs = {str(v): "synthetic-input" for v in (1,2,3)}
        train_keys = {str(v): f"train-keys-{v}" for v in (1,2,3)}
        active = ["SSE","SSE2","SSE3","SSSE3","SSE41","POPCNT","SSE42","AVX","F16C","FMA3","AVX2"]
        inactive = ["AVX512F","AVX512CD","AVX512_KNL","AVX512_KNM","AVX512_SKX","AVX512_CLX","AVX512_CNL","AVX512_ICL","AVX512_SPR"]
        numeric = dict(python="synthetic", machine="synthetic", numpy="2.3.5", pandas="synthetic",
            scipy="synthetic", sklearn="synthetic", execution_env={},
            numpy_build_config={"SIMD Extensions": {"baseline":active[:3],"found":active[3:],"not found":inactive}},
            effective_cpu_features={**{flag:True for flag in active},**{flag:False for flag in inactive}}, threadpools=[])
        self.r = dict(status=summary.LINE+"_COMPLETE", model=summary.MODELS[0], year=2017,
            cells=cells, old_run=37229180477, negative_feedback_changed=False, production_adoption=False,
            prediction_file_sha256=summary.sha(self.pred_path), inference_keys_sha256=summary.keys_hash(self.p),
            reference_sha256=summary.sha(self.ref_path), input_sha256=inputs,
            numeric_contract=deepcopy(numeric), prepared_contract_sha256=summary.sha(self.prepared_path),train_keys_sha256=train_keys)
        common = pd.concat([self.p[summary.KEYS].assign(vintage=v, pred=self.p[f"X{v}Y{v}"].to_numpy())
            for v in (1,2,3)], ignore_index=True)
        native = self.p[summary.KEYS+["target_rank_21","exit_date_21","target_ret_21"]].assign(vintage=2)
        self.ref = dict(path=self.ref_path, result={"input_sha256":inputs,"numeric_contract":deepcopy(numeric),
            "per_year":{"2017":{"evaluation_coverage":{"train_keys_sha256":deepcopy(train_keys)},
                "transforms":{"1":{"feature_names":["synthetic_feature"]}}}}}, common=common, native=native)

    def call_loader(self):
        self.path.write_text(json.dumps(self.r))
        with patch.object(summary.pd, "read_parquet", return_value=self.p.copy()), patch.object(summary,"ROOT",self.root):
            return summary.load_cell(self.path,self.ref)

    def test_valid_synthetic_diagonals_and_cells_load(self):
        r,p = self.call_loader()
        self.assertEqual(r["model"],summary.MODELS[0])
        pd.testing.assert_frame_equal(p,self.p)

    def test_maturity_nat_or_cutoff_boundary_fail(self):
        initial = deepcopy(self.r)
        for field,value in (("max_signal_date","NaT"),("max_exit_date_21","NaT"),
                ("max_signal_date","2017-01-01"),("max_exit_date_21","2017-01-01"),("cutoff","NaT")):
            for which in ("audit","refit_audit"):
                with self.subTest(field=field,which=which,value=value):
                    self.r = deepcopy(initial)
                    self.r["cells"]["X1Y2"][which][field] = value
                    with self.assertRaises(ValueError):
                        self.call_loader()

    def test_feature_label_registry_transposition_fails(self):
        self.r["cells"]["X1Y2"]["feature_repeat"] = 2
        self.r["cells"]["X1Y2"]["target_repeat"] = 1
        with self.assertRaisesRegex(ValueError,"registry"):
            self.call_loader()

    def test_changed_refit_or_retained_prediction_hash_fails(self):
        initial = deepcopy(self.r)
        for field in ("refit","prediction"):
            with self.subTest(field=field):
                self.r = deepcopy(initial)
                if field=="refit":
                    self.r["cells"]["X1Y2"]["refit_audit"]["prediction_sha256"] = ["wrong"]
                else:
                    self.r["cells"]["X1Y2"]["prediction_sha256"] = "wrong"
                with self.assertRaises(ValueError):
                    self.call_loader()

    def test_false_diagonal_control_or_changed_old_diagonal_fails(self):
        self.r["cells"]["X2Y2"]["diagonal_control_PASS"] = False
        with self.assertRaisesRegex(ValueError,"diagonal"):
            self.call_loader()
        self.r["cells"]["X2Y2"]["diagonal_control_PASS"] = True
        self.ref["common"].loc[self.ref["common"].vintage==2,"pred"] += .001
        with self.assertRaisesRegex(ValueError,"diagonal"):
            self.call_loader()

    def test_fixed_repeat2_target_mismatch_fails(self):
        self.ref["native"].loc[0,"target_rank_21"] = .1
        with self.assertRaises(AssertionError):
            self.call_loader()

    def test_wrong_matrix_target_or_feature_registry_fails(self):
        original = deepcopy(self.r)
        for key,value in (("train_matrix_sha256","matrix-2"),("train_labels_sha256","integer-1"),
                ("train_rows",11),("feature_names",["wrong_feature"])):
            with self.subTest(key=key):
                self.r=deepcopy(original)
                self.r["cells"]["X1Y2"]["audit"][key]=value
                with self.assertRaises(ValueError):
                    self.call_loader()

    def test_prepared_registry_native_train_keys_and_numeric_tamper_fail(self):
        original=deepcopy(self.r)
        for which in ("registry","keys","numeric"):
            with self.subTest(which=which):
                self.r=deepcopy(original)
                if which=="registry":
                    self.r["prepared_contract_sha256"]="wrong"
                elif which=="keys":
                    self.r["train_keys_sha256"]["1"]="wrong"
                else:
                    self.r["numeric_contract"]["pandas"]="different"
                with self.assertRaises(ValueError):
                    self.call_loader()

    def test_ridge_requires_continuous_target_donor_hash(self):
        self.r["model"]="RIDGE"
        with self.assertRaisesRegex(ValueError,"donor"):
            self.call_loader()
        for cell in self.r["cells"].values():
            for which in ("audit","refit_audit"):
                cell[which]["train_labels_sha256"]=f"continuous-{cell['target_repeat']}"
        self.call_loader()


class SummaryMappingTests(unittest.TestCase):
    def test_feature_and_label_cells_not_transposed_quality_only_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs, refs, out = root/"inputs",root/"refs",root/"out"
            inputs.mkdir(); refs.mkdir()
            for model in summary.MODELS:
                rd = refs/model; rd.mkdir()
                (rd/"RESULT.json").write_text(json.dumps(dict(variant=model,
                    status="COMPACT21_PREDICTIVE_V2_COMPLETE",files_sha256={})))
                for year in range(2017,2027):
                    jd = inputs/f"{model}-{year}"; jd.mkdir()
                    (jd/"RESULT.json").write_text(json.dumps(dict(line=summary.LINE,model=model,year=year)))
            def fake_load(path,reference):
                original = json.loads(path.read_text())
                r = dict(original, input_sha256={},fit_sources={},factorial_sources={},protocol_sha256="synthetic",
                    prepared_contract_sha256="synthetic",numeric_contract={})
                p = pd.DataFrame(dict(signal_date=pd.Timestamp(original["year"],1,31),ticker=["A","B"],
                    target_rank_21=[.5,1.],exit_date_21=pd.Timestamp(original["year"],3,2),target_ret_21=[0.,.01]))
                for x in (1,2,3):
                    for y in (1,2,3):
                        p[f"X{x}Y{y}"] = [1.,0.] if x>y else [0.,1.]
                return r,p
            retained=[]
            def fake_parquet(frame,path,index=False):
                retained.append(frame.copy())
                Path(path).write_bytes(b"synthetic retained rank vectors")
            with patch.object(summary,"load_cell",side_effect=fake_load), \
                    patch.object(summary,"normalized_numeric",side_effect=lambda x:x), \
                    patch.object(summary.pd,"read_parquet",return_value=pd.DataFrame()), \
                    patch.object(summary,"evaluate",return_value={"diagnostic_only":"fixed_repeat2"}), \
                    patch.object(pd.DataFrame,"to_parquet",new=fake_parquet), redirect_stdout(io.StringIO()):
                summary.summarize(inputs,refs,out)
            result=json.loads((out/"SUMMARY.json").read_text())
            self.assertFalse(result["production_adoption"])
            self.assertNotIn("DEVELOPMENT_CANDIDATE",result)
            self.assertNotIn("gate",result["models"][summary.MODELS[0]])
            self.assertEqual(result["fixed_repeat2_quality"][summary.MODELS[0]]["X1Y2"],{"diagnostic_only":"fixed_repeat2"})
            selected=retained[0]
            selected=selected[(selected.model==summary.MODELS[0])&(selected.pair=="1-2")&(selected.ticker=="A")]
            self.assertTrue(selected.signed_feature.eq(.25).all())
            self.assertTrue(selected.signed_label.eq(-.25).all())
            self.assertTrue(selected.total_rank_change.eq(0.).all())
            model=result["models"][summary.MODELS[0]]["equal_date_equal_pair"]
            self.assertAlmostEqual(model["contrasts"]["AA-BA"]["rank_mad"],.5)
            self.assertAlmostEqual(model["contrasts"]["AA-AB"]["rank_mad"],0.)


if __name__ == "__main__":
    unittest.main()
