import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v2.replay import verify_panel_identity, verify_training_fingerprints
from paper_ltr_v2.summarize_replay import checked_calendar, metrics, checked_leaders
from paper_ltr_v1.learner import FEATURES, array_hash, keys_hash, decile_labels, split_training, raw_matrix


class ReplayClosureTests(unittest.TestCase):
    def test_training_fingerprints_reject_mutated_fit_input(self):
        dates=pd.date_range('2014-01-31',periods=20,freq='ME')
        panel=pd.DataFrame({name:np.arange(20,dtype=float) for name in FEATURES})
        panel['signal_date']=dates;panel['ticker']='A';panel['exit_date_21']=dates+pd.Timedelta(days=21)
        panel['target_rank_21']=.6
        sub,val,_=split_training(panel,2017)
        fingerprints=dict(train_keys_sha256=keys_hash(panel),subtrain_keys_sha256=keys_hash(sub),
            validation_keys_sha256=keys_hash(val),train_matrix_sha256=array_hash(raw_matrix(panel)),
            train_labels_sha256=array_hash(decile_labels(panel)))
        result={'per_year':{str(y):{'transforms':{'1':fingerprints.copy()}} for y in range(2017,2027)}}
        self.assertTrue(verify_training_fingerprints(result,panel,1)['PASS'])
        result['per_year']['2018']['transforms']['1']['train_matrix_sha256']='tampered'
        with self.assertRaises(ValueError):verify_training_fingerprints(result,panel,1)

    def test_feature_and_label_mutations_fail_semantic_identity(self):
        panel = pd.DataFrame({'signal_date': pd.to_datetime(['2016-01-31', '2016-02-29']),
                              'ticker': ['A', 'A'], 'x': [1., np.nan],
                              'target_rank_21': [.3, .7],
                              'exit_date_21': pd.to_datetime(['2016-02-29', '2016-03-31'])})
        self.assertTrue(verify_panel_identity(panel, panel.copy(), ['x'])['PASS'])
        for column, value in [('x', 2.), ('target_rank_21', .9)]:
            changed = panel.copy(); changed.loc[0, column] = value
            with self.assertRaises(ValueError): verify_panel_identity(panel, changed, ['x'])
        changed = panel.iloc[:1]
        with self.assertRaises(ValueError): verify_panel_identity(panel, changed, ['x'])

    def test_calendar_rejects_duplicates_unsorted_and_null(self):
        for dates in [['2020-01-01', '2020-01-01'], ['2020-01-02', '2020-01-01'], ['2020-01-01', None]]:
            with self.assertRaises(ValueError): checked_calendar(dates)

    def test_leaders_must_match_npz_calendar_and_be_nonnull(self):
        dates = checked_calendar(['2020-01-01', '2020-01-02'])
        frame = pd.DataFrame({'date': ['2020-01-01', '2020-01-02'], 'top1': ['A', 'B'], 'top2': ['B', 'A']})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'leaders.csv'; frame.to_csv(path, index=False)
            self.assertEqual(len(checked_leaders(path, dates)), 2)
            changed = frame.copy(); changed.loc[1, 'date'] = '2020-01-03'; changed.to_csv(path, index=False)
            with self.assertRaises(ValueError): checked_leaders(path, dates)
            changed = frame.copy(); changed.loc[1, 'top2'] = None; changed.to_csv(path, index=False)
            with self.assertRaises(ValueError): checked_leaders(path, dates)

    def test_flat_equity_has_defined_zero_sharpe(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'path.npz'
            np.savez(path, equity=np.ones((1, 3)), dates=np.array(['2020-01-01', '2020-01-02', '2020-01-03']))
            result, _ = metrics(path)
            self.assertEqual(result['sharpe'], 0.)
            self.assertEqual(result['cagr'], 0.)


if __name__ == '__main__': unittest.main()
