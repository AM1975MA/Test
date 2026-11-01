import numpy as np,pandas as pd,pytest
from portfolio_adapter import adapt_state

def fixture():
    ds=pd.date_range('2021-01-01',periods=8,freq='B')
    q={'dates':ds.to_numpy(),'tickers':np.array(['C','A','B','CASH']), 'd1':np.zeros((1,8),int),'d2':np.ones((1,8),int),'weights':np.full((1,8),.5),'O':np.ones((8,4))}
    cal=pd.DataFrame({'signal_date':[ds[0],ds[3]],'entry_date':[ds[1],ds[4]]})
    f=pd.DataFrame({'signal_date':[ds[0]]*3+[ds[3]]*3,'ticker':['A','B','C']*2,'test':[.9,.8,.1,.1,.8,.9]})
    return q,cal,f

def test_state_has_no_signal_before_entry():
    q,cal,f=fixture();st,e,d=adapt_state(q,cal,f,'test')
    assert st['d1'][0,0]==-1 and st['d1'][0,1]==1 and st['d1'][0,4]==0
    assert st['d2'][0,1]==2 and e[4]

def test_adapter_never_changes_risk_prices_or_original_state():
    q,cal,f=fixture();st,e,d=adapt_state(q,cal,f,'test')
    np.testing.assert_array_equal(st['O'],q['O']);assert np.all(q['d1']==0)

def test_adapter_future_scores_do_not_change_past_targets():
    q,cal,f=fixture();a,_,_=adapt_state(q,cal,f,'test');f.loc[f.signal_date==cal.signal_date.iloc[-1],'test']=[.99,.1,.2];b,_,_=adapt_state(q,cal,f,'test')
    np.testing.assert_array_equal(a['d1'][:,:4],b['d1'][:,:4])

def test_signal_at_or_after_fill_rejected():
    q,cal,f=fixture();cal.loc[0,'entry_date']=cal.loc[0,'signal_date']
    with pytest.raises(ValueError):adapt_state(q,cal,f,'test')

def test_probability_is_not_used_as_capital_weight():
    q,cal,f=fixture();f['test']=[.99,.01,0.,.01,.99,0.];st,_,_=adapt_state(q,cal,f,'test')
    np.testing.assert_array_equal(st['weights'],np.full((1,8),.5))

def test_future_labels_are_not_an_eligibility_rule():
    q,cal,f=fixture();a,_,_=adapt_state(q,cal,f,'test');f['fwd_ret_63']=np.nan;f['TARGET']=np.nan;b,_,_=adapt_state(q,cal,f,'test')
    np.testing.assert_array_equal(a['d1'],b['d1'])
