import sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_olc25 import feature_table,scores_for_trial


def test_control_and_no_future_columns():
    for market in ('EU','USA'):
        b,f,q,cal=feature_table(market)
        c=scores_for_trial(b,f,'AUTH',market)
        np.testing.assert_array_equal(c.FUSION.to_numpy(),b.FUSION.to_numpy())
        assert not any(str(c).startswith('fwd_') or str(c) in ['TARGET','exit_date_63'] for c in f.columns)
        for k in ['m126','m252','persist3']:
            v=f[k].dropna().to_numpy()
            assert (v >=0).all() and (v<=1).all()


def test_determinism_negative_control_and_missing_neutrality():
    b,f,_,_=feature_table('EU')
    for family,name in [('M126','m126'),('M252','m252'),('PERSIST3','persist3')]:
        x=scores_for_trial(b,f,f'{family}_W40_NULL25001','EU')
        y=scores_for_trial(b,f,f'{family}_W40_NULL25001','EU')
        np.testing.assert_array_equal(x.FUSION.to_numpy(),y.FUSION.to_numpy())
        p=(x.FUSION.to_numpy()-.6*b.FUSION.to_numpy())/.4
        mask=f[name].isna().to_numpy() & np.isfinite(b.FUSION.to_numpy())
        assert np.max(np.abs(p[mask]-.5))<1e-12
        for _,ix in f.groupby('date').indices.items():
            ix=np.asarray(ix)
            raw=f[name].to_numpy()[ix];v=raw[np.isfinite(raw)]
            if len(v):
                mask=np.isfinite(raw)&np.isfinite(b.FUSION.to_numpy()[ix])
                np.testing.assert_allclose(np.sort(p[ix][mask]),np.sort(raw[mask]),rtol=1e-12,atol=1e-12)


def test_past_data_only_and_3_month_persistence():
    for market in ['EU','USA']:
        b,f,q,cal=feature_table(market)
        dates=pd.DatetimeIndex(q['dates'])
        for d in pd.to_datetime(cal.signal_date)[1::9]:
            i=dates.get_indexer([d])[0]
            if i<0:continue
            # Only values on or before the signal can contribute to the momentum measurement.
            for lag in (126,252):
                if i<lag:continue
                sub=f[f.date==str(d.date())]
                x=q['C'].copy();x[i+1:]*=42
                tk={t:k for k,t in enumerate(q['tickers'])}
                for name in sub.ticker.head(5):
                    k=tk[name];v0=np.log(q['C'][i,k]/q['C'][i-lag,k]);v1=np.log(x[i,k]/x[i-lag,k]);
                    assert v0==v1
