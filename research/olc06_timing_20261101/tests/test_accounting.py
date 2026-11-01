import numpy as np
from vector_engine import simulate
from test_engine import tiny
from accounting import decompose

def test_log_parts_reconstruct_every_interval_with_costs():
    q,e=tiny();q['O'][1:,0]=[102,103,104,101,105];q['PC']=np.vstack([q['O'][:1],q['O'][:-1]])
    r=simulate(q,e,policy='DELAY',fraction=3,fee=.001)
    a=decompose(q,r)
    truth=np.log(r['nav'][:-1]/r['ledger'][:-1,0])
    np.testing.assert_allclose(a['log_components'].sum(1),truth,atol=1e-13)
    np.testing.assert_allclose(a['before_units'][2],r['primary_units'][1],atol=0)

def test_delayed_hold_is_identified_as_outgoing_position():
    q,e=tiny();q['O'][3,0]=110
    r=simulate(q,e,policy='DELAY',fraction=3,fee=0)
    a=decompose(q,r)
    old=a['names'].index('old_only');new=a['names'].index('new_only')
    assert a['log_components'][2,old]>0 and a['log_components'][2,new]==0

def test_stopped_position_has_exact_separate_stop_effect():
    q,e=tiny();q['UH'][1,0]=True;q['ud1'][1]=.7;q['L'][1,0]=90
    r=simulate(q,e,fee=.001);a=decompose(q,r)
    assert a['log_components'][1,a['names'].index('stop_effect')]<0
    assert a['log_components'][1,a['names'].index('stop_fees')]<0
    np.testing.assert_allclose(a['log_components'].sum(1),np.log(r['nav'][:-1]/r['ledger'][:-1,0]),atol=1e-13)

def test_alias_free_pair_reorder_does_not_invent_old_new_change():
    q,e=tiny();q['d1'][:]=0;q['d2'][:]=1;q['d1'][0,2:]=1;q['d2'][0,2:]=0
    r=simulate(q,e,fee=0);a=decompose(q,r)
    assert (a['categories'][2,:2]==a['categories'][1,:2]).all()

def test_zero_return_log_allocation_is_finite():
    q,e=tiny();r=simulate(q,e,fee=0);a=decompose(q,r)
    assert np.isfinite(a['log_components']).all()
    assert np.max(abs(a['log_components']))==0
