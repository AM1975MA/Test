import numpy as np
import pytest
from methods import collapse_columns,blend_forecasts,transition_weights,main_turnover

def test_collapse_identical_aliases_preserves_nan_and_values():
 x=np.array([[.3,.8,.3],[np.nan,.2,np.nan]])
 out,ids=collapse_columns(x,['A','B','A'])
 assert ids==['A','B'];np.testing.assert_array_equal(out,x[:,:2])

def test_false_equivalence_is_not_silently_accepted():
 with pytest.raises(ValueError):collapse_columns(np.array([[.1,.4]]),['A','A'])

def test_blend_prefix_has_no_future_dependence():
 r=np.arange(12).reshape(4,3)/12;e=r.copy();x=r.copy()
 full=blend_forecasts(r,e,x)
 np.testing.assert_array_equal(full[:3],blend_forecasts(r[:3],e[:3],x[:3]))

def test_current_missing_forecast_not_backfilled():
 r=np.ones((3,2))*.5;e=r.copy();e[2,1]=np.nan
 assert np.isnan(blend_forecasts(r,e,r)[2,1])

def test_transition_holds_four_actual_tickers():
 w=transition_weights(np.array([1.,1.,0.,0.]),np.ones(4),np.array([0.,0.,.5,.5]),.5)
 np.testing.assert_array_equal(w,np.full(4,.25))

def test_transition_uses_actual_drift_not_previous_nominal_weights():
 w=transition_weights(np.array([1.,1.,0.,0.]),np.array([3.,1.,100.,100.]),np.array([0.,0.,.5,.5]),.5)
 np.testing.assert_array_equal(w,[.375,.125,.25,.25])

def test_initial_entry_has_no_unintentional_cash_ramp():
 p=np.array([.6,.4,0.]);np.testing.assert_array_equal(transition_weights(np.zeros(3),np.ones(3),p,.25),p)

def test_transition_full_is_proposal_and_zero_is_drift():
 p=np.array([0.,0.,1.]);u=np.array([1.,3.,0.]);c=np.ones(3)
 np.testing.assert_array_equal(transition_weights(u,c,p,1),p)
 np.testing.assert_array_equal(transition_weights(u,c,p,0),[.25,.75,0])

def test_invalid_fraction_raises():
 with pytest.raises(ValueError):transition_weights(np.ones(2),np.ones(2),np.array([.5,.5]),1.1)

def test_ticker_net_turnover_ignores_slot_permutation():
 assert main_turnover(np.array([.5,.5]),np.array([.5,.5]),1.)==0.
 assert main_turnover(np.array([.5,.5,0.]),np.array([.5,0.,.5]),1.)==.5
