"""R0-P focused unit tests: original parity, discontinuity and guard semantics."""
import numpy as np
import pandas as pd
from numeric_guard import rolling_downvol_guard, cs_robust_dev


def test_epsilon_zero_exactly_matches_source():
    r = pd.DataFrame({'A': [-.01, .01, -.02, 0., .03, -.04, -.03]})
    original = r.where(r < 0).rolling(7, min_periods=3).std(ddof=0) * np.sqrt(252)
    pd.testing.assert_frame_equal(original, rolling_downvol_guard(r, 7, 0., min_periods=3))


def test_one_nearly_zero_return_sign_flip_triggers_min_period_discontinuity():
    common = [-.01] * 30 + [.01] * 32
    older = pd.DataFrame({'IYT': common + [1e-7]})
    newer = pd.DataFrame({'IYT': common + [-1e-7]})
    assert np.isnan(rolling_downvol_guard(older, 63, 0., 31).iloc[-1, 0])
    assert np.isfinite(rolling_downvol_guard(newer, 63, 0., 31).iloc[-1, 0])
    assert np.isnan(rolling_downvol_guard(older, 63, 1e-6, 31).iloc[-1, 0])
    assert np.isnan(rolling_downvol_guard(newer, 63, 1e-6, 31).iloc[-1, 0])


def test_robust_dev_preserves_native_median_mad_semantics():
    values = pd.DataFrame({'ETF1': [.2], 'ETF2': [.3], 'ETF3': [.1]})
    z = cs_robust_dev(values)
    assert abs(z['ETF1'].iloc[0]) < 1e-12
    assert np.isfinite(z['ETF3'].iloc[0])
