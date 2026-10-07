import unittest

import pandas as pd

from compact21_rolling_window_v1.run import rolling_train
from compact21_rolling_window_v1.windows import WINDOWS, manifest
from compact21_rolling_window_v1.summarize import check_complete_matrix, YEARS


class RollingProtocolTest(unittest.TestCase):
    def test_strict_window_preserves_original_rows_and_mature_end(self):
        dates = pd.date_range('2004-01-01', '2016-12-01', freq='MS')
        frame = pd.DataFrame({
            'signal_date': dates,
            'exit_date_21': dates + pd.Timedelta(days=21),
            'ticker': 'AAA',
            'target_rank_21': 0.5,
        })
        frame = frame.loc[frame.exit_date_21.lt(pd.Timestamp('2017-01-01'))]
        for name, years in WINDOWS.items():
            with self.subTest(window=name):
                selected = rolling_train(frame, 2017, years)
                self.assertEqual(selected.signal_date.min(),
                                 max(pd.Timestamp(2004, 1, 1), pd.Timestamp(2017-years, 1, 1)))
                self.assertTrue(selected.exit_date_21.lt(pd.Timestamp('2017-01-01')).all())
                self.assertEqual(selected.target_rank_21.tolist(), [0.5] * len(selected))
        self.assertEqual(set(manifest()), set(WINDOWS))

    def test_incomplete_year_window_grid_is_rejected(self):
        complete = {(name, year): object() for name in WINDOWS for year in YEARS}
        check_complete_matrix(complete)
        del complete[('ROLL6', 2017)]
        with self.assertRaises(ValueError):
            check_complete_matrix(complete)


if __name__ == '__main__':
    unittest.main()
