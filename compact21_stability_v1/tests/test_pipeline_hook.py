"""Actual-worker integration checks; reduced rounds apply exclusively to tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
import pandas as pd

from compact21_stability_v1.run_full_pipeline import make_compact_hook, transform21
from etf_trader.source_only import kernel, models


def fixture():
    random = np.random.default_rng(501)
    names = ["mom21", "mom21_pct", "mom21_dev"]
    rows = []
    for date in pd.date_range("2015-01-31", periods=20, freq="ME"):
        outcomes = random.normal(0, .05, 9)
        ranks = pd.Series(outcomes).rank(pct=True).to_numpy()
        for j, (outcome, rank) in enumerate(zip(outcomes, ranks)):
            rows.append(dict(signal_date=date, ticker=f"T{j}",
                             exit_date_21=date + pd.Timedelta(days=30),
                             exit_date_63=date + pd.Timedelta(days=90),
                             target_rank_21=rank, target_rank_63=rank, fwd_ret_21=outcome,
                             mom21=random.normal(0, .1), mom21_pct=(j + 1) / 9,
                             mom21_dev=random.normal()))
    frame = pd.DataFrame(rows)
    test = frame.iloc[:9].copy()
    test["signal_date"] = pd.Timestamp("2017-01-31")
    k = SimpleNamespace(F2D_FEATURES=names,
                        COMPACT_PARAMS=dict(kernel.COMPACT_PARAMS, n_estimators=2, min_child_weight=0),
                        COMPACT_SEEDS=list(kernel.COMPACT_SEEDS))
    return k, frame, test, pd.Timestamp("2017-01-01")


class PipelineHookTests(unittest.TestCase):
    def setUp(self):
        self.k, self.frame, self.test, self.cutoff = fixture()
        self.directory = tempfile.TemporaryDirectory(prefix="compact21_hook_test_")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.valid = pd.Series(True, index=self.frame.index)
        # Native worker threads remain exactly the preregistered execution mode.
        self.old_environment = {name: os.environ.get(name) for name in
                                ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
                                 "ETF_TRADER_XGB_THREADS_PER_WORKER", "ETF_TRADER_XGB_WORKERS")}
        os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                          ETF_TRADER_XGB_THREADS_PER_WORKER="1", ETF_TRADER_XGB_WORKERS="3")
        self.addCleanup(self.restore_environment)

    def restore_environment(self):
        for name, value in self.old_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def fit(self, variant, frame=None, name=None):
        frame = self.frame if frame is None else frame
        output = self.root / (name or variant)
        output.mkdir()
        prediction = make_compact_hook(variant, models)(
            self.k, frame, self.test, pd.Series(True, index=frame.index),
            self.cutoff, output, 2017)[0]
        audit = json.loads((output / "stability_transform_2017.json").read_text())
        return prediction, audit

    def test_canonical_prediction_bytes_and_compact63_contract(self):
        canonical = models._fit_compact_rankers_isolated(
            self.k, self.frame, self.test, self.valid, self.cutoff, self.root, 2017)[0]
        for variant in ("BASE", "Q4", "SCALE_ECON1BP"):
            with self.subTest(variant=variant):
                prediction, audit = self.fit(variant)
                self.assertEqual(prediction[63].tobytes(), canonical[63].tobytes())
                if variant == "BASE":
                    self.assertEqual(prediction[21].tobytes(), canonical[21].tobytes())
                self.assertTrue(all(row["maturity_ok"] for row in audit["horizons"].values()))
                self.assertTrue(audit["horizons"]["63"]["canonical63_input_contract"])
                self.assertEqual(audit["seeds"], [101, 202, 303])

    def test_all_intervention_transform_shapes_and_integer_targets(self):
        for variant in ("Q4", "ORDINAL", "ECON1BP", "Q4_ECON1BP", "SCALE", "SCALE_ECON1BP"):
            with self.subTest(variant=variant):
                xtr, xte, y, _ = transform21(self.frame, self.test, self.k.F2D_FEATURES,
                                            variant, self.cutoff)
                self.assertEqual(xtr.shape, (len(self.frame), len(self.k.F2D_FEATURES)))
                self.assertEqual(xte.shape, (len(self.test), len(self.k.F2D_FEATURES)))
                self.assertTrue(np.issubdtype(y.dtype, np.integer))

    def test_future_row_mutation_does_not_change_training_or_predictions(self):
        initial, audit = self.fit("SCALE_ECON1BP", name="before")
        future = self.frame.iloc[:9].copy()
        future["signal_date"] = pd.Timestamp("2018-01-31")
        future["exit_date_21"] = pd.Timestamp("2018-03-01")
        future["exit_date_63"] = pd.Timestamp("2018-05-01")
        # Huge feature and outcome changes are excluded by training maturity;
        # the fixed test panel is held identical to isolate fitting causality.
        future[self.k.F2D_FEATURES] = 1e12
        future["fwd_ret_21"] = np.arange(len(future)) * 1e8
        future["target_rank_21"] = pd.Series(np.arange(len(future))).rank(pct=True).to_numpy()
        altered_frame = pd.concat([self.frame, future], ignore_index=True)
        altered, altered_audit = self.fit("SCALE_ECON1BP", altered_frame, name="after")
        for horizon in (21, 63):
            self.assertEqual(initial[horizon].tobytes(), altered[horizon].tobytes())
            self.assertEqual(audit["horizons"][str(horizon)], altered_audit["horizons"][str(horizon)])

    def test_target_transform_rejects_immature_rows(self):
        immature = self.frame.copy()
        immature.loc[immature.index[0], "exit_date_21"] = self.cutoff
        with self.assertRaisesRegex(ValueError, "Immature"):
            transform21(immature, self.test, self.k.F2D_FEATURES, "SCALE_ECON1BP", self.cutoff)


if __name__ == "__main__":
    unittest.main()
