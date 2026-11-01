import numpy as np
import pandas as pd
import pytest
from objectives import mature_months,top_event,target_grades,query_sizes,probability_metrics
from layer_metrics import ranking_metrics,topk_weights,ndcg,compose
from recovery_core import complete_checkpoint,valid_checkpoint

def panel():
    return pd.DataFrame({'signal_date':pd.to_datetime(['2023-08-31']*2+['2023-09-29']*2+['2023-10-31']*2),'ticker':['A','B']*3,'TARGET':[.1,.9,.2,.8,.3,np.nan],'exit_date_63':pd.to_datetime(['2023-11-30']*2+['2023-12-29','2024-01-02']+['2024-01-31']*2)})

def test_whole_cohort_maturity():
    assert list(mature_months(panel(),pd.Timestamp('2024-01-01')))==[pd.Timestamp('2023-08-31')]

def test_missing_label_excludes_whole_month_only():
    f=panel();f.loc[1,'TARGET']=np.nan
    assert len(mature_months(f,pd.Timestamp('2024-01-01')))==0

def test_future_changes_do_not_affect_available_months():
    f=panel();g=f.copy();g.loc[g.exit_date_63>=pd.Timestamp('2024-01-01'),'TARGET']=.99
    assert list(mature_months(f,pd.Timestamp('2024-01-01')))==list(mature_months(g,pd.Timestamp('2024-01-01')))

def test_duplicate_keys_fail_closed():
    f=panel();f=pd.concat([f,f.iloc[:1]])
    with pytest.raises(ValueError):mature_months(f,pd.Timestamp('2024-01-01'))

def test_top_quintile_ties_and_no_alphabetical_outcome_choice():
    assert top_event(np.arange(10.)).tolist()==[0]*8+[1]*2
    assert top_event(np.ones(10)).sum()==0

def test_grades_explicit_linear_native_target():
    np.testing.assert_array_equal(target_grades([0,.5,1]),[0,8,15])

def test_invalid_labels_fail():
    with pytest.raises(ValueError):target_grades([np.nan,.5])
    with pytest.raises(ValueError):top_event([.5,np.inf])

def test_query_contiguous_groups():
    np.testing.assert_array_equal(query_sizes(['a','a','b','b','b']),[2,3])
    with pytest.raises(ValueError):query_sizes(['a','b','a'])

def test_uniform_scores_have_expected_top_two_quality():
    a=ranking_metrics(np.arange(1.,11),np.ones(10))
    assert abs(a['target_top_quintile_precision']-.2)<1e-12
    assert abs(a['target_bottom_quintile_fraction']-.2)<1e-12
    assert np.isclose(topk_weights(np.ones(10)).sum(),1)

def test_probability_loss_not_target_mse():
    z=probability_metrics(np.array([0,1]),np.array([.2,.8]),.5)
    assert np.isclose(z['brier'],.04) and np.isclose(z['prior_brier'],.25)
    with pytest.raises(ValueError):probability_metrics([0,1],[-.01,.9],.5)

def test_complete_marker_checks_actual_bytes(tmp_path):
    (tmp_path/'a').write_text('x');complete_checkpoint(tmp_path,'k',['a'])
    assert valid_checkpoint(tmp_path,'k')
    (tmp_path/'a').write_text('y');assert not valid_checkpoint(tmp_path,'k')

def test_smoothing_is_causal():
    p=np.arange(30.).reshape(10,3)/30
    a=compose(p,p,p)[2];q=p.copy();q[6:]=.9;b=compose(q,q,q)[2]
    np.testing.assert_array_equal(a[:6],b[:6])


def test_audit_count_is_json_serializable():
    import json
    from audit_target_availability import changed_count
    assert json.dumps({'count':changed_count([{'max_change':np.float64(.2)}])})=='{"count": 1}'
