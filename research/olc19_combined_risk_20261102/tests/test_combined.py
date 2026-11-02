import numpy as np
import pytest
from combined_engine import simulate

def state(days=9):
    O=np.ones((days,4))*100.; O[:,2:]=1.
    L=O.copy();L[2,0]=94.;C=O.copy();C[2,0]=96.
    PC=np.ones_like(O)*100;PC[:,2:]=1.
    gap=np.zeros_like(O);ud=np.zeros(days);gap[2,0]=-.05;ud[2]=.6
    return dict(O=O,C=C,L=L,PC=PC,tickers=np.array(['A','B','BIL','SHV']),
      dates=np.arange(days).astype('timedelta64[D]')+np.datetime64('2021-01-01'),
      d1=np.zeros((1,days),int),d2=np.ones((1,days),int),weights=np.ones((1,days))*.5,
      g=np.ones(days),alt=np.full((1,days),-1),gap=gap,ud1=ud,uneg=ud,
      UH=np.ones_like(O,bool),SA=np.zeros_like(O,bool),observed=np.ones_like(O,bool),low_observed=np.ones_like(O,bool))

def run(mode,q=None,**kw):
    q=state() if q is None else q
    return simulate(q,np.zeros(len(q['O']),bool),contract=mode,**kw)

def test_base_has_neither_exit_nor_alarm():
    a=[];s=[];r=run('BASE',event_log=s,alarm_log=a)
    assert not a and not s and r['primary_units'][2,0]>0

def test_alarm_reduces_net_without_fast_exit():
    a=[];s=[];r=run('ALARM',event_log=s,alarm_log=a)
    assert len(a)==1 and not s
    assert r['primary_units'][2,0]>0
    assert r['ledger'][3,1]==.25

def test_fast_exit_without_market_permission():
    q=state();q['ud1'][:]=0;q['uneg'][:]=0
    s=[];r=run('FAST_LOCK3',q,event_log=s)
    assert len(s)==1 and r['primary_units'][2,0]==0

def test_lock_blocks_three_following_sessions():
    r=run('FAST_LOCK3')
    assert np.all(r['primary_units'][3:6,0]==0)
    assert r['primary_units'][6,0]>0

def test_lock_does_not_transfer_budget_to_other_name():
    r=run('FAST_LOCK3',fee=0,friction=0)
    assert r['ledger'][3,1]==.125  # half of reduced25%, not25% in surviving name
    assert r['targets'][3,1]==1.0

def test_combined_logs_both_but_no_duplicate_sale():
    s=[];a=[];r=run('COMBINED_LOCK3',event_log=s,alarm_log=a)
    assert len(s)==1 and len(a)==1
    assert r['ledger'][:,8].sum()==1
    assert np.isclose(r['ledger'][:,6].sum(),s[0]['fee'])

def test_nolock_control_rebuys_next_open():
    r=run('FAST_NOLOCK')
    assert r['primary_units'][2,0]==0 and r['primary_units'][3,0]>0

def test_current_proposal_cannot_bypass_lock():
    q=state();q['d2'][:,3:]=0;q['weights'][:,3:]=1
    r=run('FAST_LOCK3',q)
    assert not r['primary_units'][3:6].any()
    assert r['primary_units'][6,0]>0

def test_locked_ticker_cannot_be_alternate():
    q=state();q['g'][3:6]=.8;q['alt'][:,3:6]=0
    r=run('FAST_LOCK3',q)
    assert not r['defensive_units'][3:6,0].any()

def test_missing_reentry_quote_defers_order():
    q=state();q['observed'][6,0]=False
    r=run('FAST_LOCK3',q)
    assert r['ledger'][6,11]==1 and r['primary_units'][6,0]==0
    assert r['primary_units'][7,0]>0

def test_reentry_is_actual_trade_not_expiry():
    q=state();q['observed'][6,0]=False;orders=[]
    run('FAST_LOCK3',q,order_log=orders)
    entries=[z for z in orders if z['kind']=='REENTRY']
    assert len(entries)==1 and entries[0]['index']==7

def test_gap_exit_uses_worse_open():
    q=state();q['O'][2,0]=90.;q['L'][2,0]=88.;s=[]
    run('FAST_LOCK3',q,event_log=s)
    assert s[0]['raw_price']==90. and s[0]['fill_price']<90

def test_no_next_open_in_alarm_or_lock_decision():
    q=state();a=[];s=[];r=run('COMBINED_LOCK3',q,event_log=s,alarm_log=a)
    q['O'][3:]*=.7;q['C'][3:]*=.7;q['L'][3:]*=.7
    aa=[];ss=[];z=run('COMBINED_LOCK3',q,event_log=ss,alarm_log=aa)
    assert a[0]==aa[0]
    for k in ['signal_index','ticker','quantity','barrier','raw_price','lock_until']:
        assert s[0][k]==ss[0][k]
    np.testing.assert_array_equal(r['primary_units'][:3],z['primary_units'][:3])

def test_all_books_reconcile_next_open():
    for mode in ['BASE','ALARM','FAST_NOLOCK','COMBINED_NOLOCK','FAST_LOCK3','COMBINED_LOCK3']:
        q=state();r=run(mode,q)
        nav=((r['primary_units'][:-1]+r['defensive_units'][:-1])*q['O'][1:]).sum(1)+r['free_cash'][:-1]
        np.testing.assert_allclose(nav,r['nav'][:-1],atol=1e-14,rtol=0)
        assert np.max(np.abs(r['ledger'][:,25]))<1e-14

def test_unknown_contract_rejected():
    with pytest.raises(ValueError):run('OPTIMIZED_FUTURE')

def test_second_emergency_extends_only_affected_ticker_lock():
    q=state();q['L'][3,1]=94
    r=run('COMBINED_LOCK3',q)
    assert r['primary_units'][6,0]>0 and r['primary_units'][6,1]==0
    assert r['primary_units'][7,1]>0

def test_emergency_subsumes_same_barrier_alarm():
    for a,b in [('FAST_NOLOCK','COMBINED_NOLOCK'),('FAST_LOCK3','COMBINED_LOCK3')]:
        x=run(a);y=run(b)
        for k in ['nav','ledger','primary_units','defensive_units','free_cash','targets']:
            np.testing.assert_array_equal(x[k],y[k])

def test_new_ticker_does_not_inherit_another_ticker_lock():
    q=state();q['d1'][:,3:]=1;q['d2'][:,3:]=1;q['weights'][:,3:]=1
    r=run('FAST_LOCK3',q)
    assert r['ledger'][3,1]==.25 and r['primary_units'][3,1]>0
    assert r['primary_units'][3,0]==0

def test_both_stopped_names_zero_primary_budget_during_lock():
    q=state();q['L'][2,1]=94
    r=run('FAST_LOCK3',q)
    assert not r['primary_units'][3:6].any()
    assert np.all(r['ledger'][3:6,1]==0)
    assert r['primary_units'][6,:2].min()>0
