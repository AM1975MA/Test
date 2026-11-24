"""Autonomous frozen OLC19 transition engine. Prices remain simulated execution proxies."""
import math
POLICIES=('LEGACY', 'PREVIOUS', 'PREVIOUS_UNIFORM', 'PREARM_WEAK', 'PREARM_ALL', 'EOD_LOW', 'EOD_CLOSE', 'NO_STOP', 'EOD_LOW_NET', 'EOD_CLOSE_NET')
def fill(policy: str, opening: float, low: float, close: float, previous_close: float,
         next_open: float, observed: bool=True, low_observed: bool=True,
         next_observed: bool=True, friction: float|None=None, stop_fraction: float=.055) -> tuple[float,float,int]|None:
    """Return raw price, friction-adjusted price and0/1 session execution offset.

    EOD signals use the completed current bar; next_open is execution-only.
    Immediate stop prices are bar proxies, not guaranteed actual market fills.
    """
    if policy not in POLICIES: raise ValueError('Unknown stop policy')
    if friction is not None and not 0<=friction<1: raise ValueError('Invalid stop friction')
    if policy=='NO_STOP' or not observed: return None
    if not all(math.isfinite(v) and v>0 for v in [opening,previous_close]):
        raise ValueError('Invalid price')
    barrier=previous_close*(1-stop_fraction)
    if policy=='EOD_CLOSE': hit=math.isfinite(close) and close>0 and close<=barrier
    else: hit=opening<=barrier or (low_observed and math.isfinite(low) and low>0 and low<=barrier)
    if not hit:return None
    delay=int(policy in ('EOD_LOW','EOD_CLOSE'))
    if delay:
        if not next_observed:raise ValueError('Next Open is not observed; pending execution required')
        if not math.isfinite(next_open) or next_open<=0:raise ValueError('Invalid execution Open')
        raw=next_open
    else:raw=opening if opening<=barrier else barrier
    slip=friction if friction is not None else (0. if opening<=barrier else .001)
    return raw,raw*(1-slip),delay

_fill=fill
"""Ticker-vector primary book; source-compatible risk, with an explicit fee bridge.
No training or optimization. V6 forecast stream is frozen for paired attribution.
"""
import numpy as np
from engine_methods import transition_weights,main_turnover
from broker_cost import solve_budget

LEDGER_COLUMNS=['opening_nav','target_main_gross','target_alt_weight','rebalance','turnover',
 'rebalance_fee','stop_fee','stop_slippage','stop_count','systemic','cooldown','blocked',
 'risky_weight_before_stop','risky_weight_after_stop','main_positions','effective_main_positions',
 'net_pnl','next_nav','free_cash','target_refresh','held_stale_count','primary_traded_notional',
 'main_pnl_no_stop','alt_cash_pnl','stop_effect_before_friction','accounting_residual']

def simulate(q, events, policy='IMMEDIATE', fraction=1., fee=.001, legacy_slots=False,
             top4=None, risk_on=True, lag_systemic=False, exposure_timing="NOW", stop_timing="NOW", stop_policy="LEGACY", stop_friction=None, event_log=None, alarm_log=None, ordinary_alarm=False, fast_stop=False, lock_days=0, order_log=None, broker=None, broker_log=None, selection_hook=None):
    if exposure_timing not in ('NOW','PREVIOUS','OFF') or stop_timing not in ('NOW','PREVIOUS','OFF'):
        raise ValueError('Unknown information timing')
    if lag_systemic:
        if (exposure_timing,stop_timing)!=('NOW','NOW'):
            raise ValueError('Do not combine lag_systemic with explicit modes')
        exposure_timing=stop_timing='PREVIOUS'
    if policy not in ['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE','DELAY','KEEP_WAIT2','CASH_WAIT2','CASH_ZERO_WAIT2']:raise ValueError('Unknown policy')
    if legacy_slots and policy!='IMMEDIATE':raise ValueError('Slot reference is only defined for original pair')
    O,L,PC=[np.asarray(q[k],float) for k in ['O','L','PC']];D,N=O.shape
    e=np.asarray(events,bool)
    if len(e)!=D:raise ValueError('Events must align to daily history')
    tlist=list(q['tickers']);bil=tlist.index('USD_CASH_A') if 'USD_CASH_A' in tlist else (tlist.index('BIL') if 'BIL' in tlist else tlist.index('EUR_CASH_A'))
    shv=tlist.index('USD_CASH_B') if 'USD_CASH_B' in tlist else (tlist.index('SHV') if 'SHV' in tlist else tlist.index('EUR_CASH_B'))
    obs=np.asarray(q.get('observed',np.ones_like(O,bool)),bool)
    lobs=np.asarray(q.get('low_observed',obs),bool)
    gap=q['gap'];ud1=q['ud1'];uneg=q['uneg']
    pgap=np.concatenate([gap[:1]*0,gap[:-1]])
    pud1=np.r_[0.,ud1[:-1]]; puneg=np.r_[0.,uneg[:-1]]
    egap,eud,euneg=(pgap,pud1,puneg) if exposure_timing=='PREVIOUS' else (gap,ud1,uneg)
    sgap,sud,suneg=(pgap,pud1,puneg) if stop_timing=='PREVIOUS' else (gap,ud1,uneg)
    units=np.zeros(N);au=bu=su=free=0.;at=-1;cd=0;force_target=False;lock_until=np.full(N,-1,int);pending_reentry=np.zeros(N,bool);risk_trace=np.zeros((D,8))
    tar=np.zeros(N);executed=np.zeros(N);previous_proposal=None;last_cohort=None
    executed_f=executed_aw=-1.;last_i=last_j=-1;last_sig=None;remaining=0;last_proposal_vector=None;wait_remaining=0
    nav=np.ones(D);ledger=np.zeros((D,len(LEDGER_COLUMNS)));uh=np.zeros((D,N));dh=np.zeros((D,N));fc=np.zeros(D);targets=np.zeros((D,N))
    for k in range(D):
        reentry_count=0;alarm_count=0
        mode=int(q.get("risk_mode",np.zeros(D,int))[k])
        carried_units=units.copy()
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
        if selection_hook is not None:
            p=selection_hook(k,p,units,PC[k],lock_until,cd,force_target)
        sig=(i,j,w);changed=last_sig is None or i!=last_sig[0] or j!=last_sig[1] or abs(w-last_sig[2])>1e-12
        refresh=bool(e[k] or changed)
        economically_changed=last_proposal_vector is None or np.max(abs(p-last_proposal_vector))>1e-12
        last_proposal_vector=p.copy()
        wait_active=False;literal_wait=False
        if policy=='IMMEDIATE':tar=p
        elif policy=='DELAY':
            # Only target scheduling changes; risk and observed-quote rules stay downstream.
            if fraction<1 or int(fraction)!=fraction:raise ValueError('Delay requires a positive integer session count')
            if economically_changed:remaining=int(fraction)
            if p.sum()==0:
                tar=p.copy();remaining=0
            elif np.sum(units*PC[k])<=1e-14:
                tar=p.copy();remaining=0
            elif remaining>1:
                remaining-=1  # Keep previous target, not a daily rebalance to drifted weights.
            else:
                tar=p.copy();remaining=0
        elif policy in ('KEEP_WAIT2','CASH_WAIT2','CASH_ZERO_WAIT2'):
            if fraction<1 or int(fraction)!=fraction:raise ValueError('Whole positive session count required')
            if economically_changed:
                wait_remaining=int(fraction) if np.sum(units*PC[k])>1e-14 else 0
            if p.sum()==0:
                tar=p.copy();wait_remaining=0
            elif wait_remaining>1:
                wait_remaining-=1;wait_active=True
                if policy in ('CASH_WAIT2','CASH_ZERO_WAIT2'):tar=np.zeros(N)
                literal_wait=policy=='CASH_ZERO_WAIT2'
            else:
                tar=p.copy();wait_remaining=0
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
        pg=float(np.dot(tar,egap[k]));sysm=bool(risk_on and active and exposure_timing!='OFF' and ((pg<=-.032 and eud[k]>=.70) or (pg<=-.044 and euneg[k]>=.75)))
        stop_pg=float(np.dot(tar,sgap[k]))
        stop_systemic=bool(risk_on and active and ((stop_pg<=-.032 and sud[k]>=.70) or (stop_pg<=-.044 and suneg[k]>=.75)))
        stop_armed=stop_timing!='OFF' and (stop_systemic or sud[k]>=.55)
        cooldown_rule=int(q.get('cooldown_rule',np.zeros(D,int))[k])
        if cooldown_rule==1 and cd>0 and not sysm and bool(q['recovery'][k]):cd=0
        basef=1. if active else 0.
        if risk_on and active:
            if sysm:basef=.25;cd=3
            elif cd>0:
                basef=(4-cd)*.25 if cooldown_rule==2 else .25
                cd-=1
        g=float(q['g'][k]) if risk_on else 1.;f=min(basef,g)
        unrestricted_f=f
        locked=lock_until>=k
        if mode in (3,4):locked |= pending_reentry & ~q["rebound"][k]
        excluded_weight=float(tar[locked].sum())
        if excluded_weight>0:
            allowed=tar.copy();allowed[locked]=0.;mass=allowed.sum()
            tar=allowed/mass if mass>0 else allowed
            f*=mass
        targets[k]=tar
        nat=int(q['alt'][0,k]) if risk_on else -1
        if wait_active and policy in ('CASH_WAIT2','CASH_ZERO_WAIT2'):nat=-1
        if nat>=0 and locked[nat]:nat=-1
        aw=min(1-f,max(0.,1-g)) if nat>=0 else 0.;cashw=1-f-aw
        reb=bool(np.max(abs(tar-executed))>1e-12 or at!=nat or abs(executed_f-f)>1e-12 or abs(executed_aw-aw)>1e-12 or (free>1e-14 and not literal_wait) or k==0 or force_target)
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
            force_target=False
            cb=bu*O[k,bil]/val;cs=su*O[k,shv]/val;cf=free/val
            ca=au*O[k,at]/val if at>=0 else 0.
            alt_tv=.5*((abs(ca)+aw) if at!=nat else abs(ca-aw))
            if legacy_slots:
                c1=units[last_i]*O[k,last_i]/val if last_i>=0 else 0.
                c2=units[last_j]*O[k,last_j]/val if last_j>=0 and last_j!=last_i else 0.
                rw1=f*w if i>=0 else 0.;rw2=f*(1-w) if j>=0 else 0.
                tv_main=.5*((abs(c1)+rw1) if last_i!=i else abs(c1-rw1))+.5*((abs(c2)+rw2) if last_j!=j else abs(c2-rw2))
            else:tv_main=main_turnover(mainvalue,tar*f,val)
            cash_tv=.5*(abs(cf-cashw)+abs(cb)+abs(cs)) if literal_wait else .5*(abs(cf)+abs(cb-.5*cashw)+abs(cs-.5*cashw))
            tv=tv_main+alt_tv+cash_tv
            ledger[k,4]=tv;ledger[k,5]=val*fee*tv
            newval=val-ledger[k,5]
            if broker is not None:
                old_values=units*O[k]
                if at>=0:old_values[at]+=au*O[k,at]
                desired=tar*f
                if nat>=0:desired=desired.copy();desired[nat]+=aw
                desired=desired.copy()
                for ci, cash_units in ((bil,bu),(shv,su)):
                    if str(tlist[ci]).startswith(('EUR_CASH_','USD_CASH_')):
                        old_values[ci]=0.;desired[ci]=0.
                    else:
                        old_values[ci]+=cash_units*O[k,ci]
                        desired[ci]+=.5*cashw
                newval,broker_fee,n_orders=solve_budget(val,old_values,desired,broker['ticket']/broker['initial'],broker['impact'])
                ledger[k,5]=broker_fee
                if broker_log is not None:
                    diff=newval*desired-old_values
                    for ii in np.flatnonzero(np.abs(diff)>max(1e-12,val*1e-10)):
                        broker_log.append(dict(kind='REBALANCE',index=k,ticker=str(tlist[ii]),notional_eur=float(abs(diff[ii])*broker['initial']),signed_notional_eur=float(diff[ii]*broker['initial']),cost_eur=float(broker['ticket']+broker['impact']*abs(diff[ii])*broker['initial'])))
            if newval<=0:raise ValueError('Nonpositive capital after fees')
            units=tar*f*newval/O[k];au=aw*newval/O[k,nat] if nat>=0 else 0.
            if literal_wait:
                bu=0.;su=0.;free=cashw*newval;at=nat
            else:
                bu=.5*cashw*newval/O[k,bil];su=.5*cashw*newval/O[k,shv];free=0.;at=nat
            executed=tar.copy();executed_f=f;executed_aw=aw;last_i=i;last_j=j
            ledger[k,21]=np.abs(units*O[k]-mainvalue).sum()
        if reb and order_log is not None:
            for name in np.flatnonzero(np.abs(units-carried_units)>1e-14):
                order_log.append(dict(kind='ORDER',index=k,ticker=str(tlist[name]),delta=float(units[name]-carried_units[name]),price=float(O[k,name]),gross=float(f)))
        if reb:
            for name in np.flatnonzero(pending_reentry & (units>carried_units+1e-14) & (units>0)):
                if k<=lock_until[name]:raise AssertionError('Reentry bypassed exclusion')
                reentry_count+=1;pending_reentry[name]=False
                if order_log is not None:
                    order_log.append(dict(kind='REENTRY',index=k,ticker=str(tlist[name]),quantity=float(units[name]),price=float(O[k,name]),lock_until=int(lock_until[name])))
        before=units.copy();defunits=np.zeros(N);defunits[bil]+=bu;defunits[shv]+=su
        if at>=0:defunits[at]+=au
        opening_after=(units*O[k]).sum()+np.dot(defunits,O[k])+free
        ledger[k,12]=((units*O[k]).sum()+(au*O[k,at] if at>=0 else 0.))/opening_after
        ledger[k,20]=int(np.sum((units>0)&~obs[k]))
        for t in np.flatnonzero(before>0):
            weak=bool(q['UH'][k,t] or q['SA'][k,t])
            if ordinary_alarm and risk_on and weak and stop_armed:
                alarm=_fill('EOD_LOW',float(O[k,t]),float(L[k,t]),float(q.get('C',PC)[k,t]),float(PC[k,t]),1.,
                     observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),next_observed=True,friction=0.)
                if alarm is not None:
                    cd=max(cd,3);force_target=True;alarm_count+=1
                    if alarm_log is not None:
                        alarm_log.append(dict(signal_index=k,action_index=k+1,ticker=str(tlist[t]),barrier=float(PC[k,t]*.945),
                             opening=float(O[k,t]),low=float(L[k,t]),close=float(q.get('C',PC)[k,t]),weak=weak,
                             market_permission=bool(stop_armed),intended_gross=.25))
            if not(fast_stop and risk_on) or mode==5:continue
            threshold=float(q["stop_threshold"][k,t]) if mode in (2,4) else .055
            order=_fill('PREARM_ALL',float(O[k,t]),float(L[k,t]),float(q.get('C',PC)[k,t]),float(PC[k,t]),1.,
                observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),friction=stop_friction,stop_fraction=threshold)
            if order is None:continue
            rawfill,fill,_=order;qty=float(units[t])
            ledger[k,24]+=qty*(rawfill-O[k+1,t])
            stop_cost=qty*fill*fee if broker is None else broker['ticket']/broker['initial']+qty*fill*broker['impact']
            ledger[k,6]+=stop_cost;ledger[k,7]+=qty*(rawfill-fill);ledger[k,8]+=1
            free+=qty*fill-stop_cost;units[t]=0.
            if mode==0:cd=max(cd,3)
            if broker is not None and broker_log is not None:
                broker_log.append(dict(kind='STOP',index=k,ticker=str(tlist[t]),notional_eur=float(qty*fill*broker['initial']),signed_notional_eur=float(-qty*fill*broker['initial']),cost_eur=float(stop_cost*broker['initial'])))
            lock_until[t]=max(lock_until[t],k+(1 if mode in (3,4) else lock_days));pending_reentry[t]=True
            if event_log is not None:
                event_log.append(dict(signal_index=k,ticker=str(tlist[t]),raw_price=rawfill,fill_price=fill,barrier=float(PC[k,t]*(1-threshold)),
                    threshold=threshold,quantity=qty,carried_quantity=float(carried_units[t]),newly_bought_quantity=max(0.,qty-float(carried_units[t])),
                    opening_breach=bool(O[k,t]<=PC[k,t]*.945),fee=stop_cost,slippage=qty*(rawfill-fill),
                    lock_until=int(lock_until[t]),earliest_reentry=int(lock_until[t]+1)))
        state_code=2 if excluded_weight>0 or ledger[k,8]>0 else (3 if reentry_count>0 else (1 if unrestricted_f<1 or alarm_count>0 else 0))
        risk_trace[k]=[state_code,locked.sum(),excluded_weight,unrestricted_f,f,reentry_count,ledger[k,8],alarm_count]
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
    return {'risk_trace':risk_trace,'nav':nav,'ledger':ledger,'primary_units':uh,'defensive_units':dh,'free_cash':fc,'targets':targets}
