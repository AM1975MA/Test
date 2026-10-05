"""Synthetic formula, isolation and fail-closed retained-control tests; no actual fits."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from compact21_semidev_v1 import run as r
from compact21_semidev_v1 import view as v


def fixture():
    rng = np.random.default_rng(1405)
    index = pd.bdate_range("2015-01-02", periods=520)
    close = pd.DataFrame(100*np.exp(np.cumsum(rng.normal(0,.01,(len(index),3)),axis=0)),
                         index=index,columns=["A","B","C"])
    dates = r.k.month_end_dates(index)
    keys = pd.MultiIndex.from_product([dates, close.columns], names=r.KEYS).to_frame(index=False)
    original = pd.DataFrame(rng.normal(size=(len(keys),125)),columns=r.k.F2D_FEATURES)
    original[r.KEYS] = keys
    original["exit_date_21"] = original.signal_date+pd.Timedelta(days=40)
    original["target_rank_21"] = np.tile([1/3,2/3,1.],len(dates))
    original["fwd_ret_21"] = rng.normal(size=len(keys))
    return original, close


class ViewTests(unittest.TestCase):
    def test_negative_count_crossing_is_finite_and_direct_formula(self):
        for h in (21,63,126):
            minimum = max(10,h//2)
            for probe in (-1e-8,0.,1e-8):
                returns = np.zeros(h); returns[:minimum-1]=-.01;returns[-1]=probe
                got = v.semideviation(pd.DataFrame({"x":returns}),h).iloc[-1,0]
                direct = np.sqrt(np.mean(np.minimum(returns,0)**2))*np.sqrt(252)
                self.assertTrue(np.isfinite(got));self.assertAlmostEqual(got,direct,places=14)
            zeros = v.semideviation(pd.DataFrame({"x":np.ones(h)*.01}),h).iloc[-1,0]
            self.assertEqual(zeros,0.)

    def test_nonfinite_returns_never_count_as_zero_coverage(self):
        for h in (21,63,126):
            minimum=max(10,h//2)
            x=np.full(h,np.nan);x[:minimum-1]=-.01;x[-1]=np.inf
            self.assertTrue(np.isnan(v.semideviation(pd.DataFrame({"x":x}),h).iloc[-1,0]))
            x[-1]=-np.inf
            self.assertTrue(np.isnan(v.semideviation(pd.DataFrame({"x":x}),h).iloc[-1,0]))
            x[-1]=0.
            self.assertTrue(np.isfinite(v.semideviation(pd.DataFrame({"x":x}),h).iloc[-1,0]))

    def test_only_nine_fields_change_and_transfer_preserves_original_cohorts(self):
        original,close=fixture();new,audit=v.align_view(original,close)
        keep=[c for c in original if c not in v.CHANGED]
        pd.testing.assert_frame_equal(original[keep],new[keep],check_exact=True)
        self.assertEqual(audit["preserved_features"],116)
        rows=original.iloc[[25,9,0,14]].copy()
        shifted=v.transfer_rows(rows,new)
        pd.testing.assert_frame_equal(rows[keep],shifted[keep],check_exact=True)
        self.assertEqual(shifted.index.tolist(),rows.index.tolist())
        for c in v.CHANGED:
            np.testing.assert_array_equal(shifted[c],new.loc[rows.index,c])

    def test_future_prices_do_not_alter_past_family(self):
        _,close=fixture();cutoff=pd.Timestamp("2016-01-01")
        future=close.copy();future.loc[future.index>=cutoff]*=3
        a=v.build_family(close);b=v.build_family(future)
        for feature in v.CHANGED:
            pd.testing.assert_frame_equal(a[feature].loc[a[feature].index<cutoff],
                                          b[feature].loc[b[feature].index<cutoff],check_exact=True)

    def test_unidentified_populations_and_keys_fail(self):
        original,close=fixture()
        with self.assertRaises(ValueError):v.align_view(original,close.drop(columns="C"))
        wrong=original.copy();wrong.loc[0,"signal_date"]=pd.Timestamp("2015-01-15")
        with self.assertRaises(ValueError):v.align_view(wrong,close)
        with self.assertRaises(ValueError):v.transfer_rows(original,pd.concat([original,original.iloc[:1]]))
        with tempfile.TemporaryDirectory() as td:
            raw=Path(td);(raw/"INPUT_CONTRACT.json").write_text('{"raw_files_sha256":{"A.csv":"wrong"}}')
            with self.assertRaises(ValueError):v.from_frozen_raw(original,raw,raw/"INPUT_CONTRACT.json")

    def test_original_reconstruction_bounds_are_distinct_from_score_byte_gates(self):
        original,close=fixture()
        dates=r.k.month_end_dates(close.index);lr=np.log(close).diff()
        rows=dates.get_indexer(original.signal_date);cols=close.columns.get_indexer(original.ticker)
        for h in (21,63,126):
            base=r.k.rolling_downvol(lr,h).reindex(dates)
            for suffix,field in (("",base),("_pct",r.k.cs_pct(base)),("_dev",r.k.cs_robust_dev(base))):
                original[f"downvol{h}{suffix}"]=field.to_numpy()[rows,cols]
        checks=v.original_reconstruction_audit(original,close)["checks"]
        self.assertEqual(checks["downvol21"]["absolute_tolerance"],1e-12)
        self.assertEqual(checks["downvol21_pct"]["absolute_tolerance"],0.)
        self.assertEqual(checks["downvol21_dev"]["absolute_tolerance"],1e-10)
        self.assertTrue(checks["downvol21_pct"]["finite_values_bit_exact_claimed"])
        finite_index=np.flatnonzero(original.downvol21_pct.notna())[0]
        altered=original.copy();altered.loc[finite_index,"downvol21_pct"]=np.nextafter(altered.loc[finite_index,"downvol21_pct"],np.inf)
        with self.assertRaisesRegex(ValueError,"finite reconstruction"):
            v.original_reconstruction_audit(altered,close)
        dev_index=np.flatnonzero(original.downvol21_dev.notna())[0]
        altered=original.copy();altered.loc[dev_index,"downvol21_dev"]+=5e-11
        self.assertTrue(v.original_reconstruction_audit(altered,close)["PASS"])
        altered.loc[dev_index,"downvol21_dev"]+=2e-10
        with self.assertRaisesRegex(ValueError,"finite reconstruction"):
            v.original_reconstruction_audit(altered,close)
        altered=original.copy();altered.loc[finite_index,"downvol21"]=np.nan
        with self.assertRaisesRegex(ValueError,"missingness"):
            v.original_reconstruction_audit(altered,close)


class ControlTests(unittest.TestCase):
    def setUp(self):
        original,_=fixture()
        self.year=2016
        frames={i:original.copy() for i in (1,2,3)}
        self.tr,self.te,self.common=r.select_original_frames(frames,self.year)
        self.p={i:[np.linspace(0,1,len(self.common)),np.linspace(0,1,len(self.te[i]))] for i in frames}
        self.audit={"train_matrix_sha256":"x","train_labels_sha256":"y","train_groups_sha256":"g",
                    "test_matrix_sha256":["c","n"],"prediction_sha256":["pc","pn"],"learned_state_hashes":{}}
        self.native=pd.concat([r.predictions_frame(self.te[i],self.p[i][1],i) for i in frames],ignore_index=True)
        self.common_reference=pd.concat([self.common[r.KEYS].assign(pred=self.p[i][0],vintage=i) for i in frames],ignore_index=True)
        self.reference={"per_year":{str(self.year):{"transforms":{str(i):dict(self.audit) for i in frames},
            "evaluation_coverage":r.evaluation_coverage(self.tr,self.te,self.common)}}}
        self.calls=[]

    def mocked_fit(self,train,tests,variant,year,tmp,tag):
        self.calls.append(tag)
        i=int(tag.rsplit("_",1)[1])
        return self.p[i],dict(self.audit),train.target_rank_21.to_numpy(),0.

    def test_complete_retained_control_gate_pass_without_real_fit(self):
        with patch.object(r.learners,"fit",side_effect=self.mocked_fit):
            controls,audits,native,common=r.original_controls(self.tr,self.te,self.common,self.year,
                self.reference,self.native,self.common_reference,Path("unused"))
        self.assertEqual(len(self.calls),3)
        self.assertTrue(all(c["metadata_exact"] for c in controls.values()))
        pd.testing.assert_frame_equal(native,self.native,check_exact=True)
        pd.testing.assert_frame_equal(common,self.common_reference,check_exact=True)

    def test_one_ulp_reference_change_blocks_before_remaining_fits(self):
        changed=self.native.copy();idx=changed.index[changed.vintage.eq(2)][0]
        changed.loc[idx,"pred"]=np.nextafter(changed.loc[idx,"pred"],np.inf)
        with patch.object(r.learners,"fit",side_effect=self.mocked_fit),self.assertRaisesRegex(ValueError,"bytes"):
            r.original_controls(self.tr,self.te,self.common,self.year,self.reference,changed,self.common_reference,Path("unused"))
        self.assertEqual(len(self.calls),2)

    def test_changed_metadata_blocks_even_when_score_bytes_equal(self):
        self.reference["per_year"][str(self.year)]["transforms"]["1"]["unexpected_field"]=True
        with patch.object(r.learners,"fit",side_effect=self.mocked_fit),self.assertRaisesRegex(ValueError,"complete learned audit"):
            r.original_controls(self.tr,self.te,self.common,self.year,self.reference,self.native,self.common_reference,Path("unused"))
        self.assertEqual(len(self.calls),1)

    def test_source_parity_gate_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"source changed"):
            r.source_gate({"sources":{}})


if __name__=="__main__":unittest.main()
