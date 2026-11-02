import copy
import numpy as np
import pandas as pd
import pytest
from paths import P16
from experiment import load_groups,fit_year
from nested_validation import fit_annual

@pytest.fixture(scope='module')
def groups():return load_groups()[0]

def test_authentic_fit_matches_parent(groups):
    expected=fit_year(groups,2022,'top2',True)
    model,audit=fit_annual(groups,2022)
    np.testing.assert_allclose(model['theta'],expected['theta'],rtol=0,atol=1e-13)
    assert model['penalty']==expected['penalty']
    assert model['inner_fits']==expected['inner_fits']

def test_null_reselects_in_every_inner_fold_without_future_donors(groups):
    model,audit=fit_annual(groups,2023,seed=20001)
    assert len(model['cv'])==3
    assert model['inner_fits']==6
    assert len(audit['views'])==3
    for v in audit['views']:
        assert pd.Timestamp(v['latest_donor'])<pd.Timestamp(v['cutoff'])
        assert pd.Timestamp(v['max_training_exit'])<pd.Timestamp(v['cutoff'])
    assert audit['inner_validation_context']=='AUTHENTIC'

def test_future_targets_do_not_change_past_model(groups):
    original,a=fit_annual(groups,2021,seed=20002)
    changed=copy.deepcopy(groups)
    for g in changed:
        if pd.isna(g['available']) or g['available']>=pd.Timestamp('2021-01-01'):
            g['u']=np.nan_to_num(g['u'])*111+30
            g['returns']=np.nan_to_num(g['returns'])*5
    other,b=fit_annual(changed,2021,seed=20002)
    np.testing.assert_array_equal(original['theta'],other['theta'])
    assert a==b

def test_omission_and_penalty_grid_are_predeclared(groups):
    m,a=fit_annual(groups,2022,omit=1,grid_factor=2.)
    assert m['penalty'] in [.02,.2,2.]
    assert np.asarray(m['theta'])[:,2].tolist()==[0.,0.]
    assert all(v['omitted_channel']==1 for v in a['views'])
