import sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_olc27 import data, fit_cutoff, choose_top5, apply_swaps,FEATURES

def test_maturity_and_market_weight():
    frames,base=data()
    for year in range(2021,2027):
        m,meta=fit_cutoff(frames,year,'LONG_POOL',None)
        if m is not None:
            assert pd.Timestamp(meta['last_maturity'])<pd.Timestamp(year,1,1)
            assert abs(meta['groups_weight']['EU']-.5)<1e-12
            assert abs(meta['groups_weight']['USA']-.5)<1e-12
    assert fit_cutoff(frames,2021,'LONG_POOL',None)[0] is None

def test_top5_rule_and_missing():
    s=pd.DataFrame({'ticker':list('ABCDEF'),'FUSION':[.90,.86,.84,.82,.80,.78]})
    p=pd.Series([.20,.10,.40,.35,.36,.9])
    want,swap=choose_top5(s,p)
    assert set(want)=={'A','C'} and swap['drop']=='B' and swap['add']=='C'
    p.iloc[1]=np.nan
    want,swap=choose_top5(s,p)
    assert want==['A','B'] and swap is None

def test_auth_and_2021_fallback():
    frames,base=data()
    out,changes,preds,models=apply_swaps(frames,base,'LONG_POOL')
    for m in ('EU','USA'):
        a=base[m];b=out[m]
        mask=frames[m].signal_date.dt.year==2021
        np.testing.assert_array_equal(a.loc[mask,'FUSION'].to_numpy(),b.loc[mask,'FUSION'].to_numpy())
        assert np.array_equal(np.isfinite(a.FUSION),np.isfinite(b.FUSION))
        assert all(x['add']!=x['drop'] for x in changes[m])

def test_deterministic_null():
    f,b=data()
    a,_,_,_=apply_swaps(f,b,'LONG_POOL_NULL27001')
    c,_,_,_=apply_swaps(f,b,'LONG_POOL_NULL27001')
    for m in ('EU','USA'):np.testing.assert_array_equal(a[m].FUSION.to_numpy(),c[m].FUSION.to_numpy())

def test_future_outcome_perturbation_cannot_change_earlier_fit():
    frames,_=data()
    _,reference=fit_cutoff(frames,2024,'LONG_POOL',None)
    modified={m:x.copy() for m,x in frames.items()}
    cutoff=pd.Timestamp(2024,1,1)
    for m in ('EU','USA'):
        f=modified[m]
        mask=f.maturity_date.isna()|(f.maturity_date>=cutoff)
        f.loc[mask,'future126']=np.where(np.arange(int(mask.sum()))%2==0,0.01,0.99)
    _,altered=fit_cutoff(modified,2024,'LONG_POOL',None)
    for key in ['n_rows','months','coefs','intercept','last_maturity','labels_positive','groups_weight']:
        assert reference[key]==altered[key],key

def test_candidate_decisions_exactly_match_precommitted_swap_log():
    root=Path(__file__).resolve().parents[1]/'results'
    for market in ('EU','USA'):
        baseline=pd.read_csv(root/'AUTH'/f'{market}_DECISIONS.csv').set_index('signal_date')
        for trial in ('AUTH_ONLY','LONG_POOL','LONG_STRAT','LONG_POOL_NULL27001','LONG_POOL_NULL27002','LONG_POOL_NULL27003'):
            result=pd.read_csv(root/trial/f'{market}_DECISIONS.csv').set_index('signal_date')
            assert baseline.index.equals(result.index)
            changed={d for d in baseline.index if set(baseline.loc[d,['ticker1','ticker2']])!=set(result.loc[d,['ticker1','ticker2']])}
            logged=set(pd.read_csv(root/trial/f'{market}_SWAPS.csv').date)
            assert changed==logged
            base_scores=pd.read_csv(root/'AUTH'/f'{market}_SCORES.csv.gz')
            for d in logged:
                rows=base_scores[base_scores.signal_date==d].sort_values(['FUSION','ticker'],ascending=[False,True])
                assert set(result.loc[d,['ticker1','ticker2']]).issubset(set(rows.head(5).ticker))
