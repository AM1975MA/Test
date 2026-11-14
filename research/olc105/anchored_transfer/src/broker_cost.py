"""Per-instrument ticket + per-side shortfall. Adjusted economic units, NOT whole shares."""
import numpy as np

def solve_budget(value,old_values,target_weights,ticket,impact):
    old=np.asarray(old_values,float);w=np.asarray(target_weights,float)
    if value<=0 or ticket<0 or not 0<=impact<1 or old.shape!=w.shape or (w<0).any() or w.sum()>1+1e-10:raise ValueError('Invalid account/cost')
    eps=max(1e-12,value*1e-10)
    def charge(eq):
        diff=eq*w-old;mask=np.abs(diff)>eps;n=int(mask.sum())
        return float(n*ticket+impact*np.abs(diff[mask]).sum()),n
    if charge(value)[0]==0:return float(value),0.,0
    if ticket*int(((old>0)|(w>0)).sum())>=value:raise ValueError('Ticket fees exhaust capital')
    lo=0.;hi=float(value)
    for _ in range(65):
        mid=(lo+hi)/2
        if mid+charge(mid)[0]>value:hi=mid
        else:lo=mid
    cost,n=charge(lo)
    if abs(value-lo-cost)>max(1e-8,value*1e-10):raise ValueError('Discontinuous order budget not reconciled')
    return float(value-cost),float(cost),n
