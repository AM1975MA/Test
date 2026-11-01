import numpy as np
import pandas as pd
import pytest
from diagnostic_primitives import permute_block,canonicalize,restore_columns

def sample():
    return pd.DataFrame({'signal_date':np.repeat(pd.to_datetime(['2020-01-31','2020-02-28','2020-03-31']),5),'ticker':['A','B','C','D','E']*3,'x':np.arange(15.),'z':np.arange(15.)*3,'label':np.arange(15.)*100})

def test_null_preserves_joint_block_and_labels():
    x=sample();out=permute_block(x,['x','z'],7101,'EU')
    pd.testing.assert_frame_equal(x[['signal_date','ticker','label']],out[['signal_date','ticker','label']])
    for d,g in x.groupby('signal_date'):
        assert sorted(map(tuple,g[['x','z']].values))==sorted(map(tuple,out.loc[g.index,['x','z']].values))
    assert not x.x.equals(out.x)
    assert np.array_equal(out.z,3*out.x)

def test_null_is_causal_and_reproducible():
    x=sample();out=permute_block(x,['x','z'],7101,'EU')
    pd.testing.assert_frame_equal(out.iloc[:10],permute_block(x.iloc[:10],['x','z'],7101,'EU'))
    pd.testing.assert_frame_equal(out,permute_block(x,['x','z'],7101,'EU'))

def test_lossless_compression_preserves_order_missing_and_dtype():
    x=pd.DataFrame({'a':np.array([1.,np.nan,3.]),'b':[2,4,6],'duplicate':[1.,np.nan,3.]})
    z,meta=canonicalize(x,{'duplicate':'a'})
    assert list(z.columns)==['a','b']
    pd.testing.assert_frame_equal(restore_columns(z,meta),x)

def test_lossless_compression_rejects_nonidentical_or_unknown_alias():
    x=pd.DataFrame({'a':[1.,2.],'b':[1.,3.]})
    with pytest.raises(ValueError):canonicalize(x,{'b':'a'})
    with pytest.raises(ValueError):canonicalize(x,{'absent':'a'})
