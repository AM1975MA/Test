import numpy as np,pandas as pd,pytest
from ranking_core import utility,horizon_labels,mature_groups,score,pairs,objective,fit_beta,PRIOR

def test_utility_counts_increments_once():
 r=np.array([[.1,.1,.1],[0,.1,.1]])
 q=2**(-.5)
 np.testing.assert_allclose(utility(r),[np.log(1.1)/(1+q+.5),q*np.log(1.1)/(1+q+.5)])

def test_increments_are_ratios_not_differences():
 f=pd.DataFrame({'signal_date':pd.to_datetime(['2020-01-31']*3),'ticker':['A','B','C'],
 'fwd_ret_21':[.2,.0,.1],'fwd_ret_42':[.2,.1,.15],'fwd_ret_63':[.2,.21,.16],
 'target_rank_21':[1,1/3,2/3],'target_rank_42':[1,1/3,2/3],'target_rank_63':[2/3,1,1/3]})
 y=horizon_labels(f)
 np.testing.assert_allclose(y['I42'],np.array([1/3,1,2/3])**1.5)
 np.testing.assert_allclose(y['I63'],np.array([1/3,1,2/3])**1.5)
 np.testing.assert_allclose(y['C21'],np.array([1,1/3,2/3])**1.5)

def test_maturity_requires_all_peers_and_strict_cutoff():
 f=pd.DataFrame({'market':['EU']*4,'signal_date':pd.to_datetime(['2020-01-31']*2+['2020-02-28']*2),
 'exit_date_63':pd.to_datetime(['2020-04-30','2020-05-01','2020-06-01','2020-06-01']),
 'fwd_ret_21':[0.]*4,'fwd_ret_42':[0.]*4,'fwd_ret_63':[0.]*4})
 assert len(mature_groups(f,pd.Timestamp('2020-05-01')))==0
 assert len(mature_groups(f,pd.Timestamp('2020-05-02')))==1

def test_score_is_prior_linear_and_monotone():
 z=np.array([[.1,.2,.3],[.2,.2,.3]])
 np.testing.assert_array_equal(score(z,PRIOR),z@PRIOR)
 assert score(z,PRIOR)[1]>score(z,PRIOR)[0]

def test_invalid_simplex_and_future_returns_fail_closed():
 with pytest.raises(ValueError):score(np.ones((3,3)),np.array([1,1,1]))
 with pytest.raises(ValueError):utility(np.array([[-1,.2,.3]]))

def sample_groups():
 rng=np.random.default_rng(24);groups=[]
 for market,n in [('EU',3),('USA',5)]:
  for k in range(n):
   z=rng.uniform(size=(20,3));u=z[:,0]*.05
   groups.append({'market':market,'date':pd.Timestamp(2020,k+1,1),'z':z,'u':u})
 return groups

def test_pair_weights_equal_markets_and_dates():
 D,w,meta=pairs(sample_groups(),1)
 assert D.shape[1]==3 and np.isfinite(D).all()
 assert np.isclose(w.sum(),1)
 for m in ['EU','USA']:
  assert np.isclose(sum(x['total_weight'] for x in meta if x['market']==m),.5)

def test_pairwise_gradient_matches_finite_differences():
 D,w,_=pairs(sample_groups(),1.5);b=PRIOR.copy();loss,g=objective(b,D,w,.1)
 numeric=np.array([(objective(b+np.eye(3)[i]*1e-6,D,w,.1)[0]-objective(b-np.eye(3)[i]*1e-6,D,w,.1)[0])/2e-6 for i in range(3)])
 np.testing.assert_allclose(g,numeric,atol=1e-7)

def test_fitting_rewards_informative_head_without_leverage():
 out=fit_beta(sample_groups(),alpha=1,lam=.01)
 assert out['success'] and out['beta'][0]>.7
 assert min(out['beta'])>=0 and np.isclose(sum(out['beta']),1)
