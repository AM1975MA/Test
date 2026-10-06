"""Query-weight reproduction, cohort immutability and isolated worker controls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from compact21_blockbag_v1 import run


class QueryTests(unittest.TestCase):
    def test_exact_frozen_draw_and_no_circular_wrap(self):
        n=11; year=2020
        got=run.query_weights(n,year)
        for b in range(4):
            rng=np.random.default_rng(np.random.SeedSequence([20261005,year,b]))
            starts=rng.integers(0,n-2,size=4)
            rows=np.concatenate([np.arange(s,s+3) for s in starts])[:n]
            np.testing.assert_array_equal(got[b],np.bincount(rows,minlength=n))
        self.assertEqual(got.dtype,np.float64)
        np.testing.assert_array_equal(got.sum(axis=1),[n]*4)
        self.assertTrue((got==0).any())
        self.assertFalse(np.array_equal(got,run.query_weights(n,2021)))
        np.testing.assert_array_equal(got,run.query_weights(n,year))

    def test_minimum_cohort(self):
        with self.assertRaises(ValueError): run.query_weights(2,2020)
        np.testing.assert_array_equal(run.query_weights(3,2020),np.ones((4,3)))

    def test_aggregate_identical_float32_vectors_is_byte_exact(self):
        values=np.random.default_rng(88).normal(size=4096).astype(np.float32)
        self.assertEqual(run.aggregate_bags([values]*4).tobytes(),values.tobytes())
        inputs=np.random.default_rng(89).normal(size=(4,4096)).astype(np.float32)
        expected=inputs.astype(np.float64).mean(axis=0).astype(np.float32)
        self.assertEqual(run.aggregate_bags(inputs).tobytes(),expected.tobytes())

    def test_calendar_gap_cannot_be_used_as_consecutive_block(self):
        frame=pd.DataFrame({"signal_date":pd.to_datetime(["2010-01-31","2010-02-28","2010-04-30"]),"ticker":["A"]*3})
        with self.assertRaisesRegex(ValueError,"calendar gap"):
            run.query_contract({i:frame.copy() for i in (1,2,3)},2020)

    def test_shared_query_contract_rejects_different_keys(self):
        frame=pd.DataFrame({"signal_date":np.repeat(pd.date_range("2010-01-31",periods=5,freq="ME"),2),"ticker":["A","B"]*5})
        trains={i:frame.copy() for i in (1,2,3)}
        dates,groups,weights,a=run.query_contract(trains,2020)
        self.assertEqual(weights.shape,(4,5))
        np.testing.assert_array_equal(groups,[2]*5)
        self.assertTrue(a["same_keys_all_vintages"])
        trains[3].loc[0,"ticker"]="Z"
        with self.assertRaises(AssertionError): run.query_contract(trains,2020)

    def test_nested_aggregation_preserves_seed_then_bag_order(self):
        def fit(train,tests,year,tmp,tag,w):
            b=int(tag[-1]); p=[np.array([b+.25],dtype=np.float32)]
            return p,{"group_weights_sha256":str(b),"model_params":{},"prediction_sha256":[str(b)],"seed_prediction_sha256":{}},None,1.
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.object(run,"weighted_fit",side_effect=fit):
            p,a,seconds=run.ensemble_fit(None,[None],2020,Path(td),"dummy",np.ones((4,3)))
        np.testing.assert_array_equal(p[0],np.array([1.75],dtype=np.float32))
        self.assertEqual(len(a["bags"]),4)
        self.assertEqual(seconds,4.)

    def test_allones_control_fails_closed_on_audit_tamper(self):
        frame=pd.DataFrame({"signal_date":[pd.Timestamp("2010-01-31")],"ticker":["A"]})
        trains={i:frame for i in (1,2,3)}
        ref={"per_year":{"2020":{"transforms":{str(i):{"prediction_sha256":["old"]} for i in (1,2,3)}}}}
        with patch.object(run,"weighted_fit",return_value=([np.array([1.]),np.array([1.])],{"prediction_sha256":["wrong"],"group_weights_sha256":"w"},None,0)):
            with self.assertRaisesRegex(ValueError,"complete audit"):
                run.weighted_controls(trains,trains,frame,2020,ref,None,None,None)


class WorkerTests(unittest.TestCase):
    def test_small_synthetic_allones_is_canonical_and_zeros_allowed(self):
        rng=np.random.default_rng(7)
        X=rng.normal(size=(24,4)).astype(np.float64)
        y=np.tile(np.arange(6),4); groups=np.full(4,6,dtype=np.int64)
        Xte=rng.normal(size=(8,4)).astype(np.float64)
        params={"objective":"rank:ndcg","tree_method":"hist","max_depth":2,"eta":.1,"subsample":.85,"colsample_bytree":.8}
        worker=ROOT/"compact21_blockbag_v1/weighted_worker.py"
        canonical=ROOT/"vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py"
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            d=Path(td)
            outputs=[]
            for label,path,weights in (("canonical",canonical,None),("ones",worker,np.ones(4)),("zeros",worker,np.array([0.,2.,0.,2.]))):
                kwargs={"Xtr":X,"Xte":Xte,"y":y,"groups":groups}
                if weights is not None: kwargs["group_weights"]=weights
                np.savez(d/f"{label}.npz",**kwargs)
                out=d/f"{label}.npy"
                subprocess.run([sys.executable,str(path),"--data",str(d/f"{label}.npz"),"--seed","101","--threads","1","--rounds","8","--params-json",json.dumps(params),"--output",str(out)],check=True,capture_output=True,text=True)
                outputs.append(np.load(out))
            self.assertEqual(outputs[0].dtype,outputs[1].dtype)
            self.assertEqual(outputs[0].tobytes(),outputs[1].tobytes())
            self.assertTrue(np.isfinite(outputs[2]).all())
            self.assertNotEqual(outputs[0].tobytes(),outputs[2].tobytes())

    def test_invalid_row_weights_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            d=Path(td); np.savez(d/"bad.npz",Xtr=np.ones((6,2)),Xte=np.ones((2,2)),y=np.tile([0,1,2],2),groups=np.array([3,3]),group_weights=np.ones(6))
            p=subprocess.run([sys.executable,str(ROOT/"compact21_blockbag_v1/weighted_worker.py"),"--data",str(d/"bad.npz"),"--seed","101","--threads","1","--rounds","1","--params-json",json.dumps({"objective":"rank:ndcg","tree_method":"hist"}),"--output",str(d/"out.npy")],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("Invalid ranking-query weights",p.stderr)


if __name__=="__main__": unittest.main()
