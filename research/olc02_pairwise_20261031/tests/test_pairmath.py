import numpy as np
import pandas as pd
import pytest
from pairmath import log_advantage, mature_mask, monthly_weights, cost_log, candidate_pairs, best_action

def test_same_portfolio_has_zero_direct_advantage():
    assert abs(log_advantage([1,2],[.2,.8],[100,200],[110,190]))<1e-14

def test_actual_hold_quantities_not_equal_weight_proxy():
    got=log_advantage([1,3,0],[0,0,1],[100,100,100],[120,80,110])
    assert abs(got-(np.log(1.1)-np.log(.9)))<1e-14

def test_missing_exit_quote_is_not_zero_return():
    assert np.isnan(log_advantage([1,0],[0,1],[100,100],[110,np.nan]))

def test_unused_missing_quote_does_not_invalidate_label():
    assert abs(log_advantage([1,0],[1,0],[100,np.nan],[110,np.nan]))<1e-14

def test_label_must_mature_strictly_before_cutoff():
    m=mature_mask(pd.to_datetime(['2023-10-31']*3),pd.to_datetime(['2023-12-31','2024-01-01',None]),[1,1,1],pd.Timestamp('2024-01-01'))
    assert m.tolist()==[True,False,False]

def test_each_month_weight_is_one_not_each_pair():
    d=pd.to_datetime(['2020-01-31']*10+['2020-02-28']*2)
    w=monthly_weights(d)
    np.testing.assert_allclose([w[:10].sum(),w[10:].sum()],[1,1])

def test_cost_is_legacy_half_turnover_once():
    assert cost_log([.5,.5,0],[0,.5,.5],.001)==pytest.approx(-np.log1p(-.0005))
    assert cost_log([.5,.5],[.5,.5],.001)==0

def test_candidates_only_use_current_cl01_in_live_mode():
    ps=candidate_pairs([0,1],[2,3],[2,3,4,5],single=True)
    assert set(ps)=={(2,3),(2,1),(3,1),(0,2),(0,3)}
    assert not any(4 in p or 5 in p for p in ps)

def test_training_retains_nonexecuted_proposals():
    ps=candidate_pairs([0,1],[2,3],[2,3,4,5,6],training=True)
    assert any(4 in p for p in ps)
    assert len({tuple(sorted(p)) for p in ps})==len(ps)

def test_identical_set_not_called_switch():
    assert candidate_pairs([0,1],[1,0],[1,0,2])==[]

def test_negative_or_zero_net_advantage_means_hold():
    assert best_action([-.02,.001],[.001,.002])==-1
    assert best_action([.001],[.001])==-1

def test_positive_net_value_accepts_existing_proposal_only():
    assert best_action([.01,.005],[.002,.001])==0
