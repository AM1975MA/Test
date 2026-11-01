import numpy as np
import pandas as pd
import pytest
from schema import canonical_matrix
from legacy_view import legacy_view
from recovery_core import rsi_domain, complete_checkpoint,valid_checkpoint
import layer_metrics as lm
import calibration as cal

def test_canonical_permutation_and_alias():
    f=pd.DataFrame({'b':[1.,2.],'a':[3.,np.nan],'a_alias':[3.,np.nan]})
    np.testing.assert_equal(canonical_matrix(f,['a','b'],{'a_alias':'a'}),canonical_matrix(f.iloc[:,::-1],['a','b'],{'a_alias':'a'}))
    np.testing.assert_equal(legacy_view(f,['a','b'],{'a_alias':'a'},['a_alias','b','a']),f[['a_alias','b','a']])
def test_alias_mismatch_rejected():
    with pytest.raises(ValueError):canonical_matrix(pd.DataFrame({'a':[1.],'copy':[2.]}),['a'],{'copy':'a'})
def test_unknown_column_rejected():
    with pytest.raises(ValueError):canonical_matrix(pd.DataFrame({'a':[1.],'mystery':[2.]}),['a'])
def test_missing_required_rejected():
    with pytest.raises(ValueError):canonical_matrix(pd.DataFrame({'b':[1.]}),['a'])
def test_rsi_domain():
    x=pd.DataFrame({'up':np.arange(1.,61.),'flat':np.ones(60),'down':np.arange(60.,0.,-1)})
    out=rsi_domain(x)
    assert out.iloc[-1].tolist()==[100.,50.,0.]
    assert out.iloc[:14].isna().all().all()
def test_checkpoint_corruption(tmp_path):
    (tmp_path/'model.json').write_text('{"weight":1}')
    complete_checkpoint(tmp_path,'v1',['model.json'])
    assert valid_checkpoint(tmp_path,'v1')
    (tmp_path/'model.json').write_text('{"weight":2}')
    assert not valid_checkpoint(tmp_path,'v1')
def test_checkpoint_missing_not_complete(tmp_path):
    with pytest.raises(FileNotFoundError):complete_checkpoint(tmp_path,'v1',['missing'])
    assert not (tmp_path/'COMPLETE.json').exists()
def test_checkpoint_escape_rejected(tmp_path):
    with pytest.raises(ValueError):complete_checkpoint(tmp_path,'v1',['../bad'])
def test_exact_hybrid_target():
    a=np.array([.2,.4]);b=np.array([.6,.8]);c=np.array([.3,1.])
    np.testing.assert_allclose(lm.hybrid_target(a,b,c),.45*a**1.5+.35*b**1.5+.20*c**1.5)
def test_missing_target_not_imputed():
    assert np.isnan(lm.hybrid_target([.2],[np.nan],[.8]))[0]
def test_economic_relevance_matches_definition():
    r=np.array([-.2,-.1,0,.05,.3]);sp=np.quantile(r,.9)-np.quantile(r,.1)
    np.testing.assert_array_equal(lm.economic_relevance(r),np.rint(7.5+7.5*np.clip((r-np.median(r))/sp,-1,1)))
def test_ndcg_perfect():
    assert lm.ndcg([3.,1.,2.],[3.,1.,2.],2)==pytest.approx(1.)
def test_ndcg_ties_expected_not_ticker_lottery():
    from sklearn.metrics import ndcg_score
    y=np.array([3.,1.,2.]);p=np.ones(3)
    assert lm.ndcg(y,p,2)==pytest.approx(ndcg_score(y[None,:],p[None,:],k=2))
def test_zero_ideal_not_perfect():
    assert np.isnan(lm.ndcg(np.zeros(3),[1,2,3],2))
def test_topk_tie_weights():
    np.testing.assert_allclose(lm.topk_weights([2.,1.,1.],2),[.5,.25,.25])
    np.testing.assert_allclose(lm.topk_weights(np.ones(5),2),np.ones(5)/5)
def test_months_have_equal_weight():
    d=pd.to_datetime(['2020-01-31']*2+['2020-02-28']*4)
    w=cal.month_weights(d)
    assert w[:2].sum()==pytest.approx(.5) and w[2:].sum()==pytest.approx(.5)
def sample_history():
    return pd.DataFrame({'signal_date':pd.to_datetime(['2019-11-30','2019-12-31','2020-01-31']),
    'exit_date_63':pd.to_datetime(['2019-12-31','2020-03-30','2020-04-30']),
    'TARGET':[.2,.5,.8],'ET_RAW':[.3,.5,.7],'XGB_RAW':[.2,.5,.8]})
def test_labels_mature_strictly_before_cutoff():
    a=cal.mature_history(sample_history(),pd.Timestamp('2020-01-01'))
    assert len(a)==1 and a.TARGET.iloc[0]==.2
    b=sample_history();b.loc[0,'exit_date_63']=pd.Timestamp('2020-01-01')
    assert cal.mature_history(b,pd.Timestamp('2020-01-01')).empty
def test_future_label_change_does_not_affect_fit_inputs():
    f=sample_history();g=f.copy();g.loc[1:,'TARGET']=999.
    pd.testing.assert_frame_equal(cal.mature_history(f,pd.Timestamp('2020-01-01')),cal.mature_history(g,pd.Timestamp('2020-01-01')))
def test_affine_monotonic_and_finite():
    x=np.linspace(.1,.9,100);y=.15+.7*x
    p=cal.fit_affine(x,y,np.ones(100)/100)
    pred=p['intercept']+p['coef'][0]*x
    assert (np.diff(pred)>=0).all() and np.isfinite(pred).all()
def test_affine_mean_shift_fit():
    x=np.array([.1,.3,.7,.9]);y=x+.2;p=cal.fit_affine(x,y,np.ones(4)/4)
    pred=p['intercept']+p['coef'][0]*x
    assert np.mean((pred-y)**2)<np.mean((x-y)**2)
def test_stack_nonnegative():
    rng=np.random.default_rng(3);x=rng.normal(size=(100,2));y=.4+.2*x[:,0]-.1*x[:,1]
    p=cal.fit_stack(x,y,np.ones(100)/100)
    assert len(p['coef'])==2 and min(p['coef'])>=0 and max(p['coef'])<=2

def test_compose_current_and_lags_exact():
    r=np.full((4,2),.6);et=np.array([[.1,.8],[.2,.7],[.3,.6],[.9,.2]]);x=et.copy()
    h,s,f=lm.compose(r,et,x)
    expected=(.4*et+.3*np.vstack([et[:1],et[:-1]])+.3*np.vstack([et[:1],et[:1],et[:-2]]))**1.1
    np.testing.assert_array_equal(s,expected)
    np.testing.assert_array_equal(f,.475*r+.525*expected)
def test_compose_does_not_read_future():
    r=np.ones((5,2))*.6;et=r.copy();x=r.copy()
    _,s,f=lm.compose(r,et,x);et[-1]=.9
    _,s2,f2=lm.compose(r,et,x)
    np.testing.assert_array_equal(s[:-1],s2[:-1]);np.testing.assert_array_equal(f[:-1],f2[:-1])
def test_compose_missing_not_zero():
    r=np.ones((4,2));et=r.copy();x=r.copy();et[1,0]=np.nan
    _,s,_=lm.compose(r,et,x)
    assert np.isnan(s[1,0])
    assert s[2,0]==pytest.approx(1.) and s[3,0]==pytest.approx(1.)

def test_pair_markets_by_month_not_exact_exchange_date():
    a=pd.Series([1.,2.],index=['2021-05-31','2021-06-30'])
    b=pd.Series([3.,4.],index=['2021-05-28','2021-06-30'])
    out=lm.paired_month_matrix({'EU':a,'USA':b})
    assert out.shape==(2,2) and out.loc[pd.Period('2021-05'),'USA']==3.
def test_reject_multiple_signals_in_month_for_monthly_test():
    a=pd.Series([1.,2.],index=['2021-05-28','2021-05-31'])
    with pytest.raises(ValueError):lm.paired_month_matrix({'EU':a})
