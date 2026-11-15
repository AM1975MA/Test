"""Hand-calculated controls for diagnostic, single-instruction accounting."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


class ActionMarkoutTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('action_markouts.py')
        self.assertTrue(path.exists(), 'Independent event-account algebra is not implemented')
        spec = importlib.util.spec_from_file_location('action_markout_under_test', path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.panel = dict(C=np.full((24, 2), 100.), O=np.full((24, 2), 100.),
                          valid=np.ones((24, 2), bool),
                          dates=pd.bdate_range('2020-01-01', periods=24),
                          names=np.array(['A', 'B']))
        self.ins = dict(signal_idx=0, due_idx=1, target=np.array([0., .5]),
                        action_indices=[0], sell_only=True, force=True,
                        ticket=1., impact=.0015)

    def test_exit_retains_unaffected_units_and_separates_fees_from_market_markout(self):
        self.panel['O'][1:, 1] = 200.
        self.panel['C'][1:, :] = [80., 200.]
        result = self.mod.isolated_markouts(self.panel, self.ins, np.array([50., 50.]), 0.)
        first = result['intervals'][0]
        self.assertEqual(first['nav_hold'], 14000.)
        self.assertEqual(first['nav_action'], 14991.5)
        self.assertAlmostEqual(first['increment_bp'], 991.5)
        self.assertAlmostEqual(first['direct_cost_bp'], 8.5)
        self.assertAlmostEqual(first['market_markout_bp'], 1000.)
        np.testing.assert_array_equal(result['end_units'], [0., 50.])
        self.assertEqual([trade['j'] for trade in result['trades']], [0])

    def test_buy_is_limited_to_cash_after_costs_despite_unaffected_gap(self):
        self.panel['O'][1:, 1] = 200.
        self.panel['C'][1:, :] = [110., 200.]
        self.ins.update(target=np.array([.5, .5]), sell_only=False)
        result = self.mod.isolated_markouts(self.panel, self.ins, np.array([0., 50.]), 5000.)
        first = result['intervals'][0]
        notional = 4999. / 1.0015
        fee = 1. + .0015 * notional
        self.assertAlmostEqual(result['trades'][0]['notional'], notional)
        self.assertAlmostEqual(first['market_markout_bp'], .1 * notional)
        self.assertAlmostEqual(first['increment_bp'], .1 * notional - fee)
        self.assertEqual(result['end_units'][1], 50.)
        self.assertAlmostEqual(result['end_cash'], 0.)

    def test_lag_and_missing_masked_quote_produce_ties_before_the_first_fill(self):
        self.ins.update(due_idx=3, ticket=0., impact=0.)
        self.panel['valid'][3, 0] = False
        self.panel['valid'][1:, 1] = False
        self.panel['C'][4:, 0] = 90.
        result = self.mod.isolated_markouts(self.panel, self.ins, np.array([50., 50.]), 0.)
        self.assertEqual(result['intervals'][0]['increment_bp'], 0.)
        self.assertEqual(result['intervals'][0]['execution_count'], 0)
        self.assertEqual(result['intervals'][1]['increment_bp'], 500.)
        self.assertEqual(result['missing_attempts'], [3])
        self.assertEqual(result['trades'][0]['execution_idx'], 4)
        self.assertEqual(result['completed_idx'], 4)

    def test_cutoff_keeps_partial_horizons_labeled_and_does_not_invent_future_prices(self):
        self.ins.update(signal_idx=21, due_idx=22, ticket=0., impact=0.)
        result = self.mod.isolated_markouts(self.panel, self.ins, np.array([50., 50.]), 0.)
        rows = result['intervals']
        self.assertEqual([row['actual_horizon_sessions'] for row in rows], [1, 2, 2])
        self.assertEqual([row['truncated'] for row in rows], [False, True, True])
        self.assertEqual([row['endpoint_idx'] for row in rows], [22, 23, 23])


if __name__ == '__main__':
    unittest.main(verbosity=2)
