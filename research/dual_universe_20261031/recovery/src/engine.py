"""Self-financing monthly research engine with executable-open and gap-stop rules.
Ledger: turnover/equity, fees, stops, post-open risky exposure, deferred rebalance,
rebalances, missing held marks, cash at close, closing NAV, gap stops, slippage.
"""
import numpy as np
from numba import njit

@njit(cache=True)
def capped_inverse(vol,cap=.6):
    n=len(vol);a=np.zeros(n);w=np.zeros(n);active=np.ones(n,np.bool_);remaining=1.
    for i in range(n):
        if np.isfinite(vol[i]) and vol[i]>0:a[i]=1./vol[i]
    if a.sum()==0:a[:]=1.
    for _ in range(n+1):
        total=0.
        for i in range(n):
            if active[i]:total+=a[i]
        if total<=0:
            count=active.sum()
            if count:
                for i in range(n):
                    if active[i]:w[i]=remaining/count
            break
        over=False
        for i in range(n):
            if active[i] and remaining*a[i]/total>cap+1e-14:over=True
        if not over:
            for i in range(n):
                if active[i]:w[i]=remaining*a[i]/total
            break
        old=remaining
        for i in range(n):
            if active[i] and old*a[i]/total>cap+1e-14:
                w[i]=cap;remaining-=cap;active[i]=False
    return w

@njit(cache=True)
def run_portfolio(O,L,C,event_day,scores,vols,regime,k=2,weight_mode=0,buffer=False,half=False,stops=False,fee=.001,slip=.001):
    days,n=O.shape;q=np.zeros(n);anchor=np.zeros(n);mark=np.zeros(n);cash=1.
    nav=np.ones(days);ledger=np.zeros((days,11));target=np.zeros(n)
    for d in range(days):
        opening=np.zeros(n);banned=np.zeros(n,np.bool_)
        V=cash
        for j in range(n):
            opening[j]=O[d,j] if np.isfinite(O[d,j]) and O[d,j]>0 else mark[j]
            V+=q[j]*opening[j]
        if V<=0:raise ValueError('Nonpositive opening wealth')
        # Standing stops already established before this opening.
        if stops:
            for j in range(n):
                if q[j]>1e-15 and anchor[j]>0 and np.isfinite(O[d,j]) and O[d,j]>0 and O[d,j]<=anchor[j]*.945:
                    fill=O[d,j]*(1.-slip);notional=q[j]*fill
                    cash+=notional*(1.-fee);ledger[d,0]+=notional/V;ledger[d,1]+=notional*fee
                    ledger[d,2]+=1;ledger[d,9]+=1;ledger[d,10]+=q[j]*(O[d,j]-fill)
                    q[j]=0.;anchor[j]=0.;banned[j]=True
        e=event_day[d]
        if e>=0:
            can_rebalance=True
            for j in range(n):
                if q[j]>1e-15 and not(np.isfinite(O[d,j]) and O[d,j]>0):can_rebalance=False
            if not can_rebalance:ledger[d,4]=1.
            else:
                order=np.argsort(-scores[e],kind='mergesort');chosen=np.full(k,-1,np.int64);count=0
                if buffer:
                    for ri in range(min(2*k,n)):
                        j=order[ri]
                        if count<k and q[j]>1e-15 and not banned[j] and np.isfinite(scores[e,j]):chosen[count]=j;count+=1
                for ri in range(n):
                    j=order[ri]
                    if count>=k:break
                    already=False
                    for ii in range(count):
                        if chosen[ii]==j:already=True
                    if not already and not banned[j] and np.isfinite(scores[e,j]):chosen[count]=j;count+=1
                weights=np.zeros(k)
                if count==k:
                    weights[:]=1./k
                    if weight_mode==1:
                        vv=np.array([vols[e,j] for j in chosen]);weights=capped_inverse(vv,.6)
                    elif weight_mode==2:
                        weights[0]=.6+.4*min(max((scores[e,chosen[0]]-scores[e,chosen[1]])/.12,0.),1.);weights[1]=1.-weights[0]
                target[:]=0.
                exposure=.5 if half and not regime[e] else 1.
                for ii in range(k):
                    j=chosen[ii]
                    if j>=0 and np.isfinite(O[d,j]) and O[d,j]>0:target[j]=weights[ii]*exposure
                now=cash
                old_values=np.zeros(n)
                for j in range(n):old_values[j]=q[j]*opening[j];now+=old_values[j]
                # Solve fee against actual traded notional at the post-fee capital.
                lo=0.;hi=2.*fee*now
                for _ in range(50):
                    f=(lo+hi)*.5;cost=0.
                    for j in range(n):cost+=fee*abs(target[j]*(now-f)-old_values[j])
                    if cost>f:lo=f
                    else:hi=f
                f=(lo+hi)*.5;net=now-f;traded=0.
                for j in range(n):
                    value=target[j]*net;delta=value-old_values[j];traded+=abs(delta)
                    new_q=value/O[d,j] if value>0 else 0.
                    if new_q>q[j]+1e-15:anchor[j]=(q[j]*anchor[j]+(new_q-q[j])*O[d,j])/new_q
                    if new_q<=1e-15:anchor[j]=0.;new_q=0.
                    q[j]=new_q
                cash=net*(1.-target.sum());ledger[d,0]+=traded/V;ledger[d,1]+=f
                if traded>1e-12:ledger[d,5]=1.
        risky=0.
        for j in range(n):risky+=q[j]*opening[j]
        ledger[d,3]=risky/(cash+risky) if cash+risky>0 else 0.
        # Intraday stop execution follows opening transactions; never same-day reentry.
        if stops:
            for j in range(n):
                if q[j]>1e-15 and anchor[j]>0 and np.isfinite(O[d,j]) and O[d,j]>0 and np.isfinite(L[d,j]) and L[d,j]>0:
                    level=anchor[j]*.945
                    if L[d,j]<=level:
                        fill=min(O[d,j],level)*(1.-slip);notional=q[j]*fill
                        cash+=notional*(1.-fee);ledger[d,0]+=notional/V;ledger[d,1]+=notional*fee
                        ledger[d,2]+=1;ledger[d,10]+=q[j]*min(O[d,j],level)*slip
                        q[j]=0.;anchor[j]=0.
        close_nav=cash
        for j in range(n):
            if np.isfinite(C[d,j]) and C[d,j]>0:mark[j]=C[d,j]
            elif q[j]>1e-15:ledger[d,6]+=1
            close_nav+=q[j]*mark[j]
        if not np.isfinite(close_nav) or close_nav<=0 or cash< -1e-10:raise ValueError('Invalid self-financing state')
        nav[d]=close_nav;ledger[d,7]=cash;ledger[d,8]=close_nav
    return nav,ledger
