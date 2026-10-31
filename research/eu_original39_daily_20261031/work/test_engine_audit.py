import os
from research_common import B
os.environ['RECONCILIATION_ROOT']=str(B)
from test_reconciliation import tiny_inputs
from engine_prepare import stage
import numpy as np

def test_unchanged_equity_when_quotes_observed():
 from audit_engine import simulate_audited
 a=tiny_inputs();x=stage.simulate_arch.py_func(*a);y=simulate_audited.py_func(*a)
 for p,q in zip(x,y[:4]):np.testing.assert_array_equal(p,q)
 assert np.max(abs(y[4][0,:-1,46]))<1e-12

def test_missing_new_quote_prevents_trade():
 from audit_engine import simulate_audited
 a=tiny_inputs();obs=np.ones_like(a[3],bool);obs[0,0]=False
 y=simulate_audited.py_func(*a,observed=obs,strict_quotes=True)
 assert y[4][0,0,24]==1 and y[4][0,0,4]==0
 assert y[4][0,0,25]==-1
 assert np.max(abs(y[4][0,:-1,46]))<1e-12
