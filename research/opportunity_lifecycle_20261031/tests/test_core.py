import numpy as np
import pytest
from opportunity_core import topk,shortlist,horizon_returns,switch_gain,actual_incumbents

def test_missing_scores_never_become_candidates():
    assert topk(np.array([.5,np.nan,np.inf,.9,-np.inf]),2)==[3,0]

def test_shortlist_only_uses_present_inputs_and_common_support():
    r=np.array([.9,.8,.1,.2]);h=np.array([.2,.1,.8,.9]);mom=np.array([.7,.6,.5,.4]);ok=np.array([True,True,True,False])
    assert shortlist([r,h,mom],ok,1)==[0,2]

def test_no_synthetic_entry_quote():
    o=np.array([[100.,np.nan],[110.,99.],[120.,101.]])
    x=horizon_returns(o,0,2)
    assert x[0]==pytest.approx(.2) and np.isnan(x[1])

def test_terminal_incomplete_label_remains_missing():
    o=np.array([[100.,101.],[110.,105.]])
    assert np.isnan(horizon_returns(o,0,2)).all()

def test_no_synthetic_exit_quote():
    o=np.array([[100.,100.],[110.,np.nan]])
    x=horizon_returns(o,0,1)
    assert x[0]==pytest.approx(.1) and np.isnan(x[1])

def test_switch_friction_solves_actual_cash_budget():
    # Sell one unit of value at cost c, then buy at one plus c times value.
    c=.001
    delta=switch_gain(.12,.10,c)
    assert delta==pytest.approx((1-c)/(1+c)*1.12-1.10)
    assert switch_gain(.10,.10,c)<0

def test_stopped_position_not_an_incumbent():
    row=np.zeros(48);row[25:28]=[2,4,7];row[11:14]=[0,.7,.2]
    assert actual_incumbents(row)==[4]

def test_order_stable_on_ties():
    assert topk(np.array([1.,1.,.5]),2)==[0,1]
