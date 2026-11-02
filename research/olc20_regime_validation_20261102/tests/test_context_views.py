import copy
import numpy as np
import pandas as pd
from context_views import transformed

def sample(n=30):
    out=[]
    for k,date in enumerate(pd.date_range('2019-01-31',periods=n,freq='ME')):
        for m,shift in [('EU',0),('USA',1000)]:
            out.append(dict(market=m,date=date,available=date+pd.Timedelta(days=70),full=True,
              x=np.array([shift+k,2*k,3*k],float),z=np.array([[.2,.3,.4],[.8,.7,.6]]),u=np.array([0.,1.])))
    return out

def test_identity_preserves_values_and_does_not_mutate():
    g=sample();old=copy.deepcopy(g);out,a=transformed(g)
    assert len(out)==len(g)
    for x,y,o in zip(out,g,old):
        np.testing.assert_array_equal(x['x'],y['x']);np.testing.assert_array_equal(y['x'],o['x'])

def test_moves_whole_vectors_jointly_across_markets():
    g=sample();out,a=transformed(g,seed=20001)
    assert a['changed']>0
    for k in range(0,len(g),2):
        e,u=out[k]['x'],out[k+1]['x']
        assert u[0]-e[0]==1000
        assert e[1]==2*e[0] and e[2]==3*e[0]
    assert sorted(x['x'][0] for x in out if x['market']=='EU')==list(range(30))

def test_blocks_preserve_local_order():
    out,a=transformed(sample(),seed=20002)
    vals=np.array([x['x'][0] for x in out if x['market']=='EU'])
    for block in vals.reshape(-1,6):np.testing.assert_array_equal(np.diff(block),np.ones(5))

def test_deterministic_and_no_outcome_dependence():
    g=sample();a,aa=transformed(g,seed=20001)
    other=copy.deepcopy(g)
    for x in other:x['u']*=999
    b,bb=transformed(other,seed=20001)
    assert aa==bb
    for x,y in zip(a,b):np.testing.assert_array_equal(x['x'],y['x'])

def test_training_subset_only_and_missing_market_month_unchanged():
    g=sample(35)[:48];g=[x for x in g if not(x['market']=='EU' and x['date'].month==4)]
    out,a=transformed(g,seed=20003)
    assert a['latest_donor']<=str(max(x['date'] for x in g))
    for x,y in zip(out,g):
        if x['market']=='USA' and x['date'].month==4:np.testing.assert_array_equal(x['x'],y['x'])
    assert a['unshared']>0

def test_omission_is_only_one_channel():
    g=sample();out,a=transformed(g,omit=1)
    for x,y in zip(out,g):
        assert x['x'][1]==0
        np.testing.assert_array_equal(x['x'][[0,2]],y['x'][[0,2]])
