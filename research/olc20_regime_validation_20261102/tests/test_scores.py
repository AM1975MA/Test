import copy,json
import numpy as np
import pandas as pd
from paths import P16
from experiment import load_groups,readcsv
from score_validation import build_scores

def check_parent(name):
    g,f,c=load_groups()
    models={year:json.loads((P16/f'models/{year}_{name}.json').read_text()) for year in range(2021,2027)}
    out,trace=build_scores(g,f,c,models)
    for m in ['EU','USA']:
        ref=readcsv(P16/f'results/{m}_SCORES.csv.gz')
        for stage in ['CURRENT','SMOOTH','FUSION']:
            np.testing.assert_allclose(out[m][stage],ref[name+'_REVALUE_'+stage],atol=2e-14,rtol=0,equal_nan=True)
        pd.testing.assert_frame_equal(out[m][['signal_date','ticker']],ref[['signal_date','ticker']])
    return g,f,c,models,out

def test_true_context_scores_match_immutable_parent():check_parent('TOP2_CONTEXT')
def test_static_revaluation_matches_immutable_parent():check_parent('TOP2_STATIC')

def test_future_outcome_fields_never_enter_scores():
    g,f,c,models,out=check_parent('TOP2_CONTEXT')
    pert=copy.deepcopy(g)
    for row in pert:
        row['u'][:]=999.;row['target'][:]=1.;row['returns'][:]=-0.99
    changed,_=build_scores(pert,f,c,models)
    for m in out:pd.testing.assert_frame_equal(out[m],changed[m])
