import numpy as np
from engine_prepare import stage
from reconcile_math import log_returns,shapley,mobius

def tiny_inputs():
    d1=np.array([[0,0,0,-1]],dtype=np.int16);d2=np.array([[1,1,1,-1]],dtype=np.int16)
    w=np.full((1,4),.6);O=np.array([[100.,100.,100.,100.],[100.,101.,100.,100.],[102.,103.,100.,100.],[104.,105.,100.,100.]])
    L=O*.9;C=O.copy();PC=np.vstack([O[:1],O[:-1]])
    gap=np.full((4,4),-.05);ud=np.full(4,.8);uneg=ud.copy();UH=np.ones((4,4),bool);SA=UH.copy()
    G=np.ones((1,4));alt=np.full((1,4),-1,dtype=np.int16)
    return [d1,d2,w,O,L,C,PC,gap,ud,uneg,UH,SA,2,3,G,G[0],alt,True,.001]

def test_instrumented_all_on_exact():
    from instrumented_engine import simulate_instrumented
    a=tiny_inputs();orig=stage.simulate_arch.py_func(*a);new=simulate_instrumented.py_func(*a)
    for x,y in zip(orig,new[:4]):np.testing.assert_array_equal(x,y)

def test_systemic_switch_keeps_stop_channel():
    from instrumented_engine import simulate_instrumented
    x=simulate_instrumented.py_func(*tiny_inputs(),systemic_enabled=False,stops_enabled=True)
    assert x[4][0,:,17].sum()==0
    assert x[4][0,:,7:9].sum()>0
    y=simulate_instrumented.py_func(*tiny_inputs(),systemic_enabled=True,stops_enabled=False)
    assert y[4][0,:,17].sum()>0
    assert y[4][0,:,7:9].sum()==0

def test_additive_and_interaction_allocation():
    values=np.array([10.,12.,14.,22.])[:,None]
    phi=shapley(values)
    np.testing.assert_allclose(phi[:,0],[5.,7.],rtol=0,atol=1e-12)
    np.testing.assert_allclose(phi.sum(0),values[-1]-values[0],rtol=0,atol=1e-12)

def test_mobius_interaction():
    np.testing.assert_allclose(mobius(np.array([10.,12.,14.,22.])[:,None])[:,0],[10.,2.,4.,6.])

def test_first_day_and_terminal_flat_day_preserved():
    nav=np.array([1.1,1.21,1.21]);lr=log_returns(nav)
    np.testing.assert_allclose(lr,[np.log(1.1),np.log(1.1),0],atol=1e-15)
    assert abs(lr.sum()-np.log(nav[-1]))<1e-15

def test_complete_factorial_required():
    import pytest
    with pytest.raises(ValueError):shapley(np.zeros((7,2)))
