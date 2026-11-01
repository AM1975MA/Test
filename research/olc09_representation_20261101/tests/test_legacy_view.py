import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np,pandas as pd,pytest
from legacy_view import legacy_view

def test_legacy_order_and_alias_multiplicity_preserved():
    f=pd.DataFrame({'b':[2.,3.],'a':[1.,np.nan]});f['aa']=f.a
    a=legacy_view(f[['aa','b','a']],['a','b'],{'aa':'a'},['a','aa','b'])
    np.testing.assert_array_equal(a,f[['a','aa','b']].to_numpy())

def test_compressed_and_expanded_have_same_legacy_matrix():
    f=pd.DataFrame({'a':[1.,np.nan],'b':[2.,3.]});g=f.copy();g['aa']=f.a;g['additional']=f.b
    aliases={'aa':'a','additional':'b'}
    np.testing.assert_array_equal(legacy_view(f,['a','b'],aliases,['a','aa','b']),legacy_view(g[['b','aa','additional','a']],['a','b'],aliases,['a','aa','b']))

def test_unknown_legacy_view_name_rejected():
    with pytest.raises(ValueError):legacy_view(pd.DataFrame({'a':[1.]}),['a'],{},['z'])
