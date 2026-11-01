import numpy as np
import pandas as pd
from evidence_math import circular_weights,score_month,daily_log

def test_bootstrap_preserves_constant_and_sample_size():
    w=circular_weights(48,6,200,101)
    np.testing.assert_allclose(w.sum(1),1)
    np.testing.assert_allclose(w@np.full((48,2),[.01,-.02]),np.tile([.01,-.02],(200,1)))
    np.testing.assert_array_equal(w,circular_weights(48,6,200,101))

def test_monthly_top2_and_excess():
    x=pd.DataFrame({'s':[4,3,2,1],'r':[.4,.2,.1,-.1]})
    q=score_month(x,'s','r')
    assert abs(q['top2_return']-.3)<1e-12
    assert abs(q['top2_excess']-.15)<1e-12
    assert q['n']==4 and q['rank_ic']==1

def test_missing_outcomes_excluded_only_from_evaluation():
    x=pd.DataFrame({'s':[4,3,2,1],'r':[np.nan,.2,.1,-.1]})
    q=score_month(x,'s','r');assert q['n']==3
    assert x.s.notna().all() and x.r.isna().sum()==1

def test_daily_accounting_first_and_flat_final():
    np.testing.assert_allclose(daily_log(np.array([1.1,1.21,1.21])),[np.log(1.1),np.log(1.1),0],atol=1e-15)
