"""Frozen OLC18 bookkeeping, isolated ordinary/emergency/reentry state extension.
No source is overwritten. None of these bar-price contracts certifies live fills.
"""
from pathlib import Path
import hashlib
import sys

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'restore/olc18_execution_20261102'
sys.path.append(str(PARENT/'src'))
import stop_engine as _parent
from stop_contract import fill as _fill

CONTRACTS={
 'BASE':(False,False,0),
 'ALARM':(True,False,0),
 'FAST_NOLOCK':(False,True,0),
 'COMBINED_NOLOCK':(True,True,0),
 'FAST_LOCK3':(False,True,3),
 'COMBINED_LOCK3':(True,True,3),
}
RISK_COLUMNS=('state','locked_names','excluded_weight','unrestricted_gross','effective_gross','reentries','fast_exits','ordinary_alarms')
_s=_parent._s

def _replace(old,new):
 global _s
 if _s.count(old)!=1:raise RuntimeError('Parent source mismatch: '+old[:90])
 _s=_s.replace(old,new)

_replace('event_log=None, alarm_log=None):',
 'event_log=None, alarm_log=None, ordinary_alarm=False, fast_stop=False, lock_days=0, order_log=None):')
_replace('cd=0;force_target=False','cd=0;force_target=False;lock_until=np.full(N,-1,int);pending_reentry=np.zeros(N,bool);risk_trace=np.zeros((D,8))')
_replace('        carried_units=units.copy()', '        reentry_count=0;alarm_count=0\n        carried_units=units.copy()')
_replace('        nat=int(q[\'alt\'][0,k]) if risk_on else -1', '''        unrestricted_f=f
        locked=lock_until>=k
        excluded_weight=float(tar[locked].sum())
        if excluded_weight>0:
            allowed=tar.copy();allowed[locked]=0.;mass=allowed.sum()
            tar=allowed/mass if mass>0 else allowed
            f*=mass
        targets[k]=tar
        nat=int(q['alt'][0,k]) if risk_on else -1
        if nat>=0 and locked[nat]:nat=-1''')
_replace('        before=units.copy();defunits=np.zeros(N);', '''        if reb and order_log is not None:
            for name in np.flatnonzero(np.abs(units-carried_units)>1e-14):
                order_log.append(dict(kind='ORDER',index=k,ticker=str(tlist[name]),delta=float(units[name]-carried_units[name]),price=float(O[k,name]),gross=float(f)))
        if reb:
            for name in np.flatnonzero(pending_reentry & (units>carried_units+1e-14) & (units>0)):
                if k<=lock_until[name]:raise AssertionError('Reentry bypassed exclusion')
                reentry_count+=1;pending_reentry[name]=False
                if order_log is not None:
                    order_log.append(dict(kind='REENTRY',index=k,ticker=str(tlist[name]),quantity=float(units[name]),price=float(O[k,name]),lock_until=int(lock_until[name])))
        before=units.copy();defunits=np.zeros(N);''')
start=_s.index('        for t in np.flatnonzero(units>0):')
end=_s.index('        ledger[k,10]=cd',start)
_s=_s[:start]+'''        for t in np.flatnonzero(before>0):
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
            if not(fast_stop and risk_on):continue
            order=_fill('PREARM_ALL',float(O[k,t]),float(L[k,t]),float(q.get('C',PC)[k,t]),float(PC[k,t]),1.,
                observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),friction=stop_friction)
            if order is None:continue
            rawfill,fill,_=order;qty=float(units[t])
            ledger[k,24]+=qty*(rawfill-O[k+1,t])
            ledger[k,6]+=qty*fill*fee;ledger[k,7]+=qty*(rawfill-fill);ledger[k,8]+=1
            free+=qty*fill*(1-fee);units[t]=0.;cd=max(cd,3)
            lock_until[t]=max(lock_until[t],k+lock_days);pending_reentry[t]=True
            if event_log is not None:
                event_log.append(dict(signal_index=k,ticker=str(tlist[t]),raw_price=rawfill,fill_price=fill,barrier=float(PC[k,t]*.945),
                    quantity=qty,carried_quantity=float(carried_units[t]),newly_bought_quantity=max(0.,qty-float(carried_units[t])),
                    opening_breach=bool(O[k,t]<=PC[k,t]*.945),fee=qty*fill*fee,slippage=qty*(rawfill-fill),
                    lock_until=int(lock_until[t]),earliest_reentry=int(lock_until[t]+1)))
        state_code=2 if excluded_weight>0 or ledger[k,8]>0 else (3 if reentry_count>0 else (1 if unrestricted_f<1 or alarm_count>0 else 0))
        risk_trace[k]=[state_code,locked.sum(),excluded_weight,unrestricted_f,f,reentry_count,ledger[k,8],alarm_count]
''' +_s[end:]
_replace("return {'nav':nav,", "return {'risk_trace':risk_trace,'nav':nav,")
_ns=dict(_fill=_fill)
exec(compile(_s,'<OLC19_isolated_combined_risk>','exec'),_ns)
_impl=_ns['simulate']
LEDGER_COLUMNS=_parent.LEDGER_COLUMNS

def simulate(q,events,*,contract='BASE',fee=.001,friction=.001,event_log=None,alarm_log=None,order_log=None):
    if contract not in CONTRACTS:raise ValueError('Unknown contract')
    if not 0<=fee<1 or not 0<=friction<1:raise ValueError('Invalid friction')
    ordinary,fast,lock=CONTRACTS[contract]
    return _impl(q,events,fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',
       stop_friction=friction,event_log=event_log,alarm_log=alarm_log,ordinary_alarm=ordinary,
       fast_stop=fast,lock_days=lock,order_log=order_log)
