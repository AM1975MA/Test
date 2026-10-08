"""Standalone unit and synthetic-XGBoost compatibility tests; no ETF backtest."""
import numpy as np
import pytest
import xgboost as xgb
from cost_pairwise import group_loss,make_xgb_objective

def objective_value(scores,returns,band=.002):
    i,j=np.triu_indices(len(scores),1)
    mask=(abs(returns[i]-returns[j])>=band)&(returns[i]!=returns[j])
    margin=(scores[i]-scores[j])[mask]*np.sign(returns[i]-returns[j])[mask]
    return np.logaddexp(0,-margin).sum()/len(scores)

def test_winner_pair_kept_and_near_tie_dropped():
    g,h,s=group_loss(np.zeros(3),[.010,.0105,.080],.002)
    assert s["included"]==2 and s["excluded"]==1
    assert g[2]<0 and g[0]>0 and g[1]>0 and np.all(h>0)

def test_ambiguous_pair_reversal_no_effect_on_gradient():
    p=np.array([.1,-.1,.8])
    a=group_loss(p,[.01,.010002,.06],.002)
    b=group_loss(p,[.010002,.01,.06],.002)
    np.testing.assert_array_equal(a[0],b[0])
    np.testing.assert_array_equal(a[1],b[1])

def test_gradient_matches_finite_difference():
    s=np.array([.01,.02,.04,-.03,.08])
    r=np.array([.011,.01101,.040,.071,-.05])
    g,h,_=group_loss(s,r,.002)
    fd=np.zeros_like(g);eps=1e-6
    for k in range(len(s)):
        a=s.copy();b=s.copy();a[k]+=eps;b[k]-=eps
        fd[k]=(objective_value(a,r)-objective_value(b,r))/(2*eps)
    np.testing.assert_allclose(g,fd,atol=1e-9,rtol=1e-8)
    assert np.all(h>0)

def test_empty_group_has_positive_safe_hessian():
    g,h,stats=group_loss(np.zeros(2),[0.,.0001],.002)
    assert np.all(g==0) and np.all(h>0) and stats["included"]==0

def test_boundary_pair_is_kept():
    assert group_loss(np.zeros(3),[0.,.002,.010],.002)[2]["included"]==3
    assert group_loss(np.zeros(3),[0.,.001999,.010],.002)[2]["included"]==2

def test_invalid_input():
    with pytest.raises(ValueError):group_loss(np.zeros(2),np.zeros(3))
    with pytest.raises(ValueError):make_xgb_objective(np.zeros(7),.002)

def test_group_alignment_and_rejection():
    r=np.array([.001,.00102,.08,.005,.00501,.2],dtype=np.float32)
    m=xgb.DMatrix(np.arange(24,dtype=np.float32).reshape(6,4));m.set_group([3,3])
    f=make_xgb_objective(r,.002,[3,3])
    g,h=f(np.zeros(6),m)
    assert len(g)==6 and np.all(h>0)
    bad=xgb.DMatrix(np.arange(24,dtype=np.float32).reshape(6,4));bad.set_group([2,4])
    with pytest.raises(ValueError,match="group_ptr"):f(np.zeros(6),bad)

def test_synthetic_train_and_prediction():
    rng=np.random.default_rng(991)
    X=rng.normal(size=(96,6)).astype(np.float32)
    r=(X[:,0]*.09+X[:,1]*.02+rng.normal(scale=.003,size=len(X))).astype(np.float32)
    d=xgb.QuantileDMatrix(X);d.set_group([12]*8)
    b=xgb.train({"tree_method":"hist","max_depth":3,"eta":.15,"nthread":1,"seed":101},d,
                num_boost_round=12,obj=make_xgb_objective(r,.002,[12]*8))
    p=b.predict(d)
    assert b.num_boosted_rounds()==12 and np.isfinite(p).all() and np.std(p)>.01
