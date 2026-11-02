import numpy as np
import pytest
from stop_engine import simulate
from vector_engine import simulate as parent

def state():
 O=np.array([[100.,100.,1.,1.],[100.,100.,1.,1.],[95.,100.,1.,1.],[94.,100.,1.,1.],[97.,100.,1.,1.],[98.,100.,1.,1.]])
 D,N=O.shape;PC=np.full_like(O,100.);PC[:,2:]=1.
 gap=np.zeros_like(O);gap[2,0]=-.05;ud=np.zeros(D);ud[2]=.8;L=O.copy();L[2,0]=94.
 C=O.copy();C[2,0]=96
 return dict(O=O,C=C,L=L,PC=PC,tickers=np.array(['A','B','BIL','SHV']),d1=np.zeros((1,D),int),d2=np.zeros((1,D),int),weights=np.ones((1,D)),g=np.ones(D),alt=np.full((1,D),-1),gap=gap,ud1=ud,uneg=ud.copy(),UH=np.ones_like(O,bool),SA=np.zeros_like(O,bool),observed=np.ones_like(O,bool),low_observed=np.ones_like(O,bool))

def test_legacy_arrays_exact():
 q=state();e=np.zeros(6,bool);new=simulate(q,e,contract='LEGACY');old=parent(q,e)
 for k in old:np.testing.assert_array_equal(new[k],old[k])
def test_previous_arrays_exact():
 q=state();e=np.zeros(6,bool);new=simulate(q,e,contract='PREVIOUS');old=parent(q,e,lag_systemic=True)
 for k in old:np.testing.assert_array_equal(new[k],old[k])
def test_prearm_independent_current_breadth():
 q=state();e=np.zeros(6,bool);q['gap'][:]=0;q['ud1'][:]=0;q['uneg'][:]=0
 r=simulate(q,e,contract='PREARM_WEAK',friction=.001)
 assert r['ledger'][2,8]==1
 assert r['ledger'][2,9]==0
def test_next_open_signal_and_sale_logged_once():
 q=state();ev=[];r=simulate(q,np.zeros(6,bool),contract='EOD_LOW',friction=.001,event_log=ev)
 assert len(ev)==1 and ev[0]['signal_index']==2 and ev[0]['execution_index']==3
 assert ev[0]['raw_price']==94
 assert r['ledger'][2,8]==1
 assert np.isclose(r['ledger'][:,6].sum(),sum(z['fee'] for z in ev))
 np.testing.assert_allclose(((r['primary_units'][:-1]+r['defensive_units'][:-1])*q['O'][1:]).sum(1)+r['free_cash'][:-1],r['nav'][:-1],rtol=0,atol=1e-14)
def test_fee_once_and_events_match():
 q=state();ev=[];r=simulate(q,np.zeros(6,bool),contract='PREARM_WEAK',friction=.005,event_log=ev)
 assert r['ledger'][:,8].sum()==len(ev)
 assert np.isclose(r['ledger'][:,6].sum(),sum(z['fee'] for z in ev))
 assert np.isclose(r['ledger'][:,7].sum(),sum(z['slippage'] for z in ev))
def test_eod_does_not_sell_recovery_close():
 q=state();r=simulate(q,np.zeros(6,bool),contract='EOD_CLOSE',friction=.001)
 assert r['ledger'][2,8]==0
def test_future_prefix():
 for mode in ['PREARM_WEAK','EOD_LOW','EOD_CLOSE']:
  q=state();a=simulate(q,np.zeros(6,bool),contract=mode,friction=.001)
  q['O'][4:]*=.7;q['C'][4:]*=.5;q['L'][4:]*=.6
  b=simulate(q,np.zeros(6,bool),contract=mode,friction=.001)
  np.testing.assert_array_equal(a['nav'][:3],b['nav'][:3])
  np.testing.assert_array_equal(a['primary_units'][:3],b['primary_units'][:3])
def test_unknown_contract_rejected():
 with pytest.raises(ValueError):simulate(state(),np.zeros(6,bool),contract='future')
