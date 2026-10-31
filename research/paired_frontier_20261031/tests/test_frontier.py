import numpy as np
import pandas as pd
from frontier_helpers import asof_snapshot, diversify_pair, systematic_cap, monthly_calibration

def test_snapshot_never_uses_next_observation():
 x=pd.DataFrame({'A':[1.,99.]},index=pd.to_datetime(['2024-12-30','2025-01-02']))
 out,source=asof_snapshot(x,pd.to_datetime(['2024-12-31']),max_age_days=5)
 assert out.iloc[0,0]==1 and source.iloc[0,0]==pd.Timestamp('2024-12-30')

def test_snapshot_rejects_stale_and_prelisting():
 x=pd.DataFrame({'A':[1.]},index=pd.to_datetime(['2024-12-20']))
 out,_=asof_snapshot(x,pd.to_datetime(['2024-12-01','2024-12-31']),5)
 assert out.isna().all().all()

def test_pair_drops_redundant_second_not_leader():
 s=np.array([.9,.8,.7]);c=np.array([[1,.98,.3],[.98,1,.2],[.3,.2,1.]])
 assert diversify_pair(s,c,False,[])==[0,2]

def test_pair_fallback_when_everything_correlated():
 assert diversify_pair(np.array([.9,.8,.7]),np.ones((3,3)),False,[])==[0,1]

def test_buffer_preserves_members_but_orders_by_score():
 assert diversify_pair(np.array([.9,.8,.7]),np.eye(3),True,[2,1],correlation_limit=None)==[1,2]

def test_systemic_weak_leader_alone_does_not_cut_market():
 cap=systematic_cap(np.array([-.08,0.,.01,.02]),np.array([.4,.8,.8,.8]),np.array([.8,.9,1.01,1.02]),False,np.ones(4),np.ones(4))
 np.testing.assert_array_equal(cap,np.ones(4))

def test_systemic_fast_reentry():
 cap=systematic_cap(np.array([-.06,-.02,.01,.02]),np.full(4,.8),np.array([.9,.95,.99,1.01]),False,np.ones(4),np.ones(4))
 np.testing.assert_array_equal(cap,[.5,.5,.75,1.])

def calibration_input():
 rng=np.random.default_rng(3);dates=pd.date_range('2017-01-31',periods=40,freq='ME');N=6
 a=rng.uniform(size=(40,N));b=rng.uniform(size=(40,N));f=np.stack([a-.5,b-.5],axis=2);y=.05*f[:,:,0]-.01*f[:,:,1]
 exitdates=dates+pd.Timedelta(days=35)
 return dates,exitdates,f,y

def test_calibration_prefix_future_invariant():
 ds,ex,f,y=calibration_input();p,a=monthly_calibration(ds,ex,f,y)
 yy=y.copy();yy[30:]+=50
 pp,aa=monthly_calibration(ds,ex,f,yy)
 np.testing.assert_allclose(p[:31],pp[:31],equal_nan=True)
 assert all(pd.Timestamp(r['max_exit'])<pd.Timestamp(r['signal_date']) for r in a if r['trained'])

def test_calibration_no_history_returns_predeclared_coldstart():
 ds,ex,f,y=calibration_input();p,a=monthly_calibration(ds,ex,f,y)
 np.testing.assert_allclose(p[0],f[0].mean(axis=1))
 assert a[0]['trained'] is False

def test_calibration_month_weight_is_one():
 ds,ex,f,y=calibration_input();p,a=monthly_calibration(ds,ex,f,y)
 for r in a:
  if r['trained']: assert abs(r['weight_sum']-r['train_months'])<1e-10
