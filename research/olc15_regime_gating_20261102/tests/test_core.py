import numpy as np,pandas as pd,pytest,json
from core import benchmark_context,leadership,recent_skill,mature_rows,market_weights,fit_gate,predict_gate,mix_scores,compose_current

def sample():
 return pd.DataFrame({'market':['EU']*20+['USA']*30,'x':np.r_[np.linspace(-2,2,20),np.linspace(-2,2,30)],'delta':np.r_[np.linspace(-.02,.02,20),np.linspace(-.02,.02,30)]})

def test_context_increasing_path_has_efficiency_one():
 s=pd.Series(np.exp(np.arange(180)*.001),index=pd.bdate_range('2020-01-01',periods=180));a=benchmark_context(s)
 assert abs(a.efficiency63.iloc[-1]-1)<1e-12;assert a.drawdown126.iloc[-1]==0
 assert a.iloc[:126].isna().any(axis=1).all()

def test_context_no_future_or_backfill():
 s=pd.Series(np.exp(np.cumsum(np.random.default_rng(11).normal(0,.01,220))),index=pd.bdate_range('2020-01-01',periods=220));a=benchmark_context(s)
 b=s.copy();b.iloc[180:]*=4;pd.testing.assert_frame_equal(a.iloc[:180],benchmark_context(b).iloc[:180])
 b=s.copy();b.iloc[20]=np.nan;assert benchmark_context(b).loc[b.index[20:147],'trend126'].isna().all()

def test_context_scale_invariant():
 s=pd.Series(np.exp(np.cumsum(np.random.default_rng(1).normal(0,.01,250))));a=benchmark_context(s);b=benchmark_context(s*1000)
 np.testing.assert_allclose(a,b,equal_nan=True,atol=1e-10)

def test_leadership_exact_alias_does_not_change_correlation():
 a=pd.Series([1,2,4,3.],index=list('abcd'));b=pd.Series([1,4,2,3.],index=list('abcd'));x=leadership(a,b)
 a['alias']=a['a'];b['alias']=b['a'];assert leadership(a,b)==x
 assert leadership(a,a)==1

def test_recent_skill_uses_availability_not_row_position():
 f=pd.DataFrame({'market':['EU']*5,'date':pd.date_range('2021-01-01',periods=5,freq='MS'),'available':pd.to_datetime(['2021-03-01','2021-04-01','2021-05-01','2021-06-01','2030-01-01']),'delta':[1.,2.,3.,4.,999.]})
 assert recent_skill(f,'2021-05-02','EU')==(2.,3)
 assert recent_skill(f,'2021-05-01','EU')==(0.,2)

def test_maturity_strict_incomplete_excluded():
 f=pd.DataFrame({'date':pd.to_datetime(['2021-01-01']*3),'available':pd.to_datetime(['2021-04-01','2022-01-01',None]),'delta':[1,2,np.nan]})
 assert mature_rows(f,'2022-01-01').index.tolist()==[0]

def test_market_weights_balance_unequal_row_counts():
 m=np.array(['EU']*2+['USA']*5);w=market_weights(m);assert np.isclose(w[:2].sum(),.5);assert np.isclose(w[2:].sum(),.5)
 with pytest.raises(ValueError):market_weights(['EU'])

def test_gate_monotonic_bounded_shared_and_serializable():
 f=sample();model=fit_gate(f,['x'],1);p=predict_gate(model,pd.DataFrame({'x':[-2,0,2]}));assert 0<p['g'][0]<p['g'][1]<p['g'][2]<1
 b=predict_gate(json.loads(json.dumps(model)),pd.DataFrame({'x':[-2,0,2]}));np.testing.assert_array_equal(p['g'],b['g'])

def test_fit_scaling_is_training_only():
 m=fit_gate(sample(),['x'],10);before=json.dumps(m,sort_keys=True);p=predict_gate(m,pd.DataFrame({'x':[1e10,np.nan]}));assert np.isfinite(p['g']).all();assert before==json.dumps(m,sort_keys=True)

def test_constant_gate_equals_training_mean():
 f=sample();f['delta']=.01;m=fit_gate(f,[],10);p=predict_gate(m,f)
 np.testing.assert_allclose(p['delta'],.01);np.testing.assert_allclose(p['g'],1/(1+np.exp(-2)))

def test_ridge_shrinkage_reduces_slope():
 f=sample();a=fit_gate(f,['x'],1);b=fit_gate(f,['x'],100);assert abs(b['coef'][0])<abs(a['coef'][0])

def test_mixture_endpoints_and_unknown_labels_not_inputs():
 a=np.array([.1,.9,.4]);b=np.array([.9,.1,.4]);np.testing.assert_array_equal(mix_scores(a,b,0),a);np.testing.assert_array_equal(mix_scores(a,b,1),b)
 np.testing.assert_allclose(mix_scores(a,b,.5),[.5,.5,.4])
 with pytest.raises(ValueError):mix_scores(a,b,1.01)

def test_composition_causal_prefix():
 r=np.full((5,3),.5);a=np.arange(15,dtype=float).reshape(5,3)/20;b=a.copy();b[3:]=1
 x=compose_current(r,a);y=compose_current(r,b)
 for u,v in zip(x,y):np.testing.assert_array_equal(u[:3],v[:3])
