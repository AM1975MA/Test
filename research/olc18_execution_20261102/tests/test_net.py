import numpy as np
from stop_engine import simulate
from test_engine import state

def test_net_equals_gross_without_friction():
 q=state();ev=np.zeros(6,bool)
 a=simulate(q,ev,contract='EOD_LOW',fee=0,friction=0)
 b=simulate(q,ev,contract='EOD_LOW_NET',fee=0,friction=0)
 np.testing.assert_allclose(a['nav'],b['nav'],rtol=0,atol=1e-14)
def test_net_alarm_is_not_stop_fill():
 q=state();alarms=[];fills=[]
 r=simulate(q,np.zeros(6,bool),contract='EOD_LOW_NET',alarm_log=alarms,event_log=fills)
 assert len(alarms)==1 and alarms[0]['signal_index']==2 and alarms[0]['action_index']==3
 assert not fills and r['ledger'][:,8].sum()==0
 assert r['ledger'][3,1]==.25
 assert r['primary_units'][2,0]>0
 assert r['primary_units'][3,0]<r['primary_units'][2,0]
def test_net_avoids_extra_roundtrip_cost():
 q=state();ev=np.zeros(6,bool)
 a=simulate(q,ev,contract='EOD_LOW',fee=.001,friction=.001)
 b=simulate(q,ev,contract='EOD_LOW_NET',fee=.001)
 assert b['nav'][-1]>a['nav'][-1]
 assert b['ledger'][:,6:8].sum()==0
def test_net_missing_next_quote_is_not_a_fill():
 q=state();q['observed'][3,0]=False;alarms=[]
 r=simulate(q,np.zeros(6,bool),contract='EOD_LOW_NET',alarm_log=alarms)
 assert len(alarms)==1
 assert r['ledger'][3,11]==1
 assert r['ledger'][3,3]==0
def test_net_alarm_independent_of_future_open():
 q=state();a=[];b=[];ev=np.zeros(6,bool)
 simulate(q,ev,contract='EOD_LOW_NET',alarm_log=a)
 q['O'][3:]*=1.4
 simulate(q,ev,contract='EOD_LOW_NET',alarm_log=b)
 assert a[0]==b[0]

def test_repeated_alarm_retargets_even_inside_existing_cooldown():
 q=state();q['L'][3,0]=90.;q['ud1'][3]=.8;q['uneg'][3]=.8;q['gap'][3,0]=-.06
 e=np.zeros(6,bool)
 a=simulate(q,e,contract='EOD_LOW',fee=0,friction=0)
 b=simulate(q,e,contract='EOD_LOW_NET',fee=0,friction=0)
 np.testing.assert_allclose(a['nav'],b['nav'],rtol=0,atol=1e-14)
 assert b['ledger'][4,3]==1
