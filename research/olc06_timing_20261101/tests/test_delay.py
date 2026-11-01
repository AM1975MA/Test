import numpy as np
import pytest
from vector_engine import simulate
from test_engine import tiny

def extended():
    q,e=tiny(); d=9
    for key,a in list(q.items()):
        if key=='tickers':continue
        if key in ['d1','d2','weights','alt']:q[key]=np.concatenate([a,np.repeat(a[:,-1:],d-6,axis=1)],axis=1)
        else:q[key]=np.concatenate([a,np.repeat(a[-1:],d-6,axis=0)],axis=0)
    q['dates']=np.arange(d).astype('datetime64[D]')
    return q,np.r_[e,[False]*3]

def test_delay_changes_all_at_third_not_before():
    q,e=tiny();r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    np.testing.assert_array_equal(r['targets'][2,:4],[.5,.5,0,0])
    np.testing.assert_array_equal(r['targets'][3,:4],[.5,.5,0,0])
    np.testing.assert_array_equal(r['targets'][4,:4],[0,0,.5,.5])
    assert r['ledger'][2,3]==0 and r['ledger'][3,3]==0 and r['ledger'][4,3]==1

def test_waiting_keeps_drifted_units_not_daily_equal_weights():
    q,e=tiny();q['O'][2:,0]=[120.,130.,140.,150.];q['PC']=np.vstack([q['O'][:1],q['O'][:-1]])
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    np.testing.assert_array_equal(r['primary_units'][1],r['primary_units'][2])
    np.testing.assert_array_equal(r['primary_units'][1],r['primary_units'][3])

def test_delay_one_matches_immediate():
    q,e=tiny();a=simulate(q,e,policy='DELAY',fraction=1,fee=.003);b=simulate(q,e,fee=.003)
    np.testing.assert_array_equal(a['nav'],b['nav'])

def test_first_entry_full_and_no_ghost_timer():
    q,e=tiny();q['d1'][:]=0;q['d2'][:]=1
    a=simulate(q,e,policy='DELAY',fraction=3,fee=.001);b=simulate(q,e,fee=.001)
    np.testing.assert_array_equal(a['nav'],b['nav']);assert a['primary_units'][0,:2].sum()>0

def test_new_target_restarts_delay():
    q,e=extended();q['d1'][0,3:]=0;q['d2'][0,3:]=2
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    np.testing.assert_array_equal(r['targets'][4,:4],[.5,.5,0,0])
    np.testing.assert_array_equal(r['targets'][5,:4],[.5,0,.5,0])

def test_permutation_does_not_restart_pending_delay():
    q,e=tiny();q['d1'][0,3:]=3;q['d2'][0,3:]=2
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    np.testing.assert_array_equal(r['targets'][4,:4],[0,0,.5,.5])

def test_risk_can_reduce_gross_while_delay_waits():
    q,e=tiny();q['g'][2:]=.25
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    np.testing.assert_allclose(r['primary_units'][2,:4]*100,[.125,.125,0,0],atol=1e-14)
    assert r['ledger'][2,1]==.25

def test_no_trade_at_unobserved_quote_on_due_date():
    q,e=extended();q['observed'][4,2]=False
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    assert r['ledger'][4,11]==1 and r['primary_units'][4,2]==0
    assert r['primary_units'][5,2]>0

def test_current_open_does_not_change_delay_target():
    q,e=tiny();a=simulate(q,e,policy='DELAY',fraction=3,fee=.001)
    q['O'][2,0]=500
    b=simulate(q,e,policy='DELAY',fraction=3,fee=.001)
    np.testing.assert_array_equal(a['targets'][2],b['targets'][2])

def test_delay_suffix_invariance():
    q,e=tiny();a=simulate(q,e,policy='DELAY',fraction=3,fee=.001)
    q['O'][4:]*=5;q['d1'][0,4:]=1
    b=simulate(q,e,policy='DELAY',fraction=3,fee=.001)
    np.testing.assert_array_equal(a['targets'][:4],b['targets'][:4])
    np.testing.assert_array_equal(a['nav'][:3],b['nav'][:3])

def test_zero_target_not_delayed():
    q,e=tiny();q['d1'][0,2:]=-1;q['d2'][0,2:]=-1
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    assert r['targets'][2].sum()==0 and r['primary_units'][2].sum()==0

def test_bad_delay_not_accepted():
    q,e=tiny()
    with pytest.raises(ValueError):simulate(q,e,policy='DELAY',fraction=2.5)
