import numpy as np,pandas as pd
import pytest
from prepare import group_outcome

def frame():
 return pd.DataFrame({'ticker':['a','b','c'],'CUM_FIXED_MAPPED':[.9,.8,.2],'CUM_FIT_MAPPED':[.1,.8,.9],'fwd_ret_21':[.1,.02,-.05],'fwd_ret_42':[.2,.04,-.1],'fwd_ret_63':[.3,.06,-.15],'exit_date_63':pd.to_datetime(['2021-05-03','2021-05-04','2021-05-05'])})

def test_group_label_uses_all_peers_maturity():
 f=frame();o=group_outcome(f);assert o['available']==pd.Timestamp('2021-05-05');assert o['full'];assert o['delta']<0

def test_missing_future_does_not_drop_candidate_or_create_label():
 f=frame();f.loc[2,'fwd_ret_63']=np.nan;o=group_outcome(f);assert not o['full'];assert np.isnan(o['delta']);assert o['n']==3

def test_delta_independent_log_decomposition():
 f=frame();o=group_outcome(f);r=f[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy();q=2**-.5
 u=np.array([(np.log1p(a)+q*np.log((1+b)/(1+a))+q*q*np.log((1+c)/(1+b)))/(1+q+q*q) for a,b,c in r])
 assert abs(o['delta']-((u[1]+u[2])-(u[0]+u[1]))/2)<1e-15
