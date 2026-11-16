"""Independent synthetic adversarial checks; never reads historical inputs."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import cycle_core as cc
import cycle_engine as engine
import cycle_model as cm


def fixture():
    spec = importlib.util.spec_from_file_location('independent_native_core', ROOT.parent / 'olc110/source/src/core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    dates = pd.bdate_range('2019-01-01', periods=380)
    returns = np.random.default_rng(608).normal(.0002, .012, (380, 5))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    panel = dict(dates=dates, names=np.array(['A', 'B', 'C', 'D', 'UNUSED']),
                 C=prices, O=prices.copy(), observed=np.ones(prices.shape, bool))
    monthly = np.zeros(380, bool)
    monthly[[310, 332, 353, 375]] = True
    weekly = np.zeros(380, bool)
    weekly[np.arange(296, 380, 5)] = True
    targets = np.tile([.5, .5, 0., 0., 0.], (380, 1))
    targets[310:332] = [0., .5, .5, 0., 0.]
    targets[332:353] = [.5, 0., 0., .5, 0.]
    order = [[2, 0] for _ in range(380)]
    for k in range(305, 310):
        order[k] = [3, 0]
    bundle = dict(panel=panel, f=dict(C=prices, returns=returns), core=core,
                  monthly=monthly, feature_monthly=monthly, weekly=weekly,
                  targets=targets, selected_order=order, begin=300)
    seed = dict(units=np.array([40., 30., 0., 0., 0.]), cash=2000.)
    return bundle, seed


def replay(bundle, seed, plan=None, *, lag=0, end=341, callback=None):
    return engine.simulate(bundle['panel'], bundle['f'],
                           lambda k, w: bundle['targets'][k], bundle['monthly'],
                           legacy=bundle['core'], account_policy=callback or plan,
                           initial_state=seed, issue_initial=plan is not None or callback is not None,
                           allow_initial_targeted=plan is not None or callback is not None,
                           start=str(bundle['panel']['dates'][300].date()),
                           end=str(bundle['panel']['dates'][end].date()), lag=lag)


class IndependentBoundaries(unittest.TestCase):
    def test_subset_counterfactuals_equal_full_universe_replays(self):
        b, seed = fixture()
        baseline = replay(b, seed)
        b['baseline_nav'] = {int(row.k): float(row.nav_close) for row in baseline['daily'].itertuples()}
        group = cc.counterfactual_group(b, 299, seed)
        self.assertEqual(group['status'], 'OK')
        self.assertNotIn(4, group['asset_indices'])
        base_nav = baseline['daily'].nav_close.iloc[-1]
        self.assertLess(group['base_replay_error'], 1e-8)
        for row in group['records']:
            plan = cc.PlanExecutor(b, row['head'], row['asset'], 299)
            result = replay(b, seed, plan)
            expected = float(result['daily'].nav_close.iloc[-1])
            self.assertAlmostEqual(group['nav'][f"{row['head']}:{row['asset']}"], expected, places=8)
            self.assertAlmostEqual(row['y'], np.log(expected / base_nav), places=13)

    def test_entry_preserves_retained_units_across_large_gap(self):
        b, seed = fixture()
        # First actual sale is300; first strictly later weekly signal is301.
        # A retained-price gap occurs on the302 execution Close.
        b['panel']['C'][302:, 1] *= 2.7
        b['panel']['O'] = b['panel']['C'].copy()
        plan = cc.PlanExecutor(b, 'REDEPLOY', 0, 299)
        states = {}
        def callback(k, w, context):
            states[k] = dict(units=context['units'].copy(), cash=context['cash'], nav=context['nav'])
            return plan(k, w, context)
        result = replay(b, seed, plan, callback=callback)
        self.assertEqual(plan.summary['entry_attempt_idx'], 301)
        self.assertEqual(states[302]['units'][1], seed['units'][1])
        self.assertGreater(states[302]['units'][2], 0)
        orders = result['orders'].query("reason == 'REDEPLOY_ENTRY'")
        self.assertEqual(orders.j.tolist(), [2])
        self.assertGreaterEqual(states[302]['cash'], 0.)

    def test_monthly_handoff_does_not_cancel_a_still_earlier_due_fill(self):
        b, seed = fixture()
        b['monthly'][310] = False
        b['monthly'][302] = True
        b['panel']['observed'][300:303, 0] = False
        plan = cc.PlanExecutor(b, 'PARK', 0, 299)
        result = replay(b, seed, plan, lag=1)
        self.assertEqual(plan.summary['handoff_idx'], 302)
        sale = result['orders'].query("reason == 'PARK_SALE'")
        self.assertEqual(sale.execution_idx.tolist(), [303])
        # At lag1 the302 monthly instruction cannot supersede before304.
        monthly = result['instructions'].query("reason == 'SCHEDULED'")
        self.assertEqual(monthly.iloc[0].due_idx, 304)

    def test_future_selection_changes_plan_outcome_but_not_initial_features(self):
        b, seed = fixture()
        nav = seed['cash'] + seed['units'] @ b['f']['C'][299]
        current = seed['units'] * b['f']['C'][299] / nav
        before = cc.plan_features(b, 299, current, nav, 0, 'REDEPLOY')
        changed = dict(b, selected_order=deepcopy(b['selected_order']))
        changed['selected_order'][301] = [3, 0]
        after = cc.plan_features(changed, 299, current, nav, 0, 'REDEPLOY')
        np.testing.assert_array_equal(before, after)
        original = cc.PlanExecutor(b, 'REDEPLOY', 0, 299)
        alternate = cc.PlanExecutor(changed, 'REDEPLOY', 0, 299)
        replay(b, seed, original)
        replay(changed, seed, alternate)
        self.assertEqual(original.summary['entry_candidate_idx'], 2)
        self.assertEqual(alternate.summary['entry_candidate_idx'], 3)

    def test_outgoing_asset_is_eligible_to_recompete(self):
        b, seed = fixture()
        b['selected_order'][301] = [0, 2]
        plan = cc.PlanExecutor(b, 'REDEPLOY', 0, 299)
        result = replay(b, seed, plan)
        self.assertEqual(plan.summary['entry_candidate_idx'], 0)
        self.assertEqual(result['orders'].query("reason == 'REDEPLOY_ENTRY'").j.tolist(), [0])

    def test_date_balanced_models_invariant_to_duplicate_identical_legs(self):
        rng = np.random.default_rng(801)
        signals = np.arange(0, 300, 3)
        X = rng.normal(size=(len(signals), 3))
        y = .1 * X[:, 0] + np.where(X[:, 1] > 0, .3, -.2)
        dates = pd.bdate_range('2018-01-01', periods=1000)
        kwargs = dict(cutoff=400, dates=dates, min_dates=1, min_months=1, min_blocks=1)
        a = cm.fit_head(X, y, signals, signals + 42, **kwargs)
        twice = np.repeat(np.arange(len(signals)), 2)
        b = cm.fit_head(X[twice], y[twice], signals[twice], signals[twice] + 42, **kwargs)
        self.assertEqual(a['meta']['draw_hash'], b['meta']['draw_hash'])
        self.assertEqual(a['meta']['mature_dates'], b['meta']['mature_dates'])
        for kind in ('MEAN', 'RIDGE', 'TREE'):
            for x in X[::11]:
                for statistic in ('mean', 'lower'):
                    self.assertAlmostEqual(a['models'][kind].predict(x)[statistic],
                                           b['models'][kind].predict(x)[statistic], places=12)


if __name__ == '__main__':
    unittest.main()
