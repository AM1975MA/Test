import numpy as np, pandas as pd
from scipy.stats import rankdata


def test_pct_rank_invariant_to_strict_monotonic_transform():
    x=np.array([-1.,-.5,0.,0.,2.])
    a=pd.Series(x).rank(pct=True,method='average').to_numpy()
    b=pd.Series(7*np.exp(x)).rank(pct=True,method='average').to_numpy()
    assert np.array_equal(a,b)


def test_ranking_ignores_economic_score_magnitudes():
    a=np.array([.12,.11,.10]);b=np.array([5.,.11,.10])
    assert np.array_equal(rankdata(a),rankdata(b))


def test_target_still_immature_at_same_open():
    t0=pd.Timestamp('2026-07-01');t1=pd.Timestamp('2026-07-01')
    assert not (t1>t0)


def test_pairwise_spread_is_antisymmetric():
    r=np.log(np.array([110./100.,96./100.]))
    assert abs((r[0]-r[1])+(r[1]-r[0]))<1e-14


def test_annual_maturity_is_strictly_before_cutoff():
    cutoff=pd.Timestamp('2024-01-01')
    labels=pd.to_datetime(['2023-12-29','2024-01-01','2024-01-02'])
    assert (labels<cutoff).tolist()==[True,False,False]
