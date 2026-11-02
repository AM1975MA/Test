import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pytest
from scipy.optimize._numdiff import approx_derivative
from context_model import capped_weights,setup,objective,fit_model,predict_weights

def fixture_groups():
    rng=np.random.default_rng(16);groups=[]
    for market in ['EU','USA']:
        for t in range(4):
            z=rng.uniform(.1,.9,(8,3));x=rng.normal(size=3)
            u=.02*(z[:,0]+x[0]*z[:,1])+rng.normal(0,.005,8)
            groups.append(dict(market=market,date=f'2020-0{t+1}-01',z=z,u=u,x=x))
    return groups

def test_weights_are_capped_and_normalized():
    for s in [np.zeros(5),np.array([1.,0.,0.,0.,0.]),np.array([1.,1.,0.,0.])]:
        w=capped_weights(s)
        assert np.isclose(w.sum(),1)
        assert (w>=0).all() and (w<=.5+1e-15).all()
    assert capped_weights(np.array([1.,0.,0.]))[0]==.5
    np.testing.assert_allclose(capped_weights(np.zeros(4)),.25)

def test_soft_top2_has_second_position_information():
    w=capped_weights(np.array([2.,1.,0.]),temperature=.01)
    np.testing.assert_allclose(w[:2],[.5,.5],atol=1e-12)

@pytest.mark.parametrize('kind',['pair','top2'])
@pytest.mark.parametrize('contextual',[False,True])
def test_analytic_gradient_matches_finite_differences(kind,contextual):
    cache,scaler=setup(fixture_groups(),contextual)
    theta=np.linspace(-.15,.2,cache['dimension'])
    value,gradient=objective(theta,cache,kind,.1)
    num=approx_derivative(lambda x:objective(x,cache,kind,.1)[0],theta,method='3-point').reshape(-1)
    np.testing.assert_allclose(gradient,num,rtol=2e-5,atol=2e-7)
    assert np.isfinite(value)

def test_queries_not_ticker_counts_balance_markets():
    cache,_=setup(fixture_groups(),True)
    for m in ['EU','USA']:
        assert abs(cache['query_weights'][cache['markets']==m].sum()-.5)<1e-15

def test_prior_has_declared_weights_and_static_ignores_context():
    model={'theta':[[0.],[0.]],'contextual':False,'scaler':{}}
    a=predict_weights(model,np.ones(3));b=predict_weights(model,np.zeros(3))
    np.testing.assert_allclose(a,[.45,.35,.20],atol=1e-15)
    np.testing.assert_array_equal(a,b)

def test_contextual_simplex_and_sensitivity():
    model={'theta':[[0.,1.,0.,0.],[0.,0.,0.,0.]],'contextual':True,
           'scaler':{'median':[0,0,0],'mean':[0,0,0],'sd':[1,1,1]}}
    a=predict_weights(model,[0,0,0]);b=predict_weights(model,[1,0,0])
    assert b[0]>a[0] and np.isclose(b.sum(),1)
    assert (b>0).all()

def test_input_validation_and_training_missing_values():
    groups=fixture_groups();groups[0]['x'][0]=np.nan
    cache,scaler=setup(groups,True)
    assert np.isfinite(cache['design']).all()
    groups[0]['z'][0,0]=np.nan
    with pytest.raises(ValueError):setup(groups,True)

def test_three_start_fit_uses_training_only_and_serializable():
    import json
    model=fit_model(fixture_groups(),True,'pair',.1)
    json.dumps(model,allow_nan=False)
    assert len(model['starts'])==3
    assert model['converged']
    assert np.isclose(sum(predict_weights(model,[0,0,0])),1)
