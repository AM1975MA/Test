import numpy as np,pandas as pd,json
from core import CONTEXT
from gating import fit_year

def panel():
 rows=[];rng=np.random.default_rng(13)
 for d in pd.date_range('2021-01-31','2026-06-30',freq='ME'):
  for m in ['EU','USA']:
   x=rng.normal(size=5);rows.append(dict(date=d,available=d+pd.Timedelta(days=92),market=m,delta=.01*x[0]+rng.normal(0,.005),recent=0.,**dict(zip(CONTEXT,x))))
 return pd.DataFrame(rows)

def test_first_adaptation_requires_dates_in_both_markets():
 p=panel();a=fit_year(p,2022,CONTEXT);b=fit_year(p,2023,CONTEXT)
 assert not a['active'];assert b['active'];assert min(b['model']['counts'].values())>=12

def test_future_labels_cannot_change_earlier_gate():
 p=panel();a=fit_year(p,2024,CONTEXT);q=p.copy();q.loc[q.available>=pd.Timestamp('2024-01-01'),'delta']=999
 b=fit_year(q,2024,CONTEXT);assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)

def test_inner_validation_training_strictly_before_validation():
 o=fit_year(panel(),2026,CONTEXT)
 assert o['active'];assert o['inner']
 for x in o['inner']:assert pd.Timestamp(x['train_max_available'])<pd.Timestamp(x['validation_year'],1,1)
 assert pd.Timestamp(o['max_train_available'])<pd.Timestamp('2026-01-01')

def test_no_market_specific_coefficients():
 o=fit_year(panel(),2025,CONTEXT);assert len(o['model']['coef'])==5;assert set(o['model']['counts'])=={'EU','USA'}
