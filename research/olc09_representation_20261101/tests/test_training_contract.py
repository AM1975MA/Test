import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from train_models import effective_parameters,CONFIGS
from bridge import ET_MODEL_KW,XGB_MODEL_KW,permute_block
import numpy as np
import pandas as pd

def test_only_declared_parameters_change():
    e,x=effective_parameters(CONFIGS['FIXED_PATH_S101'],45)
    for k,v in ET_MODEL_KW.items():
        if k!='max_features':assert e[k]==v
    for k,v in XGB_MODEL_KW.items():
        if k!='colsample_bytree':assert x[k]==v

def test_canonical_and_null_same_params():
    assert effective_parameters(CONFIGS['FIXED_PATH_S101'],45)==effective_parameters(CONFIGS['FIXED_NULL7101_S101'],45)

def test_all_three_shuffles_in_both_regimes():
    for regime in ['FIXED','ALL']:
        for seed in [7101,7102,7103]:assert f'{regime}_NULL{seed}_S101' in CONFIGS

def test_permutation_does_not_use_future_dates():
    f=pd.DataFrame({'signal_date':pd.to_datetime(['2021-01-31']*3+['2021-02-28']*3),'ticker':['A','B','C']*2,'p':[1.,2.,3.,4.,5.,6.],'q':[3.,4.,5.,6.,7.,8.]})
    a=permute_block(f,['p','q'],7101,'EU');b=permute_block(f.iloc[:3],['p','q'],7101,'EU')
    pd.testing.assert_frame_equal(a.iloc[:3],b)
    for _,g in a.groupby('signal_date'):assert len(np.unique(g.q-g.p))==1

def test_seed_sensitivity_is_symmetric():
    for seed in [211,307]:
        for prefix in ['REF42','FIXED_CORE','FIXED_PATH']:assert CONFIGS[f'{prefix}_S{seed}']['seed']==seed
