import ast
import unittest
from pathlib import Path
from history_window_v1.replay_patch import patch_models, patch_titanium

ROOT=Path(__file__).resolve().parents[1]/'vendor/etf_trader_v2'

class ReplayPatchTests(unittest.TestCase):
    def test_only_compact_month_gate_changes(self):
        original=(ROOT/'src/etf_trader/source_only/models.py').read_text()
        patched=patch_models(original)
        self.assertIn('if n_train_dates<58:',patched)
        self.assertEqual(patched.replace('if n_train_dates<58:','if n_train_dates<60:').replace("'required':58","'required':60"),original)
        ast.parse(patched)

    def test_training_cutoff_all_titanium_inputs(self):
        original=(ROOT/'scripts/build_tit_r_source_only.py').read_text()
        patched=patch_titanium(original)
        for frame in ('compact','tail','macro','extra'):
            self.assertIn(f"{frame}={frame}[{frame}.signal_date.ge('2012-01-01')].copy()",patched)
        self.assertLess(patched.index("compact=compact[compact.signal_date.ge('2012-01-01')]"),patched.index('pred=fit_predict('))
        self.assertIn('compact=k.add_labels(compact,mats["Open"],dates)',patched)
        ast.parse(patched)

    def test_fail_closed_on_unexpected_source(self):
        with self.assertRaises(ValueError):patch_models('if n_train_dates<61: pass')
        with self.assertRaises(ValueError):patch_titanium('pred=unknown()')

if __name__=='__main__':unittest.main()
