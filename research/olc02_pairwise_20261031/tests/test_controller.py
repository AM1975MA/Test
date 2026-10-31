import numpy as np,pandas as pd
from types import SimpleNamespace
from pair_controller import PairController
from assets import FEATURES

class KnownLinearBank:
    """Deterministic dependency; assertions target controller behavior, not bank calls."""
    def __init__(self,value):
        self.value=value
        self.audit=pd.DataFrame([{'model':'RIDGE','year':2021,'age_feature_max':20.}])
    def values(self,family,s,actions,profile):
        return np.full(len(actions),self.value),np.full((len(actions),1),self.value)

def inputs():
    ds=pd.bdate_range('2021-01-28',periods=4)
    score=pd.DataFrame([[.2,.1,.9,.8]])
    a=SimpleNamespace(N=4,names=['A','B','C','D'],event={2:0},cal=pd.DataFrame({'signal_date':[ds[1]],'entry_date':[ds[2]]}),ds=ds,X=np.ones((1,4,len(FEATURES))),covs=np.array([np.eye(4)*.001]),score=score)
    a.q={'C':np.full((4,4),100.),'d1':np.full((1,4),2),'d2':np.full((1,4),3),'weights':np.full((1,4),.5)}
    a.cl01=lambda k:(2,3);a.ranked=lambda i:[2,3,0,1]
    return a

def test_negative_forecast_retains_actual_pair_not_cash():
    a=inputs();c=PairController(a,KnownLinearBank(-.1),'RIDGE_21_FULL',.001);c.want=(0,1,.5,1.)
    ans=c.step(2,0,1,-1,1.,1.,0,0,0,0,.5,1)
    assert ans==(0,1,.5,1.) and not c.force_rebalance
    assert c.records[-1]['action']=='HOLD'

def test_positive_forecast_buys_only_the_cl01_pair():
    a=inputs();c=PairController(a,KnownLinearBank(.1),'RIDGE_21_FULL',.001);c.want=(0,1,.5,1.)
    ans=c.step(2,0,1,-1,1.,1.,0,0,0,0,.5,1)
    assert ans==(2,3,.5,1.) and c.force_rebalance

def test_missing_position_is_explicit_baseline_reentry_not_trained_hold():
    a=inputs();c=PairController(a,KnownLinearBank(-.1),'RIDGE_21_FULL',.001);c.want=(0,1,.5,1.)
    ans=c.step(2,0,1,-1,0.,1.,0,0,0,100,.5,1)
    assert ans==(2,3,.5,1.) and c.records[-1]['action']=='BASE_REENTRY'

def test_current_day_prices_cannot_change_discretionary_decision():
    a=inputs();b=inputs();b.q['C'][2:]=1e8
    answers=[]
    for asset in [a,b]:
        c=PairController(asset,KnownLinearBank(.1),'RIDGE_21_FULL',.001);c.want=(0,1,.5,1.)
        answers.append(c.step(2,0,1,-1,1.,1.,0,0,0,0,.5,1))
    assert answers[0]==answers[1]

def test_age_guard_abstains_to_baseline_outside_training_support():
    a=inputs();bank=KnownLinearBank(-.1)
    bank.audit['h']=21;bank.audit['age_feature_max']=0.
    c=PairController(a,bank,'RIDGE_21_FULL_AGE',.001);c.want=(0,1,.5,1.)
    ans=c.step(2,0,1,-1,1.,1.,0,0,0,0,.5,1)
    assert ans==(2,3,.5,1.)
    assert c.records[-1]['action']=='AGE_SUPPORT_BASE'

def test_age_guard_leaves_in_support_negative_decision_unchanged():
    a=inputs();bank=KnownLinearBank(-.1);bank.audit['h']=21
    c=PairController(a,bank,'RIDGE_21_FULL_AGE',.001);c.want=(0,1,.5,1.)
    assert c.step(2,0,1,-1,1.,1.,0,0,0,0,.5,1)==(0,1,.5,1.)

def test_unconditional_proposal_control_is_not_a_forecast_gate():
    a=inputs();c=PairController(a,KnownLinearBank(-.1),'FOLLOW_CL01',.001);c.want=(0,1,.5,1.)
    assert c.step(2,0,1,-1,1.,1.,0,0,0,0,.5,1)==(2,3,.5,1.)
