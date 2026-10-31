from pathlib import Path
import numpy as np,pandas as pd,pytest
from common import atomic_bytes,eligibility,forward_labels,mature_mask,return_grades
from modeling import training_rows,target_values
from engine import run_portfolio,capped_inverse
from replay import configurations,metrics,BASELINE
from analysis import posterior_draws,block_contrasts
from router import build_scheduled_engine

def test_atomic_replace(tmp_path):
    p=tmp_path/'nested'/'x.bin';atomic_bytes(p,b'old');atomic_bytes(p,b'new')
    assert p.read_bytes()==b'new'
    assert len(list(p.parent.iterdir()))==1

def test_eligibility_no_prelisting_or_future_fill():
    ix=pd.bdate_range('2000-01-01',periods=330)
    c=pd.DataFrame({'A':100.,'B':np.nan},index=ix);c.loc[ix[100]:,'B']=100.
    v=pd.DataFrame(1.,index=ix,columns=c.columns);e=eligibility(c,v)
    assert not e.B.any() and not e.A.iloc[:252].any() and e.A.iloc[252]
    c.loc[ix[-1],'A']=np.nan;assert not eligibility(c,v).A.iloc[-1]

def test_eligibility_requires_observed_history_and_volume():
    ix=pd.bdate_range('2000-01-01',periods=330);c=pd.DataFrame(100.,index=ix,columns=['A']);v=c*0
    assert not eligibility(c,v).iloc[-1,0]
    v[:]=1.;c.iloc[50:200]=np.nan;assert not eligibility(c,v).iloc[-1,0]

def test_target_next_open_and_missing_open():
    ix=pd.bdate_range('2000-01-01',periods=80);o=pd.DataFrame({'A':np.arange(80)+100.},index=ix)
    x=forward_labels(o,ix[[0]])
    assert x.iloc[0].entry_date==ix[1] and x.iloc[0].exit_date_21==ix[22]
    assert np.isclose(x.iloc[0].fwd_ret_21,122/101-1)
    o.iloc[1,0]=np.nan;assert np.isnan(forward_labels(o,ix[[0]]).iloc[0].fwd_ret_21)

def test_unmatured_forecast_rows_retained():
    ix=pd.bdate_range('2000-01-01',periods=10);o=pd.DataFrame(100.,index=ix,columns=['A'])
    x=forward_labels(o,ix[[7]])
    assert len(x)==1 and pd.isna(x.iloc[0].exit_date_63) and np.isnan(x.iloc[0].fwd_ret_63)

def test_strict_cutoff_and_matched_multihorizon_mask():
    p=pd.DataFrame({'eligible':[True]*3,'signal_date':pd.to_datetime(['2018-10-01']*3)})
    for h in [21,42,63]:p[f'exit_date_{h}']=pd.to_datetime(['2018-12-31','2019-01-01',None]);p[f'fwd_ret_{h}']=[.1,.1,.1]
    assert mature_mask(p,2019).tolist()==[True,False,False]
    p.loc[0,'exit_date_63']=pd.Timestamp('2019-01-02')
    assert mature_mask(p,2019).iloc[0] and not mature_mask(p,2019,True).any()

def test_grading_economic_and_finite():
    r=np.array([-.2,-.01,0.,.01,.4]);y=return_grades(r)
    assert np.all(np.diff(y)>=0) and y.dtype.kind in 'iu' and y.min()>=0 and y.max()<=15
    assert y[-1]-y[-2]>y[3]-y[2]
    with pytest.raises(ValueError):return_grades(np.array([1.,np.nan]))

def fixture():
    p=pd.DataFrame({'signal_date':pd.to_datetime(['2018-10-31']*4+['2019-01-31']*4),'ticker':['A','B','C','D']*2,'eligible':True})
    for h in [21,42,63]:
        p[f'exit_date_{h}']=pd.to_datetime(['2018-12-28']*4+['2019-04-30']*4)
        p[f'fwd_ret_{h}']=[-.1,0,.05,.2]*2;p[f'target_rank_{h}']=[.25,.5,.75,1]*2
    return p

def test_training_purges_future_and_retains_same_multi_mask():
    p=fixture();p.loc[0,'exit_date_63']=pd.Timestamp('2019-01-02')
    n=[len(training_rows(p,2019,m)) for m in ['BASE_MATURE63','MULTI_453520','CONSENSUS_MULTI']]
    assert n==[3,3,3] and len(training_rows(p,2019,'BASE_D4'))==4

def test_test_outcomes_never_enter_training():
    p=fixture();a=training_rows(p,2019,'BASE_D4')
    p.loc[p.signal_date.dt.year==2019,'fwd_ret_21']=1e99
    pd.testing.assert_frame_equal(a,training_rows(p,2019,'BASE_D4'))

def test_target_consensus_penalizes_horizon_disagreement():
    p=fixture().iloc[:4].copy();p.loc[0,['target_rank_21','target_rank_42','target_rank_63']]=[.9,.9,0]
    y=target_values(p,'CONSENSUS_MULTI');expected=round(100*(.35*.9+.30*.9+.20*0+.15*0))
    assert y[0]==expected and y[-1]==100

def test_return_grading_query_local_and_labels_integer():
    p=fixture().iloc[:4].copy();a=target_values(p,'RETURN_D4');p.fwd_ret_21+=10
    np.testing.assert_array_equal(a,target_values(p,'RETURN_D4'));assert a.dtype.kind in 'iu'

def data(days=4,n=4):
    O=np.full((days,n),100.);L=O.copy();C=O.copy();ev=np.full(days,-1,dtype='int64');ev[0]=0
    s=np.array([[.9,.8,.3,.2]]);v=np.full_like(s,.2);r=np.ones(1,dtype='bool')
    return O,L,C,ev,s,v,r

def test_cash_without_events():
    a=list(data());a[3][:]=-1
    n,l=run_portfolio(*a);np.testing.assert_allclose(n,1);assert l[:,:7].sum()==0 and np.all(l[:,7:9]==1)

def test_buy_self_financing_fee():
    n,l=run_portfolio(*data(),fee=.003)
    np.testing.assert_allclose(n,1/1.003,rtol=1e-12)
    assert np.isclose(l[:,0].sum(),1/1.003) and np.isclose(l[:,1].sum(),.003/1.003)

def test_missing_new_open_cash_not_synthetic_fill():
    a=list(data());a[0][0,0]=np.nan
    n,l=run_portfolio(*a,fee=0)
    np.testing.assert_allclose(n,1);assert np.isclose(l[0,0],.5)

def test_missing_held_open_defers_rebalance():
    a=list(data());a[3][1]=1;a[4]=np.r_[a[4],[[.1,.2,.9,.8]]];a[5]=np.full((2,4),.2);a[6]=np.ones(2,dtype='bool');a[0][1,0]=np.nan
    n,l=run_portfolio(*a,fee=0);assert l[1,0]==0 and l[1,4]==1

def test_gap_stop_worse_open_and_no_same_day_reentry():
    a=list(data());a[0][1,0]=80;a[1][1,0]=79;a[2][1:,0]=80;a[3][1]=0
    n,l=run_portfolio(*a,fee=0,slip=0,stops=True)
    assert l[1,2]==1 and np.isclose(n[1],.9)
    a[0][2:,0]=120;a[2][2:,0]=120
    nn,ll=run_portfolio(*a,fee=0,slip=0,stops=True)
    assert np.isclose(nn[2],.9)

def test_intraday_stop_at_level_not_close():
    a=list(data());a[1][1,0]=90
    n,l=run_portfolio(*a,fee=0,slip=0,stops=True)
    assert l[1,2]==1 and np.isclose(n[1],.9725)

def test_no_future_close_controls_open_decision():
    a=list(data());n,l=run_portfolio(*a,fee=.001)
    b=[x.copy() for x in a];b[2][0,0]=200
    nn,ll=run_portfolio(*b,fee=.001)
    assert l[0,0]==ll[0,0] and nn[0]>n[0]

def test_half_regime_exposure():
    a=list(data());a[-1][:]=False
    n,l=run_portfolio(*a,fee=0,half=True);assert l[0,3]==.5 and l[0,0]==.5

def test_inverse_vol_cap_and_budget():
    w=capped_inverse(np.array([.01,.3,.4,.5,.6]));assert np.isclose(w.sum(),1) and w.max()<=.60000000001

def test_buffer_retains_previously_held_top2k():
    a=list(data());a[3][1]=1;a[4]=np.r_[a[4],[[.6,.5,.9,.8]]];a[5]=np.full((2,4),.2);a[6]=np.ones(2,dtype='bool')
    n,l=run_portfolio(*a,fee=0,buffer=True);assert l[1,0]==0
    n,l=run_portfolio(*a,fee=0,buffer=False);assert l[1,0]==2

def test_prefix_invariance_for_future_prices():
    a=list(data(8));a[2][2,0]=101
    n,l=run_portfolio(*a,fee=.001,stops=True)
    b=[v.copy() for v in a];b[0][4:]*=2;b[1][4:]*=.1;b[2][4:]*=3
    nn,ll=run_portfolio(*b,fee=.001,stops=True)
    np.testing.assert_array_equal(n[:4],nn[:4]);np.testing.assert_array_equal(l[:4],ll[:4])

def test_allocation_grid_has_exact_declared_cardinality():
    cs=configurations([f'N{i}' for i in range(21)])
    assert len(cs)==840 and all(c['k']==2 for c in cs if c['weight']=='MARG')

def test_metrics_keep_first_return_and_previous_close_for_subperiod():
    dates=pd.bdate_range('2020-01-01',periods=4);nav=np.array([1.1,1.21,1.21,1.21])
    a=metrics(nav,dates,'2020-01-01','2020-01-06');b=metrics(nav,dates,'2020-01-02','2020-01-06')
    assert np.isclose(a['ann_log'],np.log(1.21)*252/4)
    assert np.isclose(b['end_equity'],1.1)

def test_posterior_reproducible_and_joint_dependence_retained():
    x=np.array([[-.2,-.21],[-.1,-.11],[0,.01],[.1,.11],[.2,.21],[.3,.31]])
    a=posterior_draws(x);b=posterior_draws(x)
    np.testing.assert_array_equal(a,b)
    assert np.corrcoef(a.T)[0,1]>.7
    assert not np.isclose((a>0).all(1).mean(),(a[:,0]>0).mean()*(a[:,1]>0).mean(),atol=.001)

def test_posterior_rejects_missing_or_insufficient_pairs():
    with pytest.raises(ValueError):posterior_draws(np.zeros((2,2)))
    with pytest.raises(ValueError):posterior_draws(np.array([[0,1],[np.nan,0],[1,1]]))

def test_nonoverlap_blocks_and_annualization():
    m=pd.DataFrame(np.full((19,2),.01));x=block_contrasts(m,6)
    assert x.shape==(3,2);np.testing.assert_allclose(x,.12)

def test_constant_schedule_equals_static_engine_exactly():
    run=build_scheduled_engine();D=5;N=4
    O=np.full((D,N),100.);L=O.copy();C=O.copy();C[2,0]=105
    e=np.array([0,-1,-1,1,-1]);s=np.array([[.9,.8,.2,.1],[.8,.1,.9,.2]]);v=np.full_like(s,.2);r=np.array([True,False])
    cfg=np.tile([2,0,0,1,1],(D,1));which=np.zeros(2,dtype='int64')
    a,al=run_portfolio(O,L,C,e,s,v,r,k=2,half=True,stops=True)
    b,bl=run(O,L,C,e,s[None,:,:],v,r,cfg,which)
    np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(al,bl)

def test_rule_switch_carries_single_account_and_pays_new_trades():
    run=build_scheduled_engine();D=4;N=4
    O=np.full((D,N),100.);L=O.copy();C=O.copy();e=np.array([0,-1,1,-1])
    s=np.array([[[.9,.8,.2,.1],[.9,.8,.2,.1]],[[.1,.2,.9,.8],[.1,.2,.9,.8]]]);v=np.full((2,N),.2);r=np.ones(2,dtype='bool')
    cfg=np.tile([2,0,0,0,0],(D,1));which=np.array([0,1])
    nav,l=run(O,L,C,e,s,v,r,cfg,which,fee=.003)
    assert nav[2]<nav[1] and l[2,0]>1.9 and np.isclose(nav[0],1/1.003)
