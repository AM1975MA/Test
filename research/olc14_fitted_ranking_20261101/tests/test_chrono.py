import numpy as np,pandas as pd,pytest
from chrono_fit import anchor_scale,eligible,inner_folds,balanced_value,fit_year

def test_anchor_scale_keeps_order_and_anchor_marginal():
 raw=np.array([3.,1.,2.]);anchor=np.array([.1,.7,.3])
 np.testing.assert_array_equal(anchor_scale(raw,anchor),[.7,.1,.3])
 np.testing.assert_array_equal(anchor_scale(raw**3,anchor),anchor_scale(raw,anchor))

def test_anchor_ties_use_mean_occupied_values():
 np.testing.assert_allclose(anchor_scale([2.,2.,1.],[.1,.3,.7]),[.5,.5,.1])

def fake_groups():
 rng=np.random.default_rng(1);gs=[]
 for date in pd.date_range('2019-01-31','2023-12-31',freq='ME'):
  for m in ['EU','USA']:
   z=rng.uniform(size=(10,3));u=z[:,0]*.03+z[:,1]*.01
   gs.append(dict(market=m,date=date,available=date+pd.Timedelta(days=95),CUM=z,INC=z[:,::-1],u=u))
 return gs

def test_eligible_requires_strict_maturity_but_does_not_alter_values():
 gs=fake_groups();cut=pd.Timestamp('2021-01-01');out=eligible(gs,cut)
 assert out and all(g['available']<cut and g['date']<cut for g in out)
 assert max(g['date'] for g in out).month==8
 assert all(any(g is h for h in gs) for g in out)

def test_inner_folds_never_train_on_validation_outcomes():
 fs=inner_folds(fake_groups(),pd.Timestamp('2023-01-01'))
 assert len(fs)==2
 for f in fs:
  assert max(g['available'] for g in f['train'])<f['cutoff']
  assert min(g['date'] for g in f['valid'])>=f['cutoff']
  assert max(g['available'] for g in f['valid'])<pd.Timestamp('2023-01-01')

def test_market_balance_not_row_or_universe_size():
 gs=[dict(market='EU',u=np.array([0.,1.,2.])),dict(market='USA',u=np.array([0.,1.,2.])),dict(market='USA',u=np.array([0.,1.,2.]))]
 vals=balanced_value(gs,[np.array([0.,1.,2.])]*3)
 assert np.isclose(vals['EU'],.5) and np.isclose(vals['USA'],.5) and np.isclose(vals['criterion'],.5)

def test_future_outcomes_cannot_change_fitted_parameters():
 gs=fake_groups();cut=pd.Timestamp('2021-01-01');a=fit_year(gs,cut,'CUM')
 import copy
 changed=copy.deepcopy(gs)
 for g in changed:
  if g['available']>=cut:g['u']=g['u'][::-1]*1000
 b=fit_year(changed,cut,'CUM')
 np.testing.assert_array_equal(a['beta'],b['beta'])
 assert a['alpha']==b['alpha'] and a['lambda']==b['lambda']

def test_anchor_scale_cannot_introduce_new_ordering_ties():
 raw=np.array([3.,1.,2.]);anchor=np.array([.2,.2,.8])
 out=anchor_scale(raw,anchor)
 assert len(np.unique(out))==3
 np.testing.assert_array_equal(np.argsort(raw),np.argsort(out))
 np.testing.assert_allclose(np.sort(out),np.sort(anchor),rtol=0,atol=1e-12)
