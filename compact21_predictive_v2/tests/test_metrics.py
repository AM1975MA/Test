import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import unittest

spec = importlib.util.spec_from_file_location("predictive_metrics", Path(__file__).parents[1] / "metrics.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def panel(months=12, vintages=1):
    rows = []
    for date in pd.date_range("2020-01-31", periods=months, freq="ME"):
        for v in range(vintages):
            for t in range(10):
                rows.append(dict(signal_date=date, vintage=str(v), ticker=f"T{t:02d}",
                    target_rank_21=(t+1)/10, pred=float(t), target_ret_21=t/100,
                    exit_date_21=date + pd.Timedelta(days=30)))
    return pd.DataFrame(rows)


class MetricsTests(unittest.TestCase):
    def test_perfect_and_reversed_selection_regret_and_chance(self):
        f = panel()
        perfect = metrics.evaluate(f)
        assert perfect["aggregate"]["ndcg5"] == 1
        assert perfect["aggregate"]["top1_hit_exact"] == 1
        assert perfect["aggregate"]["top1_return_regret"] == 0
        self.assertAlmostEqual(perfect["aggregate"]["random_top1_hit_exact"], .1)
        self.assertAlmostEqual(perfect["aggregate"]["random_top1_realized_percentile"], .55)
        f["pred"] *= -1
        reverse = metrics.evaluate(f)
        self.assertAlmostEqual(reverse["aggregate"]["top1_realized_percentile"], .1)
        assert reverse["aggregate"]["top5_overlap"] == 0
        self.assertAlmostEqual(reverse["aggregate"]["rank_ic"], -1)
        self.assertAlmostEqual(reverse["aggregate"]["top1_return_regret"], .09)


    def test_ties_are_ticker_deterministic_and_row_order_invariant(self):
        f = panel(1)
        f["pred"] = 1.
        first = metrics.evaluate(f)["per_date"][0]
        second = metrics.evaluate(f.sample(frac=1, random_state=8))["per_date"][0]
        assert first == second
        assert first["selected_ticker"] == "T00"
        assert first["rank_ic"] is None
        assert first["top1_realized_percentile"] == .1
        assert first["prediction_tied_rows"] == 10
        assert first["pred_top1_tie_count"] == 10
        assert first["pred_top5_boundary_tie_count"] == 10
        assert first["target_topdecile_boundary_tie_count"] == 1


    def test_maturity_uses_exits_but_validates_all_predictions(self):
        f = panel(2)
        late = f.signal_date == f.signal_date.max()
        f.loc[late, "target_rank_21"] = np.nan
        f.loc[late, "target_ret_21"] = np.nan
        result = metrics.evaluate(f, "2020-03-01")
        assert result["coverage"]["mature_rows"] == 10
        assert result["coverage"]["immature_rows"] == 10
        f.loc[late, "pred"] = np.nan
        with self.assertRaisesRegex(ValueError, "Nonfinite predictions"):
            metrics.evaluate(f, "2020-03-01")


    def test_partial_maturity_and_invalid_temporal_exit_fail(self):
        f = panel(1)
        f.loc[0, "exit_date_21"] = pd.Timestamp("2020-04-01")
        with self.assertRaisesRegex(ValueError, "Partially mature"):
            metrics.evaluate(f, "2020-03-01")
        f.loc[0, "exit_date_21"] = f.loc[0, "signal_date"]
        with self.assertRaisesRegex(ValueError, "Exit must follow"):
            metrics.evaluate(f, "2020-03-01")


    def test_strict_inference_and_target_coverage(self):
        for kind in ("duplicate", "missing", "nonfinite", "target"):
            with self.subTest(kind=kind):
                f = panel(1)
                expected = f[metrics.KEYS].copy()
                if kind == "duplicate":
                    f = pd.concat([f, f.iloc[[0]]])
                elif kind == "missing":
                    f = f.iloc[1:]
                elif kind == "nonfinite":
                    f.loc[0, "pred"] = np.inf
                else:
                    f.loc[0, "target_rank_21"] = 1.1
                with self.assertRaises(ValueError):
                    metrics.evaluate(f, expected_keys=expected)

    def test_vintage_replication_does_not_inflate_bootstrap_sample_size(self):
        base = panel(12)
        candidate = base.copy()
        candidate["pred"] *= -1
        one = metrics.paired_compare(metrics.evaluate(candidate), metrics.evaluate(base), n_bootstrap=100)
        # Replicating the very same history three times cannot change interval.
        base3 = pd.concat([base.assign(vintage=str(v)) for v in range(3)], ignore_index=True)
        cand3 = pd.concat([candidate.assign(vintage=str(v)) for v in range(3)], ignore_index=True)
        three = metrics.paired_compare(metrics.evaluate(cand3), metrics.evaluate(base3), n_bootstrap=100)
        assert one["paired_dates"] == three["paired_dates"] == 12
        assert one["bootstrap"] == three["bootstrap"]
        self.assertAlmostEqual(three["difference"]["top1_realized_percentile"], -.9)


    def test_bootstrap_reproducible_and_date_effects_shared_across_vintages(self):
        base = panel(18, 3)
        candidate = base.copy()
        mask = candidate.signal_date.dt.month % 2 == 0
        candidate.loc[mask, "pred"] *= -1
        ca, ba = metrics.evaluate(candidate), metrics.evaluate(base)
        a = metrics.paired_compare(ca, ba, n_bootstrap=200)
        b = metrics.paired_compare(ca, ba, n_bootstrap=200)
        assert a == b
        interval = a["bootstrap"]["3"]["intervals_95pct"]["top1_realized_percentile"]
        assert interval["lower"] <= a["difference"]["top1_realized_percentile"] <= interval["upper"]
        assert a["defined_paired_date_counts"]["top1_realized_percentile"] == 18


    def test_pairing_rejects_different_target_or_coverage(self):
        base = metrics.evaluate(panel())
        changed = panel()
        changed.loc[0, "target_rank_21"] = .11
        with self.assertRaisesRegex(ValueError, "target/cohort mismatch"):
            metrics.paired_compare(metrics.evaluate(changed), base, n_bootstrap=100)
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            metrics.paired_compare(metrics.evaluate(panel(11)), base, n_bootstrap=100)


    def test_undefined_ic_is_reported_and_optional_returns_not_fabricated(self):
        f = panel().drop(columns="target_ret_21")
        f["pred"] = 1.
        evaluation = metrics.evaluate(f)
        assert evaluation["aggregate"]["top1_return_regret"] is None
        assert evaluation["per_year"][0]["defined_date_counts"]["rank_ic"] == 0
        paired = metrics.paired_compare(evaluation, evaluation, n_bootstrap=100)
        assert paired["bootstrap"]["3"]["intervals_95pct"]["rank_ic"] is None


    def test_annual_weighting_distinct_from_date_weighting(self):
        f = panel(13)
        f.loc[f.signal_date.dt.year == 2021, "pred"] *= -1
        ev = metrics.evaluate(f)
        self.assertAlmostEqual(ev["aggregate"]["top1_realized_percentile"], .55)
        self.assertAlmostEqual(ev["aggregate_by_date"]["top1_realized_percentile"], 12.1/13)


    def test_future_label_values_cannot_change_mature_quality(self):
        f = panel(2)
        initial = metrics.evaluate(f, "2020-03-01")
        future = f.signal_date == f.signal_date.max()
        f.loc[future, "target_rank_21"] = np.inf
        f.loc[future, "target_ret_21"] = -np.inf
        assert metrics.evaluate(f, "2020-03-01") == initial

    def test_topdecile_mean_regret_can_be_negative_for_true_winner(self):
        f = panel(1)
        f = pd.concat([f.assign(ticker="A"+f.ticker), f.assign(ticker="B"+f.ticker)], ignore_index=True)
        # Two highest ranked targets; selected AT09 has better raw return.
        f.loc[f.ticker == "BT09", "target_ret_21"] = .08
        result = metrics.evaluate(f)["per_date"][0]
        assert result["top1_return_regret"] == 0
        self.assertAlmostEqual(result["top1_return_regret_vs_topdecile_mean"], -.005)
        assert result["target_top1_tie_count"] == 2


    def test_paired_returns_availability_and_value_mismatches_fail(self):
        baseline = metrics.evaluate(panel())
        no_returns = metrics.evaluate(panel().drop(columns="target_ret_21"))
        with self.assertRaisesRegex(ValueError, "availability mismatch"):
            metrics.paired_compare(no_returns, baseline, n_bootstrap=100)
        changed = panel()
        changed.loc[0, "target_ret_21"] += .01
        with self.assertRaisesRegex(ValueError, "realized return targets differ"):
            metrics.paired_compare(metrics.evaluate(changed), baseline, n_bootstrap=100)


    def test_bootstrap_invalid_configuration_and_short_history_fail(self):
        ev = metrics.evaluate(panel(2))
        with self.assertRaisesRegex(ValueError, "shorter"):
            metrics.paired_compare(ev, ev, n_bootstrap=100)
        with self.assertRaisesRegex(ValueError, "Invalid bootstrap"):
            metrics.paired_compare(ev, ev, n_bootstrap=99)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            metrics.paired_compare(ev, ev, block_lengths=(1, 1), n_bootstrap=100)


if __name__ == "__main__":
    unittest.main()
