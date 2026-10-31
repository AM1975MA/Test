import numpy as np
import pandas as pd
from relative_information import history,relative_path,peer_context

def data():
 rng=np.random.default_rng(4);d=pd.bdate_range('2017-01-02',periods=330)
 m=rng.normal(.0005,.01,len(d));r=m[:,None]+rng.normal(0,.003,(len(d),7))
 return pd.DataFrame(np.exp(r.cumsum(0)),index=d,columns=list('ABCDEFG'))

def weights():return np.array([.6,.4,0,0,0,0,0]),np.array([0,0,.5,.5,0,0,0])

def test_no_future_history_and_no_backfill():
 c=data();c.iloc[:25,0]=np.nan;asof=c.index[270]
 h=history(c,asof)
 assert h.index.max()==asof and h.iloc[:25,0].isna().all()

def test_relative_future_prefix_invariance():
 c=data();t=c.index[270];o,n=weights();x=relative_path(c,t,o,n)
 c.loc[c.index>t]*=10
 np.testing.assert_allclose(x,relative_path(c,t,o,n),atol=0,rtol=0)

def test_ticker_price_scale_invariance():
 c=data();o,n=weights();x=relative_path(c,c.index[-1],o,n)
 np.testing.assert_allclose(x,relative_path(c*np.arange(1,8),c.index[-1],o,n),atol=1e-12)

def test_identical_basket_no_relative_signal():
 c=data();o,_=weights();x=relative_path(c,c.index[-1],o,o)
 np.testing.assert_allclose(x,np.zeros(12),atol=1e-12)

def test_long_missing_quote_remains_missing_not_fabricated():
 c=data();o,n=weights();c.iloc[-8:,0]=np.nan
 assert np.isnan(relative_path(c,c.index[-1],o,n)).all()

def test_peer_excludes_self_and_support():
 c=data();features,peers=peer_context(c,c.index[-1])
 assert features.shape==(7,9)
 assert all(i not in p and len(p)==5 for i,p in enumerate(peers))
 assert np.isfinite(features).all()

def test_peer_future_prefix_invariance():
 c=data();d=c.index[270];x,p=peer_context(c,d);c.loc[c.index>d]*=np.arange(1,8)*100
 y,q=peer_context(c,d);np.testing.assert_allclose(x,y,rtol=0,atol=0);assert p==q

def test_peer_insufficient_history_nan():
 c=data().iloc[:50];x,p=peer_context(c,c.index[-1])
 assert np.isnan(x).all() and all(not q for q in p)
