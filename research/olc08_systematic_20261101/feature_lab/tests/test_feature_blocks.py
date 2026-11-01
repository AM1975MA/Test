import numpy as np
import pandas as pd
from feature_blocks import native_blocks,leadership_block,prune_training,sample_native

def bars(n=200):
    t=np.arange(n);c=np.exp(4+.002*t+.01*np.sin(t/3));o=c*np.exp(.002*np.cos(t/4))
    return pd.DataFrame({'Open':o,'Close':c},index=pd.bdate_range('2015-01-01',periods=n))

def test_prefix_has_no_future_information():
    f=bars();x=native_blocks(f)
    pd.testing.assert_frame_equal(x.iloc[:155],native_blocks(f.iloc[:155]))

def test_positive_scale_invariance():
    f=bars();pd.testing.assert_frame_equal(native_blocks(f),native_blocks(f*100),check_exact=False,rtol=1e-8,atol=1e-9)

def test_price_path_bounded_and_flat_contract():
    f=bars();f.loc[:]=10
    x=native_blocks(f)
    assert x.path_high_age63.iloc[-1]==0
    assert x.path_underwater63.iloc[-1]==0
    assert x.path_upside_concentration63.iloc[-1]==0
    assert x.path_downside_energy63.iloc[-1]==.5
    assert x.path_sign_persistence63.iloc[-1]==0
    assert x.session_overnight_share63.iloc[-1]==.5
    assert x.path_high_age63.iloc[:62].isna().all()

def test_manual_path_statistics():
    f=bars();x=native_blocks(f);r=np.log(f.Close).diff().iloc[-63:].to_numpy();c=f.Close.iloc[-63:].to_numpy()
    assert abs(x.path_high_age63.iloc[-1]-(62-np.flatnonzero(c==c.max())[-1])/62)<1e-12
    assert abs(x.path_underwater63.iloc[-1]-np.mean(c<np.maximum.accumulate(c)))<1e-12
    assert abs(x.path_downside_energy63.iloc[-1]-np.sum(np.minimum(r,0)**2)/np.sum(r*r))<1e-12

def test_session_decomposition_and_manual_efficiency():
    f=bars();g=np.log(f.Open/f.Close.shift());d=np.log(f.Close/f.Open)
    np.testing.assert_allclose((g+d).iloc[1:],np.log(f.Close).diff().iloc[1:],atol=1e-14)
    x=native_blocks(f)
    assert abs(x.session_intraday_efficiency63.iloc[-1]-d.iloc[-63:].sum()/d.iloc[-63:].abs().sum())<1e-12

def test_source_date_sampling_exact_no_future_quote():
    f=native_blocks(bars());dates=pd.Series([f.index[130],pd.NaT,f.index[155]+pd.Timedelta(hours=1)])
    s=sample_native(f,dates)
    pd.testing.assert_series_equal(s.iloc[0],f.iloc[130],check_names=False)
    assert s.iloc[1:].isna().all().all()

def panel():
    ds=pd.date_range('2015-01-31',periods=9,freq='ME');rows=[]
    for d in ds:
        for i,t in enumerate(['A','B','C']):rows.append(dict(signal_date=d,ticker=t,eligible=True,mom21=i+.01*d.month,mom63=2-i))
    return pd.DataFrame(rows)

def test_leadership_uses_current_and_past_only():
    p=panel();x=leadership_block(p);first=p.signal_date<=p.signal_date.unique()[5]
    pd.testing.assert_frame_equal(x.loc[first].reset_index(drop=True),leadership_block(p.loc[first]).reset_index(drop=True))
    last=x.loc[p.ticker.eq('C')].iloc[-1]
    assert last.lead_top21_persistence3==1
    assert last.lead_rank21_change3==0
    assert last.lead_rank21_turnover3==0

def test_missing_rank_does_not_skip_month():
    p=panel();p.loc[(p.ticker=='C')&(p.signal_date==p.signal_date.unique()[5]),'eligible']=False
    x=leadership_block(p);row=x.loc[(p.ticker=='C')&(p.signal_date==p.signal_date.unique()[6])].iloc[0]
    assert np.isnan(row.lead_rank21_change1)
    assert np.isnan(row.lead_top21_persistence3)

def test_pruning_ignores_target_and_prefers_percentiles():
    rng=np.random.default_rng(1);a=rng.normal(size=400)
    x=pd.DataFrame({'a':a,'a_pct':pd.Series(a).rank(pct=True),'b':rng.normal(size=400),'constant':3.,'future':a*100})
    keep,log=prune_training(x,['a','a_pct','b','constant'])
    assert keep==['a_pct','b'];assert len(log)==2
    x['future']=rng.normal(size=400)
    assert prune_training(x,['a','a_pct','b','constant'])[0]==keep

def test_pruning_no_false_redundancy_on_too_few_pairs():
    rng=np.random.default_rng(7);a=rng.normal(size=400)
    x=pd.DataFrame({'a':a,'b':a});x.loc[:149,'b']=np.nan
    keep,_=prune_training(x,['a','b']);assert keep==['a','b']

def test_pruning_contract_invalid_threshold():
    import pytest
    with pytest.raises(ValueError):prune_training(pd.DataFrame({'a':range(400)}),['a'],1.1)
