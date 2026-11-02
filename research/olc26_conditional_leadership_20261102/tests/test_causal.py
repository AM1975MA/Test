import sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_olc26 import candidates_all,make_panel,train_cutoff,scores_one,FEATS


def test_strict_target_maturity_and_missing_support():
    frames,base,_,_=candidates_all()
    for market in ('EU','USA'):
        f=frames[market]
        assert f.signal_date.max()<pd.Timestamp('2026-07-01')
        assert all(col in f for col in FEATS+['future126','maturity_date'])
        for year in range(2021,2027):
            cutoff=pd.Timestamp(year,1,1)
            tr=f.loc[(f.maturity_date<cutoff)&f.future126.notna()&np.isfinite(f[FEATS]).all(axis=1)]
            assert (tr.maturity_date < cutoff).all()
            assert (tr.signal_date < tr.maturity_date).all()


def test_pooled_balancing_and_annual_fallback():
    frames,base,_,_=candidates_all()
    mdl,meta=train_cutoff(frames,2021,'POOL',None)
    assert mdl is None and meta['fallback']
    for year in range(2022,2027):
        mdl,meta=train_cutoff(frames,year,'POOL',None)
        assert mdl is not None and not meta['fallback']
        assert abs(meta['weight_by_market']['EU']-0.5)<1e-10
        assert abs(meta['weight_by_market']['USA']-0.5)<1e-10
        assert pd.Timestamp(meta['last_maturity'])<pd.Timestamp(year,1,1)


def test_original_2021_and_missing_feature_no_correction():
    frames,base,_,_=candidates_all()
    for t in ('POOL','STRAT'):
        out,models=scores_one(frames,base,t)
        for m in ('EU','USA'):
            f=frames[m]
            original=base[m]
            v=out[m]
            mask=(f.signal_date.dt.year==2021)|~np.isfinite(f[FEATS]).all(axis=1)
            np.testing.assert_array_equal(v.loc[mask,'FUSION'].to_numpy(),original.loc[mask,'FUSION'].to_numpy())
            assert np.array_equal(np.isfinite(v.FUSION),np.isfinite(original.FUSION))
            assert np.all(np.abs(v.FUSION.to_numpy()[np.isfinite(v.FUSION)]-original.FUSION.to_numpy()[np.isfinite(v.FUSION)])<=.05000000000001)


def test_deterministic_null_predictions():
    frames,base,_,_=candidates_all()
    a,_=scores_one(frames,base,'POOL_NULL26001')
    b,_=scores_one(frames,base,'POOL_NULL26001')
    for m in ('EU','USA'):
        np.testing.assert_array_equal(a[m].FUSION.to_numpy(),b[m].FUSION.to_numpy())
