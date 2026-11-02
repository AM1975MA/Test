import numpy as np,pandas as pd
from revalue_memory import revalue
from core import compose_current
from parent_chrono import anchor_scale

def groups():
    rng=np.random.default_rng(160);out=[]
    for date in pd.date_range('2021-01-31',periods=4,freq='ME'):
        z=rng.uniform(0,1,(5,3));out.append(dict(date=date,z=z,anchor=z@np.array([.45,.35,.2]),tickers=np.array(list('ABCDE'))))
    return out

def test_constant_beta_commutes_with_existing_memory():
    g=groups();b=[np.array([.6,.1,.3])]*len(g)
    current=np.array([anchor_scale(x['z']@bb,x['anchor']) for x,bb in zip(g,b)])
    expected,_=compose_current(np.zeros_like(current),current)
    actual=revalue(g,b)
    np.testing.assert_allclose(actual,expected,atol=1e-15,rtol=0)

def test_revaluation_uses_current_not_past_beta():
    g=groups();b=[np.array([.95,.04,.01]),np.array([.01,.04,.95]),np.array([.2,.6,.2]),np.array([.3,.3,.4])]
    current=np.array([anchor_scale(x['z']@bb,x['anchor']) for x,bb in zip(g,b)])
    expected,_=compose_current(np.zeros_like(current),current)
    out=revalue(g,b)
    assert not np.allclose(out[1],expected[1])
    np.testing.assert_allclose(out[0],expected[0],atol=1e-15)

def test_future_forecasts_do_not_revise_previous_decisions():
    g=groups();b=[np.array([.6,.1,.3])]*len(g);a=revalue(g,b)
    g[-1]['z']=1-g[-1]['z'];b[-1]=np.array([.1,.1,.8]);c=revalue(g,b)
    for x,y in zip(a[:-1],c[:-1]):np.testing.assert_array_equal(x,y)

def test_missing_prior_ticker_not_filled_from_future():
    g=groups();g[0]['tickers']=g[0]['tickers'][:4];g[0]['z']=g[0]['z'][:4];g[0]['anchor']=g[0]['anchor'][:4]
    b=[np.array([.45,.35,.2])]*len(g);out=revalue(g,b)
    expected=anchor_scale(g[1]['z']@b[1],g[1]['anchor'])[-1]**1.1
    assert np.isclose(out[1][-1],expected)
