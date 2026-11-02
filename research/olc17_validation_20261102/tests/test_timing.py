import numpy as np
import pytest
from vector_engine import simulate as parent
from validated_engine import simulate

def state():
    O=np.array([[100.,100.,1.,1.],[100.,100.,1.,1.],[95.,100.,1.,1.],[94.,100.,1.,1.],[97.,100.,1.,1.],[98.,100.,1.,1.]])
    D,N=O.shape;PC=np.full_like(O,100.);PC[:,2:]=1.
    gap=np.zeros_like(O);gap[2,0]=-.05;ud=np.zeros(D);ud[2]=.8
    L=O.copy();L[2,0]=94.
    return dict(O=O,L=L,PC=PC,tickers=np.array(['A','B','BIL','SHV']),
        d1=np.zeros((1,D),int),d2=np.zeros((1,D),int),weights=np.ones((1,D)),g=np.ones(D),
        alt=np.full((1,D),-1),gap=gap,ud1=ud,uneg=ud.copy(),UH=np.ones_like(O,bool),SA=np.zeros_like(O,bool),
        observed=np.ones_like(O,bool),low_observed=np.ones_like(O,bool))

def equal(a,b):
    for k in b: np.testing.assert_array_equal(a[k],b[k])

def test_legacy_parity():
    q=state();e=np.zeros(6,bool);e[0]=True
    equal(simulate(q,e),parent(q,e))

def test_lag_parity():
    q=state();e=np.zeros(6,bool);e[0]=True
    equal(simulate(q,e,exposure_timing='PREVIOUS',stop_timing='PREVIOUS'),parent(q,e,lag_systemic=True))

def test_stop_delay_does_not_delay_exposure_signal():
    q=state();e=np.zeros(6,bool);a=simulate(q,e,stop_timing='PREVIOUS')
    assert a['ledger'][2,9]==1
    assert a['ledger'][2,8]==0

def test_exposure_delay_keeps_current_stop_signal():
    q=state();e=np.zeros(6,bool);a=simulate(q,e,exposure_timing='PREVIOUS')
    assert a['ledger'][2,9]==0
    assert a['ledger'][2,8]==1

def test_disable_gap_layer_retains_gross_limit():
    q=state();q['g'][:]=.7;a=simulate(q,np.zeros(6,bool),exposure_timing='OFF',stop_timing='OFF')
    assert np.max(a['ledger'][:-1,1])==.7
    assert a['ledger'][:,8:10].sum()==0

def test_future_cannot_change_past_holdings():
    q=state();e=np.zeros(6,bool);a=simulate(q,e,exposure_timing='PREVIOUS',stop_timing='PREVIOUS')
    q['gap'][4:]=-.9;q['ud1'][4:]=1.;q['L'][4:]*=.5;q['O'][4:]*=.7
    b=simulate(q,e,exposure_timing='PREVIOUS',stop_timing='PREVIOUS')
    np.testing.assert_array_equal(a['primary_units'][:4],b['primary_units'][:4])
    np.testing.assert_array_equal(a['nav'][:3],b['nav'][:3])

def test_input_mode_rejects_typos():
    with pytest.raises(ValueError):simulate(state(),np.zeros(6,bool),stop_timing='future')

def test_current_low_not_used_for_open_exposure():
    q=state();e=np.zeros(6,bool);a=simulate(q,e);q['L'][2]*=.1;b=simulate(q,e)
    assert a['ledger'][2,1]==b['ledger'][2,1]

def test_open_units_reconcile_capital():
    q=state();r=simulate(q,np.zeros(6,bool),exposure_timing='PREVIOUS',stop_timing='PREVIOUS')
    nv=((r['primary_units'][:-1]+r['defensive_units'][:-1])*q['O'][1:]).sum(1)+r['free_cash'][:-1]
    np.testing.assert_allclose(nv,r['nav'][:-1],atol=1e-14,rtol=0)
