import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from schema import canonical_matrix,column_parameters

def example():return pd.DataFrame({'a':[1.,np.nan,3.],'b':[9.,8.,7.]})

def test_named_order_is_canonical():
    f=example()
    np.testing.assert_array_equal(canonical_matrix(f[['b','a']],['a','b']),f[['a','b']].to_numpy())

def test_exact_known_aliases_do_not_change_matrix():
    f=example();f['alias_a']=f.a;f['alias_b']=f.b
    a=canonical_matrix(f[['alias_b','b','alias_a','a']],['a','b'],{'alias_a':'a','alias_b':'b'})
    np.testing.assert_array_equal(a,example().to_numpy())

def test_wrong_alias_values_rejected():
    f=example();f['alias']=f.a;f.loc[0,'alias']=2.
    with pytest.raises(ValueError,match='alias'):canonical_matrix(f,['a','b'],{'alias':'a'})

def test_different_nan_mask_rejected():
    f=example();f['alias']=f.a.fillna(0)
    with pytest.raises(ValueError,match='alias'):canonical_matrix(f,['a','b'],{'alias':'a'})

def test_unknown_column_rejected():
    f=example();f['unknown']=0.
    with pytest.raises(ValueError,match='Unknown'):canonical_matrix(f,['a','b'])

def test_missing_column_rejected():
    with pytest.raises(ValueError,match='Missing'):canonical_matrix(example()[['a']],['a','b'])

def test_duplicate_column_names_rejected():
    f=example();f.columns=['a','a']
    with pytest.raises(ValueError,match='Duplicate'):canonical_matrix(f,['a','b'])

def test_alias_cycles_rejected():
    with pytest.raises(ValueError,match='mapping'):canonical_matrix(example(),['a'],{'b':'b'})

def test_fixed_absolute_counts_for_all_widths():
    for p in [39,42,45,48]:
        et,xgb=column_parameters(p,'FIXED')
        assert et==16 and int(np.floor(np.float32(xgb)*p))==37

def test_all_columns_counts():
    for p in [39,42,45,48]:assert column_parameters(p,'ALL')==(1.0,1.0)

def test_legacy_fraction_kept():assert column_parameters(42,'LEGACY')==(.4,.9)

def test_bad_configuration_rejected():
    with pytest.raises(ValueError):column_parameters(20,'FIXED')
    with pytest.raises(ValueError):column_parameters(42,'invalid')
