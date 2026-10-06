"""Acceptance logic and date-weighted stability tests, independent of learners."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]
from compact21_predictive_v2 import summarize as summary


def stability_fixture(rank_mad, disagreement):
    values = {"rank_mad": rank_mad, "top1_disagreement": disagreement, "top5_jaccard": .8}
    return {"mean": deepcopy(values), "pairs": {p: {"mean": deepcopy(values)} for p in ("1-2", "1-3", "2-3")}}


def gate_fixture():
    def quality(percentile, overlap):
        return {"eval": {"per_date": [
            {"vintage": str(v), "signal_date": date, "top1_realized_percentile": percentile}
            for v in (1, 2, 3) for date in ("2020-01-31", "2020-02-29")],
            "aggregate_by_date": {"top5_overlap": overlap}}}
    return dict(candidate=quality(.65, .15), base=quality(.6, .1),
        paired={"difference": {"top1_realized_percentile": .05},
            "bootstrap": {"3": {"intervals_95pct": {"top1_realized_percentile": {"lower98_75_one_sided": .01}}}}},
        common=stability_fixture(.02, .2), native=stability_fixture(.02, .15),
        bc=stability_fixture(.04, .3), bn=stability_fixture(.04, .3), controls_pass=True)


def stability_panel():
    records = []
    for date, count in (("2020-01-31", 2), ("2020-02-29", 10)):
        for vintage in (1, 2, 3):
            for ticker in range(count):
                prediction = float(ticker)
                if count == 2 and vintage == 2:
                    prediction = -prediction
                records.append(dict(signal_date=pd.Timestamp(date), vintage=vintage,
                    ticker=f"T{ticker:02d}", pred=prediction))
    return pd.DataFrame(records)


class SummaryGateTests(unittest.TestCase):
    def test_positive_primary_and_positive_familywise_lower_pass(self):
        result = summary.gate(**gate_fixture())
        self.assertTrue(result["DEVELOPMENT_CANDIDATE"])
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["production_adoption"])

    def test_zero_or_negative_primary_cannot_pass_positive_ci(self):
        for effect in (0., -.001):
            with self.subTest(effect=effect):
                args = gate_fixture()
                args["paired"]["difference"]["top1_realized_percentile"] = effect
                result = summary.gate(**args)
                self.assertFalse(result["checks"]["primary_positive"])
                self.assertFalse(result["DEVELOPMENT_CANDIDATE"])

    def test_zero_negative_or_missing_ci_cannot_pass_positive_mean(self):
        for lower in (0., -.001, None):
            with self.subTest(lower=lower):
                args = gate_fixture()
                intervals = args["paired"]["bootstrap"]["3"]["intervals_95pct"]
                intervals["top1_realized_percentile"] = None if lower is None else {"lower98_75_one_sided": lower}
                result = summary.gate(**args)
                self.assertFalse(result["checks"]["primary_familywise_lower_positive"])
                self.assertFalse(result["DEVELOPMENT_CANDIDATE"])

    def test_failed_control_blocks_even_large_quality_and_extra_cagr(self):
        args = gate_fixture()
        args["controls_pass"] = False
        args["paired"]["difference"]["top1_realized_percentile"] = .4
        args["paired"]["bootstrap"]["3"]["intervals_95pct"]["top1_realized_percentile"]["lower98_75_one_sided"] = .3
        args["candidate"]["cagr"] = 999.
        result = summary.gate(**args)
        self.assertFalse(result["checks"]["all_controls_reproduced"])
        self.assertFalse(result["DEVELOPMENT_CANDIDATE"])
        self.assertFalse(result["production_adoption"])

    def test_one_native_pair_worse_blocks_even_aggregate_reduction_passes(self):
        args = gate_fixture()
        pairs = args["native"]["pairs"]
        pairs["1-2"]["mean"]["top1_disagreement"] = .31
        pairs["1-3"]["mean"]["top1_disagreement"] = .1
        pairs["2-3"]["mean"]["top1_disagreement"] = .1
        args["native"]["mean"]["top1_disagreement"] = (.31+.1+.1)/3
        result = summary.gate(**args)
        self.assertTrue(result["checks"]["native_top1_disagreement_reduced_ge25pct"])
        self.assertFalse(result["checks"]["each_native_pair_top1_not_worse"])
        self.assertFalse(result["DEVELOPMENT_CANDIDATE"])

    def test_one_common_pair_worse_blocks_even_aggregate_reduction_passes(self):
        args = gate_fixture()
        pairs = args["common"]["pairs"]
        pairs["1-2"]["mean"]["rank_mad"] = .05
        pairs["1-3"]["mean"]["rank_mad"] = .01
        pairs["2-3"]["mean"]["rank_mad"] = .01
        args["common"]["mean"]["rank_mad"] = (.05+.01+.01)/3
        result = summary.gate(**args)
        self.assertTrue(result["checks"]["common_rank_mad_reduced_ge25pct"])
        self.assertFalse(result["checks"]["each_common_pair_mad_not_worse"])
        self.assertFalse(result["DEVELOPMENT_CANDIDATE"])

    def test_one_vintage_worse_blocks_positive_overall_effect(self):
        args = gate_fixture()
        for record in args["candidate"]["eval"]["per_date"]:
            record["top1_realized_percentile"] = .59 if record["vintage"] == "1" else .8
        result = summary.gate(**args)
        self.assertFalse(result["vintage_checks"]["1"])
        self.assertTrue(result["vintage_checks"]["2"])
        self.assertFalse(result["checks"]["primary_each_vintage_not_worse"])
        self.assertFalse(result["DEVELOPMENT_CANDIDATE"])

    def test_top5_worse_blocks_top1_improvement(self):
        args = gate_fixture()
        args["candidate"]["eval"]["aggregate_by_date"]["top5_overlap"] = .099
        result = summary.gate(**args)
        self.assertTrue(result["checks"]["primary_positive"])
        self.assertFalse(result["checks"]["top5_precision_not_worse"])
        self.assertFalse(result["DEVELOPMENT_CANDIDATE"])

    def test_reduction_zero_denominator_and_exact_boundary(self):
        self.assertTrue(summary.reduction_gate(0., 0.))
        self.assertFalse(summary.reduction_gate(.000001, 0.))
        self.assertTrue(summary.reduction_gate(.3, .4))
        self.assertFalse(summary.reduction_gate(.300001, .4))


class StabilityTests(unittest.TestCase):
    def test_dates_are_equal_weighted_even_when_universe_size_changes(self):
        result = summary.stability_by_date(stability_panel())
        pair = result["pairs"]["1-2"]
        self.assertAlmostEqual(pair["dates"][0]["rank_mad"], .5)
        self.assertAlmostEqual(pair["dates"][1]["rank_mad"], 0.)
        self.assertAlmostEqual(pair["mean"]["rank_mad"], .25)
        self.assertNotAlmostEqual(pair["mean"]["rank_mad"], 1/12)
        self.assertAlmostEqual(pair["mean"]["top1_disagreement"], .5)
        self.assertAlmostEqual(result["mean"]["rank_mad"], 1/6)
        self.assertEqual(pair["coverage"]["aligned_rows"], 12)

    def test_ties_and_top5_boundary_use_ticker_order_independent_of_rows(self):
        f = stability_panel()
        f["pred"] = 1.
        a = summary.stability_by_date(f)
        b = summary.stability_by_date(f.sample(frac=1, random_state=21))
        self.assertEqual(a, b)
        self.assertEqual(a["mean"]["rank_mad"], 0.)
        self.assertEqual(a["mean"]["top1_disagreement"], 0.)
        self.assertEqual(a["mean"]["top5_jaccard"], 1.)
        for pair in a["pairs"].values():
            self.assertEqual(pair["dates"][1]["top1_a"], "T00")

    def test_missing_rows_fail_stability_coverage(self):
        f = stability_panel()
        keep = ~((f.vintage == 2) & (f.ticker == "T09"))
        with self.assertRaises(ValueError):
            summary.stability_by_date(f.loc[keep])

    def test_duplicate_nonfinite_or_empty_pair_fails(self):
        f = stability_panel()
        invalid = [pd.concat([f, f.iloc[[0]]], ignore_index=True),
            f.assign(pred=np.inf), f[f.vintage != 3]]
        for case in invalid:
            with self.subTest(rows=len(case)):
                with self.assertRaises(ValueError):
                    summary.stability_by_date(case)


if __name__ == "__main__":
    unittest.main()
