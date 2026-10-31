"""Ticker-vector primary book; source-compatible risk, with an explicit fee bridge.
No training or optimization. V6 forecast stream is frozen for paired attribution.
"""
import numpy as np
from methods import transition_weights,main_turnover

LEDGER_COLUMNS=['opening_nav','target_main_gross','target_alt_weight','rebalance','turnover',
 'rebalance_fee','stop_fee','stop_slippage','stop_count','systemic','cooldown','blocked',
 'risky_weight_before_stop','risky_weight_after_stop','main_positions','effective_main_positions',
 'net_pnl','next_nav','free_cash','target_refresh','held_stale_count','primary_traded_notional',
 'main_pnl_no_stop','alt_cash_pnl','stop_effect_before_friction','accounting_residual']

def simulate(q, events, policy='IMMEDIATE', fraction=1., fee=.001, legacy_slots=False,
             top4=None, risk_on=True, lag_systemic=False):
    if policy not in ['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE']:raise ValueError('Unknown policy')
    if legacy_slots and policy!='IMMEDIATE':raise ValueError('Slot reference is only defined for original pair')
    O,L,PC=[np.asarray(q[k],float) for k in ['O','L','PC']];D,N=O.shape
    e=np.asarray(events,bool)
    if len(e)!=D:raise ValueError('Events must align to daily history')
    tlist=list(q['tickers']);bil=tlist.index('BIL') if 'BIL' in tlist else tlist.index('EUR_CASH_A')
    shv=tlist.index('SHV') if 'SHV' in tlist else tlist.index('EUR_CASH_B')
    obs=np.asarray(q.get('observed',np.ones_like(O,bool)),bool)
    lobs=np.asarray(q.get('low_observed',obs),bool)
    gap=q['gap'];ud1=q['ud1'];uneg=q['uneg']
    if lag_systemic:
        gap=np.concatenate([gap[:1]*0,gap[:-1]]);ud1=np.r_[0.,ud1[:-1]];uneg=np.r_[0.,uneg[:-1]]
    units=np.zeros(N);au=bu=su=free=0.;at=-1;cd=0
    tar=np.zeros(N);executed=np.zeros(N);previous_proposal=None;last_cohort=None
    executed_f=executed_aw=-1.;last_i=last_j=-1;last_sig=None;remaining=0;last_proposal_vector=None
    nav=np.ones(D);ledger=np.zeros((D,len(LEDGER_COLUMNS)));uh=np.zeros((D,N));dh=np.zeros((D,N));fc=np.zeros(D);targets=np.zeros((D,N))
    for k in range(D):
        mainvalue=units*O[k];val=mainvalue.sum()+free+bu*O[k,bil]+su*O[k,shv]
        if at>=0:val+=au*O[k,at]
        if k==0 and val==0:val=1.
        ledger[k,0]=val
        if k==D-1:
            nav[k]=val;uh[k]=units;dh[k,bil]+=bu;dh[k,shv]+=su
            if at>=0:dh[k,at]+=au
            fc[k]=free;targets[k]=tar;ledger[k,17]=val;break
        i=int(q['d1'][0,k]);j=int(q['d2'][0,k]);w=float(q['weights'][0,k]);w=1. if i==j else w
        p=np.zeros(N)
        if i>=0:p[i]+=w
        if j>=0:p[j]+=1-w
        sig=(i,j,w);changed=last_sig is None or i!=last_sig[0] or j!=last_sig[1] or abs(w-last_sig[2])>1e-12
        refresh=bool(e[k] or changed)
        economically_changed=last_proposal_vector is None or np.max(abs(p-last_proposal_vector))>1e-12
        last_proposal_vector=p.copy()
        if policy=='IMMEDIATE':tar=p
        elif policy=='PHASE':
            if fraction<1 or int(fraction)!=fraction:raise ValueError('Phase requires a positive integer session count')
            if economically_changed:remaining=int(fraction)
            if p.sum()==0:tar=p;remaining=0
            elif np.sum(units*PC[k])<=1e-14:
                tar=p.copy();remaining=0
            elif remaining>0:
                tar=transition_weights(units,PC[k],p,1./remaining)
                remaining-=1
            else:tar=p.copy()
        elif refresh:
            if p.sum()==0:tar=p
            elif policy=='PARTIAL':tar=transition_weights(units,PC[k],p,fraction)
            elif policy=='TOP4':
                if top4 is None:raise ValueError('Top4 targets required')
                tar=np.asarray(top4[k],float).copy()
            elif policy=='COHORT2':
                if e[k]:
                    last_cohort=None if previous_proposal is None else previous_proposal.copy()
                    previous_proposal=p.copy()
                tar=p.copy() if last_cohort is None else .5*p+.5*last_cohort
        last_sig=sig;targets[k]=tar
        active=tar.sum()>1e-12
        pg=float(np.dot(tar,gap[k]));sysm=bool(risk_on and active and ((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75)))
        basef=1. if active else 0.
        if risk_on and active:
            if sysm:basef=.25;cd=3
            elif cd>0:basef=.25;cd-=1
        g=float(q['g'][k]) if risk_on else 1.;f=min(basef,g)
        nat=int(q['alt'][0,k]) if risk_on else -1
        aw=min(1-f,max(0.,1-g)) if nat>=0 else 0.;cashw=1-f-aw
        reb=bool(np.max(abs(tar-executed))>1e-12 or at!=nat or abs(executed_f-f)>1e-12 or abs(executed_aw-aw)>1e-12 or free>1e-14 or k==0)
        if legacy_slots and (i!=last_i or j!=last_j):reb=True
        if reb:
            needed=(units>0)|(tar*f>0)
            if at>=0 and au>0:needed[at]=True
            if nat>=0 and aw>0:needed[nat]=True
            if np.any(needed&~obs[k]):
                reb=False;ledger[k,11]=1
                if k==0:free=val
        ledger[k,1:4]=[f,aw,reb];ledger[k,9:11]=[sysm,cd];ledger[k,19]=refresh
        if reb:
            cb=bu*O[k,bil]/val;cs=su*O[k,shv]/val;cf=free/val
            ca=au*O[k,at]/val if at>=0 else 0.
            alt_tv=.5*((abs(ca)+aw) if at!=nat else abs(ca-aw))
            if legacy_slots:
                c1=units[last_i]*O[k,last_i]/val if last_i>=0 else 0.
                c2=units[last_j]*O[k,last_j]/val if last_j>=0 and last_j!=last_i else 0.
                rw1=f*w if i>=0 else 0.;rw2=f*(1-w) if j>=0 else 0.
                tv_main=.5*((abs(c1)+rw1) if last_i!=i else abs(c1-rw1))+.5*((abs(c2)+rw2) if last_j!=j else abs(c2-rw2))
            else:tv_main=main_turnover(mainvalue,tar*f,val)
            tv=tv_main+alt_tv+.5*(abs(cf)+abs(cb-.5*cashw)+abs(cs-.5*cashw))
            ledger[k,4]=tv;ledger[k,5]=val*fee*tv
            newval=val-ledger[k,5]
            if newval<=0:raise ValueError('Nonpositive capital after fees')
            units=tar*f*newval/O[k];au=aw*newval/O[k,nat] if nat>=0 else 0.
            bu=.5*cashw*newval/O[k,bil];su=.5*cashw*newval/O[k,shv];free=0.;at=nat
            executed=tar.copy();executed_f=f;executed_aw=aw;last_i=i;last_j=j
            ledger[k,21]=np.abs(units*O[k]-mainvalue).sum()
        before=units.copy();defunits=np.zeros(N);defunits[bil]+=bu;defunits[shv]+=su
        if at>=0:defunits[at]+=au
        opening_after=(units*O[k]).sum()+np.dot(defunits,O[k])+free
        ledger[k,12]=((units*O[k]).sum()+(au*O[k,at] if at>=0 else 0.))/opening_after
        ledger[k,20]=int(np.sum((units>0)&~obs[k]))
        for t in np.flatnonzero(units>0):
            if risk_on and obs[k,t] and (q['UH'][k,t] or q['SA'][k,t]) and (sysm or ud1[k]>=.55):
                sp=PC[k,t]*(1-.055)
                rawfill=O[k,t] if O[k,t]<=sp else (sp if lobs[k,t] and L[k,t]<=sp else 0.)
                if rawfill>0:
                    fill=rawfill if O[k,t]<=sp else rawfill*(1-.001)
                    ledger[k,24]+=units[t]*(rawfill-O[k+1,t])
                    ledger[k,6]+=units[t]*fill*fee;ledger[k,7]+=units[t]*(rawfill-fill);ledger[k,8]+=1
                    free+=units[t]*fill*(1-fee);units[t]=0.;cd=max(cd,3)
        ledger[k,10]=cd
        nextval=float(np.dot(units+defunits,O[k+1])+free)
        if not np.isfinite(nextval) or nextval<=0:raise ValueError('Invalid NAV')
        nav[k]=nextval;uh[k]=units;dh[k]=defunits;fc[k]=free
        ledger[k,13]=((units*O[k]).sum()+(au*O[k,at] if at>=0 else 0.))/opening_after
        ledger[k,14]=int(np.sum(units*O[k]>opening_after*.0001))
        mv=units*O[k];s=mv.sum();ledger[k,15]=s*s/np.sum(mv*mv) if s>0 else 0.
        ledger[k,16:19]=[nextval-val,nextval,free]
        ledger[k,22]=np.dot(before,O[k+1]-O[k]);ledger[k,23]=np.dot(defunits,O[k+1]-O[k])
        ledger[k,25]=nextval-val-(ledger[k,22]+ledger[k,23]+ledger[k,24]-ledger[k,5]-ledger[k,6]-ledger[k,7])
    return {'nav':nav,'ledger':ledger,'primary_units':uh,'defensive_units':dh,'free_cash':fc,'targets':targets}
