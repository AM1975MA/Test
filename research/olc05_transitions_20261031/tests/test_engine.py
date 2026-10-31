import numpy as np
import pytest
from vector_engine import simulate

def tiny(prices=None):
 d=6;n=6
 O=np.ones((d,n))*100 if prices is None else np.asarray(prices,float)
 q={'O':O,'L':O.copy(),'C':O.copy(),'PC':np.vstack([O[:1],O[:-1]]),'gap':np.zeros((d,n)),
 'ud1':np.zeros(d),'uneg':np.zeros(d),'UH':np.zeros((d,n),bool),'SA':np.zeros((d,n),bool),
 'd1':np.array([[0,0,2,2,2,2]]),'d2':np.array([[1,1,3,3,3,3]]),'weights':np.full((1,d),.5),
 'g':np.ones(d),'alt':np.full((1,d),-1),'observed':np.ones((d,n),bool),'low_observed':np.ones((d,n),bool),
 'tickers':np.array(['A','B','C','D','EUR_CASH_A','EUR_CASH_B']),
 'dates':np.arange(d).astype('datetime64[D]')}
 return q,np.array([True,False,True,False,False,False])

def test_flat_prices_only_pay_trading_fees():
 q,e=tiny();r=simulate(q,e,fee=.001)
 assert (r['nav']<=1.).all();assert np.all(np.diff(r['nav'])<=1e-14)
 assert abs(r['nav'][0]-(1-.0005))<1e-12

def test_true_transition_coexists_old_and_new():
 q,e=tiny();r=simulate(q,e,policy='PARTIAL',fraction=.5,fee=0)
 np.testing.assert_allclose(r['primary_units'][2,:4]*100,[.25,.25,.25,.25])

def test_no_lookahead_in_transition_uses_previous_close():
 q,e=tiny();a=simulate(q,e,policy='PARTIAL',fraction=.5,fee=0)
 q['O'][2,0]=200
 b=simulate(q,e,policy='PARTIAL',fraction=.5,fee=0)
 np.testing.assert_array_equal(a['targets'][2],b['targets'][2])

def test_lambda_one_exactly_immediate():
 q,e=tiny();a=simulate(q,e,fee=.003);b=simulate(q,e,policy='PARTIAL',fraction=1,fee=.003)
 np.testing.assert_array_equal(a['nav'],b['nav'])

def test_missing_quote_prevents_trade():
 q,e=tiny();q['observed'][2,2]=False
 r=simulate(q,e,policy='PARTIAL',fraction=.5,fee=0)
 assert r['primary_units'][2,2]==0
 assert r['ledger'][2,11]==1

def test_equity_rebuilt_from_actual_units_next_open():
 q,e=tiny();q['O'][3:,2]*=1.2
 r=simulate(q,e,policy='PARTIAL',fraction=.5,fee=.001)
 actual=(r['primary_units'][:-1]*q['O'][1:]).sum(1)+(r['defensive_units'][:-1]*q['O'][1:]).sum(1)+r['free_cash'][:-1]
 np.testing.assert_allclose(actual,r['nav'][:-1],atol=1e-14)

def test_zero_fee_order_permutation_does_not_change_wealth():
 q,e=tiny();a=simulate(q,e,fee=0);q['d1'],q['d2']=q['d2'],q['d1'];b=simulate(q,e,fee=0)
 np.testing.assert_array_equal(a['nav'],b['nav'])

def test_slot_netting_bridge_is_explicit():
 q,e=tiny();q['d1'][0,2:]=1;q['d2'][0,2:]=0
 a=simulate(q,e,fee=.001,legacy_slots=True);b=simulate(q,e,fee=.001,legacy_slots=False)
 assert a['nav'][-1]<b['nav'][-1]
 assert b['ledger'][2,4]==0

def test_future_suffix_does_not_change_prefix():
 q,e=tiny();a=simulate(q,e,policy='PARTIAL',fraction=.5)
 q['O'][4:]*=8;q['d1'][0,4:]=3
 b=simulate(q,e,policy='PARTIAL',fraction=.5)
 np.testing.assert_array_equal(a['targets'][:4],b['targets'][:4])
 np.testing.assert_array_equal(a['nav'][:3],b['nav'][:3])

def test_conditional_stop_and_cooldown_still_apply():
 q,e=tiny();q['UH'][1,0]=True;q['ud1'][1]=.7;q['L'][1,0]=90
 r=simulate(q,e,fee=.001)
 assert r['ledger'][1,8]==1
 assert r['ledger'][2,1]==.25

def test_finite_transition_reaches_proposal_after_three_steps():
 q,e=tiny();r=simulate(q,e,policy='PHASE',fraction=3,fee=0)
 np.testing.assert_allclose(r['targets'][2,:4],[1/3,1/3,1/6,1/6],atol=1e-12)
 np.testing.assert_allclose(r['targets'][3,:4],[1/6,1/6,1/3,1/3],atol=1e-12)
 np.testing.assert_allclose(r['targets'][4,:4],[0,0,.5,.5],atol=1e-12)

def test_one_step_transition_equals_immediate():
 q,e=tiny();a=simulate(q,e,policy='PHASE',fraction=1,fee=.001);b=simulate(q,e,fee=.001)
 np.testing.assert_allclose(a['nav'],b['nav'],rtol=0,atol=1e-14)

def test_initial_full_entry_does_not_leave_fake_transition_clock():
 q,e=tiny();q['d1'][:]=0;q['d2'][:]=1;e[2]=False
 q['O'][1:,0]=np.array([101,103,102,105,108])
 q['PC']=np.vstack([q['O'][:1],q['O'][:-1]])
 a=simulate(q,e,policy='PHASE',fraction=5,fee=.001);b=simulate(q,e,fee=.001)
 np.testing.assert_array_equal(a['ledger'][:,3],b['ledger'][:,3])
 np.testing.assert_allclose(a['nav'],b['nav'],atol=1e-14,rtol=0)

def test_phase_does_not_restart_for_same_half_weight_pair_reordered():
 q,e=tiny();q['d1'][:]=0;q['d2'][:]=1
 q['O'][1:,0]=np.array([102,104,105,107,108]);q['PC']=np.vstack([q['O'][:1],q['O'][:-1]])
 a=simulate(q,e,policy='PHASE',fraction=5,fee=.001)
 q['d1'][0,2:]=1;q['d2'][0,2:]=0
 b=simulate(q,e,policy='PHASE',fraction=5,fee=.001)
 np.testing.assert_array_equal(a['targets'],b['targets'])
 np.testing.assert_array_equal(a['nav'],b['nav'])
