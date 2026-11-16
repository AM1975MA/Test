"""Independent accounting/date-boundary tests for the results-only audit."""
from pathlib import Path
import importlib.util
import unittest

import numpy as np
import pandas as pd


MODULE = Path(__file__).resolve().parents[1] / "src" / "analyze_results.py"


class ResultMetricTests(unittest.TestCase):
    def load(self):
        self.assertTrue(MODULE.is_file(), "Independent results audit has not been implemented")
        spec = importlib.util.spec_from_file_location("result_audit_under_test", MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def daily(self, dates, close, open_nav=None, gross=None, start=0):
        close = np.asarray(close, float)
        gross = np.ones(len(close)) if gross is None else np.asarray(gross, float)
        return pd.DataFrame(dict(date=pd.DatetimeIndex(dates).strftime("%Y-%m-%d"),
            k=np.arange(start, start+len(close)), nav_open=close if open_nav is None else open_nav,
            nav_close=close, cash=close*(1-gross), gross=gross,
            positions=(gross > 1e-8).astype(int)))

    def test_common_postwarmup_uses_actual_preceding_close(self):
        # Resetting to initial capital or dropping the first postwarmup return fails.
        daily = self.daily(pd.bdate_range("2024-03-01", periods=4), [100, 110, 121, 108.9], start=100)
        out = self.load().performance_window(daily, start_idx=102, initial_nav=100)
        self.assertEqual(out["initial_nav"], 110)
        self.assertEqual(out["anchor_date"], "2024-03-04")
        self.assertAlmostEqual(out["cumulative"], -0.01)
        self.assertEqual(out["sessions"], 2)

    def test_sampled_drawdown_includes_pre_fee_mark_and_correct_recovery(self):
        # Close-only metrics miss the -30% opening loss; recovery is not the trough.
        daily = self.daily(pd.bdate_range("2024-01-08", periods=4), [100, 90, 100, 110], [100, 70, 90, 100])
        out = self.load().performance_window(daily, initial_nav=100)
        self.assertAlmostEqual(out["maxdd_close"], -0.1)
        self.assertAlmostEqual(out["maxdd_sampled"], -0.3)
        episode = out["worst_drawdown"]
        self.assertEqual(episode["peak_date"], "2024-01-08")
        self.assertEqual(episode["trough_date"], "2024-01-09")
        self.assertEqual(episode["trough_sample"], "PRE_FEES")
        self.assertEqual(episode["recovery_date"], "2024-01-10")
        self.assertEqual(episode["recovery_sample"], "CLOSE")

    def test_unrecovered_drawdown_is_right_censored(self):
        daily = self.daily(pd.bdate_range("2024-01-08", periods=3), [120, 80, 90])
        out = self.load().performance_window(daily, initial_nav=100)
        self.assertAlmostEqual(out["maxdd_sampled"], -1/3)
        self.assertIsNone(out["worst_drawdown"]["recovery_date"])
        self.assertFalse(out["worst_drawdown"]["recovered"])

    def test_calendar_cagr_matches_declared_native_inclusive_window(self):
        daily = self.daily(["2024-01-05", "2024-01-08"], [100, 110])
        out = self.load().performance_window(daily, initial_nav=100)
        self.assertEqual(out["days"], 4)
        self.assertAlmostEqual(out["cagr"], 1.1**(365.2425/4)-1)

    def test_cash_spells_include_calendar_gap_and_expose_right_censoring(self):
        daily = self.daily(["2024-01-05", "2024-01-08", "2024-01-09", "2024-01-10"],
                           [100]*4, gross=[0, 0, 1, 0])
        spells = self.load().cash_spells(daily)
        self.assertEqual(spells[0]["cash_sessions"], 2)
        self.assertEqual(spells[0]["calendar_days_until_next_invested_close"], 4)
        self.assertEqual(spells[0]["next_invested_close_date"], "2024-01-09")
        self.assertTrue(spells[1]["right_censored"])
        self.assertIsNone(spells[1]["calendar_days_until_next_invested_close"])

    def test_annual_log_attribution_ties_to_full_term_minus_vix(self):
        # Summing annual simple-return differences would not tie to wealth growth.
        dates = ["2024-01-02", "2024-12-31", "2025-01-02"]
        term = self.daily(dates, [100, 150, 120])
        vix = self.daily(dates, [100, 120, 132])
        summary, annual = self.load().term_vix_comparison(term, vix, initial_nav=100)
        self.assertAlmostEqual(annual["log_increment_term_minus_vix"].sum(), np.log(120/132))
        self.assertAlmostEqual(summary["total_log_increment"], np.log(120/132))
        self.assertAlmostEqual(summary["positive_year_share_of_positive_increment_max"], 1.0)

    def test_intervention_count_requires_fills_and_completed_nonoverlap_windows(self):
        # Unfilled intentions and right-edge events cannot make the12-episode gate.
        signals = [0, 20, 21, 41, 42, 70]
        trace = pd.DataFrame({"k": signals, "action": ["CASH"]*len(signals)})
        filled = [0, 20, 21, 42, 70]
        orders = pd.DataFrame({"signal_idx": filled, "execution_idx": np.asarray(filled)+1,
                               "instruction_id": np.arange(len(filled)), "reason": "CASH", "notional": 100.0})
        summary, episodes = self.load().intervention_summary(trace, orders, last_idx=80)
        row = summary["CASH"]
        self.assertEqual(row["intended_signals"], 6)
        self.assertEqual(row["realized_instructions"], 5)
        self.assertEqual(row["completed21_instructions"], 4)
        self.assertEqual(row["separated_completed21_episodes"], 3)
        self.assertFalse(row["at_least12_separated_completed21"])
        self.assertEqual(int(episodes["selected_nonoverlap"].sum()), 3)

    def test_warmup_comparison_is_exact_through_readiness_close(self):
        # Approximate equality would conceal an unintended warmup trade difference.
        base = self.daily(pd.bdate_range("2024-01-08", periods=4), [100, 101, 102, 103])
        candidate = base.copy()
        candidate.loc[2:, "nav_close"] += 99
        self.assertTrue(self.load().warmup_replication(base, candidate, ready_idx=1)["exact_match"])
        candidate.loc[1, "nav_close"] += 1e-10
        self.assertFalse(self.load().warmup_replication(base, candidate, ready_idx=1)["exact_match"])

    def mark_fixture(self):
        dates = pd.bdate_range("2024-01-05", periods=6)
        raw = np.full((6, 1), np.nan)
        raw[0, 0] = 10
        observed = np.zeros((6, 1), bool)
        observed[0, 0] = True
        panel = dict(dates=dates, C=raw, observed=observed, names=np.array(["ETF"]))
        daily = self.daily(dates, [100]*6, gross=[.1]*5+[0])
        orders = pd.DataFrame(dict(j=[0, 0], side=["BUY", "SELL"], quantity=[1., 1.],
            price=[10., 10.], notional=[10., 10.], cost=[0., 0.], execution_idx=[0, 5], ticker=["ETF", "ETF"]))
        return daily, orders, panel

    def test_held_mark_age_boundary_and_sale_before_close(self):
        # Calendar age, not observed-session age, crosses5 on Jan11; Jan12 is sold.
        daily, orders, panel = self.mark_fixture()
        summary, violations = self.load().held_mark_audit(daily, orders, panel, initial_cash=100)
        self.assertEqual(summary["stale_held_asset_closes"], 1)
        self.assertEqual(violations["date"].tolist(), ["2024-01-11"])
        self.assertEqual(violations["source_age_calendar_days"].tolist(), [6])
        self.assertFalse(summary["valuation_support_pass"])
        self.assertTrue(summary["ledger_reconciliation_pass"])

    def test_no_accepted_source_mark_is_not_silently_valued(self):
        daily, orders, panel = self.mark_fixture()
        panel["observed"][:] = False
        summary, violations = self.load().held_mark_audit(daily, orders, panel, initial_cash=100)
        self.assertEqual(summary["held_asset_closes_without_valid_mark"], 5)
        self.assertTrue((violations["issue"] == "NO_VALID_SOURCE_MARK").all())
        self.assertFalse(summary["valuation_support_pass"])

    def test_continuous_holding_age_does_not_reset_on_topup(self):
        daily, orders, panel = self.mark_fixture()
        panel["C"][:] = 10
        panel["observed"][:] = True
        orders = orders.iloc[:1].copy()
        topup = orders.iloc[0].copy()
        topup["execution_idx"] = 3
        orders = pd.concat((orders, pd.DataFrame([topup])), ignore_index=True)
        daily.loc[3:, "gross"] = .2
        daily.loc[3:, "cash"] = 80
        daily.loc[3:, "positions"] = 1
        summary, _ = self.load().held_mark_audit(daily, orders, panel, initial_cash=100)
        self.assertEqual(summary["max_continuous_holding_age_sessions"], 5)

    def test_invalid_nav_and_panel_date_mismatch_raise(self):
        daily, orders, panel = self.mark_fixture()
        bad = daily.copy()
        bad.loc[0, "nav_close"] = np.nan
        with self.assertRaises(ValueError):
            self.load().performance_window(bad, initial_nav=100)
        daily.loc[0, "date"] = "2024-01-04"
        with self.assertRaises(ValueError):
            self.load().held_mark_audit(daily, orders, panel, initial_cash=100)

    def test_missing_daily_session_is_rejected_by_matrix_loader(self):
        # Per-row date checks alone can conceal a missing unsupported held day.
        dates = pd.bdate_range("2024-01-08", periods=4)
        daily = self.daily(dates, [100, 101, 102, 103])
        audit = self.load()
        audit.validate_result_calendar(daily, dates, start_idx=0, end_idx=3)
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_OR_MISMATCHED_RESULT_CALENDAR"):
            audit.validate_result_calendar(daily.drop(index=2), dates, start_idx=0, end_idx=3)

    def test_partial_sale_preserves_age_and_liquidation_reentry_resets_it(self):
        daily, orders, panel = self.mark_fixture()
        panel["C"][:] = 10
        panel["observed"][:] = True
        orders = pd.DataFrame(dict(j=[0]*4, ticker=["ETF"]*4,
            side=["BUY", "SELL", "SELL", "BUY"], quantity=[1., .4, .6, 1.],
            notional=[10., 4., 6., 10.], cost=[0.]*4, execution_idx=[0, 2, 3, 4]))
        daily["gross"] = [.1, .1, .06, 0., .1, .1]
        daily["cash"] = [90., 90., 94., 100., 90., 90.]
        daily["positions"] = [1, 1, 1, 0, 1, 1]
        summary, _ = self.load().held_mark_audit(daily, orders, panel, initial_cash=100)
        self.assertTrue(summary["ledger_reconciliation_pass"])
        self.assertEqual(summary["max_continuous_holding_age_sessions"], 2)


if __name__ == "__main__":
    unittest.main()
