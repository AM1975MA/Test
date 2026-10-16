"""Small isolated configuration of the existing audited NumPy ListNet learner."""
import importlib.util
from pathlib import Path
import numpy as np

path=Path(__file__).resolve().parents[1]/'paper_ltr_v1/learner.py'
spec=importlib.util.spec_from_file_location('_raw_pilot_learner',path)
learner=importlib.util.module_from_spec(spec);spec.loader.exec_module(learner)
learner.RECIPE={**learner.RECIPE,'hidden':[32,8],'max_epochs':20,'patience':10,'weight_decay':.001}

def initialize(n,rng):
    return dict(W1=rng.normal(0,np.sqrt(2/n),(n,32)),b1=np.zeros(32),
                W2=rng.normal(0,np.sqrt(2/32),(32,8)),b2=np.zeros(8),
                W3=rng.normal(0,np.sqrt(1/8),(8,1)),b3=np.zeros(1))

_backward=learner.backward
def backward(params,cache,ds):
    g=_backward(params,cache,ds)
    for name in ('W1','W2','W3'):g[name]+=.001*params[name]
    return g

learner.initialize=initialize
learner.backward=backward
