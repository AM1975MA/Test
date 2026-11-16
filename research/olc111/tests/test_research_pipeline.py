"""Economic and causal boundaries of the OLC111 bank and policy features."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import json
import hashlib
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def module():
    path = ROOT / 'src/research_pipeline.py'
    assert path.exists(), 'OLC111 causal bank/feature implementation is missing'
    spec = importlib.util.spec_from_file_location('research_pipeline_test', path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out


class ResearchPipelineTest(unittest.TestCase):
    def test_present_weights_use_only_trailing_returns_and_keep_cash(self):
        m = module()
        rr = np.full((340, 2), .001)
        rr[:, 1] = np.nan
        f = {'returns': rr}
        # Zero-weight bad history must not poison a valid held basket.
        s = m.basket_stats(f, 300, np.array([.5, 0.]))
        expected_log = np.log(1 + .5 * np.expm1(.001))
        self.assertAlmostEqual(s['log21'], 21 * expected_log)
        rr[301:, 0] = -10
        later = m.basket_stats(f, 300, np.array([.5, 0.]))
        self.assertEqual(s['log21'], later['log21'])
        self.assertTrue(np.isfinite(s['nm21']))

    def test_monthly_horizon_excludes_today_and_feature_tracks_exposure(self):
        m = module()
        rr = np.zeros((340, 2))
        rr[:, 0] = np.resize([-.01, .011], 340)
        rr[:, 1] = np.resize([.003, -.002], 340)
        monthly = np.zeros(340, bool); monthly[[300, 321]] = True
        features = m.state_features({'returns': rr}, 300, [.4, .2], [0., 1.], .7, monthly)
        self.assertAlmostEqual(features['CASH'][-1], .6)
        self.assertEqual(features['CASH'][-2], 1.)
        self.assertEqual(features['ENTRY'][-1], 1.)
        self.assertAlmostEqual(features['CASH'][3], .7)

    def test_noop_threshold_and_zero_fresh_do_not_authorize_entry(self):
        m = module()
        self.assertFalse(m.fresh_is_action([.5, .5], [.51, .49]))
        self.assertFalse(m.fresh_is_action([0., 0.], [0., 0.]))
        self.assertTrue(m.fresh_is_action([.5, .5], [0., 1.]))

    def test_action_buffer_requires_both_positive_and_uses_lower_bound(self):
        m = module()
        self.assertTrue(callable(getattr(m,'select_action',None)), 'Action buffer implementation missing')
        self.assertEqual(m.select_action({'CASH': {'mean': .10, 'lower': -.01}}),'HOLD')
        self.assertEqual(m.select_action({'CASH': {'mean': -.01, 'lower': .01}}),'HOLD')
        self.assertEqual(m.select_action({'CASH': {'mean': .10, 'lower': .01},
                                          'FRESH': {'mean': .03, 'lower': .02}}),'FRESH')
        self.assertEqual(m.select_action({'CASH': {'mean': .03, 'lower': .02},
                                          'FRESH': {'mean': .03, 'lower': .02}}),'CASH')

    def test_primary_execution_explicitly_uses_next_close_not_open(self):
        m = module(); p,f,core,monthly,targets,state = self.fixture()
        self.assertTrue(callable(getattr(m,'execution_panel',None)), 'Execution adapter missing')
        p['O'][301:,0] = 50.
        close_panel=m.execution_panel(p,'CLOSE')
        out=m.counterfactual_values(close_panel,f,core,monthly,targets,300,state,horizon=2)
        self.assertAlmostEqual(out['nav']['CASH'],8993.)
        original=m.counterfactual_values(m.execution_panel(p,'OPEN'),f,core,monthly,targets,300,state,horizon=2)
        self.assertAlmostEqual(original['nav']['CASH'],7495.25)
        self.assertEqual(p['O'][301,0],50.)

    def fixture(self):
        path = ROOT.parent / 'olc110/source/src/core.py'
        spec = importlib.util.spec_from_file_location('core_pipeline_test', path)
        core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
        dates = pd.bdate_range('2019-01-01', periods=340)
        p = dict(dates=dates, names=np.array(['A','B','UNUSED']),
                 C=np.full((340,3),100.), O=np.full((340,3),100.),
                 observed=np.ones((340,3),bool), open_observed=np.ones((340,3),bool), benchmark=0)
        # A loses 20% at first execution, B stays flat; initial state has 50A+5000cash.
        p['C'][301:,0] = 80.; p['O'][301:,0] = 80.
        f = core.features(p)
        monthly = np.zeros(340,bool)
        targets = np.tile([0.,1.,0.],(340,1))
        return p,f,core,monthly,targets,dict(units=np.array([50.,0.,0.]),cash=5000.)

    def test_native_counterfactual_respects_gap_and_actual_order_costs(self):
        m = module(); p,f,core,monthly,targets,state = self.fixture()
        values = m.counterfactual_values(p,f,core,monthly,targets,300,state,horizon=2)
        self.assertEqual(values['status'],'OK')
        # HOLD 9000. CASH sells4000, paysEUR1+6=7. FRESH also buys,
        # with spend8992 and another EUR1 +15bp self-financed purchase.
        self.assertAlmostEqual(values['nav']['HOLD'],9000.)
        self.assertAlmostEqual(values['nav']['CASH'],8993.)
        self.assertAlmostEqual(values['nav']['FRESH'],8992./1.0015,places=8)
        self.assertAlmostEqual(values['net']['CASH'],np.log(8993./9000.))
        self.assertEqual(values['orders']['CASH'],1)
        self.assertEqual(values['orders']['FRESH'],2)
        self.assertEqual(values['terminal_idx'],302)
        # Counterfactual simulation must not alter seed or panel.
        np.testing.assert_array_equal(state['units'],[50.,0.,0.])
        self.assertEqual(state['cash'],5000.)

    def test_censoring_is_matched_and_right_edge_never_becomes_zero(self):
        m = module(); p,f,core,monthly,targets,state = self.fixture()
        p['observed'][301:,0]=False
        f=core.features(p)
        values=m.counterfactual_values(p,f,core,monthly,targets,300,state,horizon=10)
        self.assertEqual(values['status'],'CENSORED_STALE_MARK')
        self.assertNotIn('net',values)
        edge=m.counterfactual_values(p,f,core,monthly,targets,335,state,horizon=21)
        self.assertEqual(edge['status'],'RIGHT_EDGE')
        self.assertNotIn('net',edge)

    def test_unsupported_initial_held_mark_censors_whole_comparison(self):
        m=module(); p,f,core,monthly,targets,state=self.fixture()
        f['C'][300,0]=np.nan
        out=m.counterfactual_values(p,f,core,monthly,targets,300,state,horizon=2)
        self.assertEqual(out['status'],'CENSORED_MISSING_MARK')
        self.assertNotIn('net',out)

    def test_feature_calendar_keeps_known_terminal_month_end(self):
        m=module()
        self.assertTrue(callable(getattr(m,'feature_monthly_schedule',None)), 'Feature calendar missing')
        dates=pd.bdate_range('2026-09-01','2026-10-30')
        execution=np.zeros(len(dates),bool)
        execution[np.flatnonzero(dates.month==9)[-1]]=True
        schedule=m.feature_monthly_schedule(dates,execution)
        self.assertTrue(schedule[-1])
        self.assertFalse(execution[-1])
        self.assertEqual(np.flatnonzero(schedule)[-1]-np.flatnonzero(dates==pd.Timestamp('2026-10-29'))[0],1)

    def test_resume_rejects_changed_input_instead_of_trusting_cached_labels(self):
        m=module()
        self.assertTrue(callable(getattr(m,'verify_bank_freeze',None)), 'Frozen cache verifier missing')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'docs').mkdir();(root/'data').mkdir()
            (root/'data/source').write_bytes(b'old')
            (root/'docs/DESIGN_AND_PROTOCOL.md').write_bytes(b'protocol')
            freeze={'code_hashes':{},'input_hashes':{'data/source':hashlib.sha256(b'old').hexdigest()},
                    'protocol_sha256':hashlib.sha256(b'protocol').hexdigest()}
            (root/'docs/BANK_FREEZE.json').write_text(json.dumps(freeze))
            m.verify_bank_freeze(root)
            (root/'data/CAUSAL_SELECTIONS.npz').write_bytes(b'cached')
            m.verify_bank_freeze(root)
            (root/'data/source').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'FROZEN_INPUT_CHANGED'):
                m.verify_bank_freeze(root)


if __name__ == '__main__':
    unittest.main()
