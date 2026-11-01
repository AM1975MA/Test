import numpy as np
import pandas as pd
import pytest
from integration import memory,rerank_shortlist,build_scores

def frame():
    n=8;dates=np.repeat(pd.date_range('2021-01-31',periods=5,freq='ME'),n)
    rng=np.random.default_rng(12)
    return pd.DataFrame({'signal_date':dates,'ticker':list('ABCDEFGH')*5,
        'RETURN':rng.random(40),'ET_REG':rng.random(40),'XGB_REG':rng.random(40),
        'XGB_CLASS':rng.random(40),'ARCH_ET':rng.random(40),'ARCH_XGB':rng.random(40)})

def test_memory_exact_arithmetic():
    a=np.arange(20).reshape(5,4)/20
    expected=.4*a+.3*a[np.maximum(np.arange(5)-1,0)]+.3*a[np.maximum(np.arange(5)-2,0)]
    np.testing.assert_array_equal(memory(a),expected)

def test_memory_current_missing_not_revived():
    a=np.array([[.2,np.nan],[.8,.6],[np.nan,.9]])
    b=memory(a)
    assert np.isnan(b[2,0]) and b[1,1]==.6
    assert abs(b[2,1]-(.4*.9+.3*.6)/.7)<1e-15

def test_memory_future_invariance():
    a=np.random.default_rng(3).random((10,4));np.testing.assert_array_equal(memory(a)[:5],memory(a[:5]))

def test_shortlist_containment():
    a=np.array([.9,.8,.7,.6,.5,.4]);c=np.array([.1,.2,.3,.4,.5,.99])
    s=rerank_shortlist(a,c,k=5)
    assert set(np.argsort(s)[-2:])=={3,4}

def test_shortlist_boundary_tie_all_admitted():
    a=np.array([.9,.8,.7,.6,.5,.5]);c=np.arange(6)/6
    s=rerank_shortlist(a,c,k=5)
    assert set(np.argsort(s)[-2:])=={4,5}

def test_shortlist_missing_score_not_admitted():
    a=np.array([.9,.8,np.nan]);c=np.array([.1,.2,.99]);s=rerank_shortlist(a,c,2)
    assert np.isnan(s[2])

def test_duplicate_keys_rejected():
    f=frame();f=pd.concat([f,f.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError):build_scores(f)

def test_scores_future_prefix():
    f=frame();d=build_scores(f);short=build_scores(f[f.signal_date<=f.signal_date.unique()[2]])
    pd.testing.assert_frame_equal(d.iloc[:len(short)].reset_index(drop=True),short.reset_index(drop=True))

def test_rank_probability_same_native_order():
    f=frame();d=build_scores(f)
    for date,g in d.groupby('signal_date'):
        original=f[f.signal_date==date]
        assert list(g.sort_values('CLASS_NATIVE').ticker)==list(original.sort_values('XGB_CLASS').ticker)

def test_target_columns_not_used():
    f=frame();a=build_scores(f);f['TARGET']=1e9;f['exit_date_63']=pd.Timestamp('2030-01-01')
    pd.testing.assert_frame_equal(a,build_scores(f))

def test_probability_out_of_range_rejected():
    f=frame();f.loc[0,'XGB_CLASS']=1.2
    with pytest.raises(ValueError):build_scores(f)

def test_row_and_column_order_do_not_change_scores():
    f=frame();a=build_scores(f);b=build_scores(f.iloc[::-1,list(range(len(f.columns)))[::-1]])
    pd.testing.assert_frame_equal(a,b)
