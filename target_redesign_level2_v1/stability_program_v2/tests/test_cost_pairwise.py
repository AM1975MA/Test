import numpy as np
import pytest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cost_pairwise import group_loss, make_xgb_objective

def test_culls_uneconomic_pair_and_keeps_large_winner():
    p=np.zeros(3)
    returns=np.array([.0100,.0105,.0800]); grad,hess,stats=group_loss(p,returns,fee_band=.002)
    assert stats['excluded'] == 1 and stats['included'] == 2
    assert abs(sum(grad))<1e-10
    assert grad[2] <0 and grad[0]>0 and grad[1]>0
    assert np.all(hess>0)

def test_reversed_epsilon_pair_is_invariant():
    a=np.array([.0100,.010002,.0600]);b=np.array([.010002,.0100,.0600]);p=np.array([.1,-.1,.8])
    grad_a,hess_a,_=group_loss(p,a,.002)
    grad_b,hess_b,_=group_loss(p,b,.002)
    np.testing.assert_allclose(grad_a,grad_b,rtol=0,atol=0)
    np.testing.assert_allclose(hess_a,hess_b,rtol=0,atol=0)

def test_no_effective_pairs_uses_safe_hessian():
    g,h,s=group_loss(np.array([0.,0.]),np.array([0.,.0001]),.002)
    assert np.all(g==0) and np.all(h>0) and s['included']==0

def test_invalid_inputs_raise():
    with pytest.raises(ValueError):group_loss(np.zeros(2),np.zeros(3),.002)
    with pytest.raises(ValueError):make_xgb_objective(np.zeros(7),.002)
