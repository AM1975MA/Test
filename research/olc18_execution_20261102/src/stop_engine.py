"""OLC18: isolated stop block over authenticated OLC17 accounting.

EOD exit is valued at the next Open; output units/free cash for that interval
are AFTER that boundary sale, before the next ordinary rebalance. Its decision
uses no next-opening price. This is not a claim of intraday fill certification.
"""
from pathlib import Path
import sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'parent_archive'
sys.path.append(str(P/'src'))
sys.path.append(str(P/'parent/olc16_contextual_rank_20261102/src'))
import validated_engine as _parent
from stop_contract import POLICIES,eligible as _eligible,fill as _fill
_s=_parent._s

def _replace(old,new):
 global _s
 if _s.count(old)!=1:raise RuntimeError('Parent source mismatch: '+old[:80])
 _s=_s.replace(old,new)

_replace('exposure_timing="NOW", stop_timing="NOW"):',
 'exposure_timing="NOW", stop_timing="NOW", stop_policy="LEGACY", stop_friction=None, event_log=None, alarm_log=None):')
_replace('    units=np.zeros(N);au=bu=su=free=0.;at=-1;cd=0','    units=np.zeros(N);au=bu=su=free=0.;at=-1;cd=0;force_target=False')
_replace('or free>1e-14 or k==0)', 'or free>1e-14 or k==0 or force_target)')
_replace('        if reb:\n            cb=', '        if reb:\n            force_target=False\n            cb=')
_replace('        mainvalue=units*O[k];', '        carried_units=units.copy()\n        mainvalue=units*O[k];')
start=_s.index('        for t in np.flatnonzero(units>0):')
end=_s.index('        ledger[k,10]=cd',start)
_s=_s[:start]+'''        for t in np.flatnonzero(units>0):
            weak=bool(q['UH'][k,t] or q['SA'][k,t])
            if not(risk_on and _eligible(stop_policy,weak,stop_armed)):continue
            close=float(q.get('C',PC)[k,t])
            if stop_policy.endswith('_NET'):
                alarm=_fill(stop_policy.removesuffix('_NET'),float(O[k,t]),float(L[k,t]),close,float(PC[k,t]),1.,
                    observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),next_observed=True,friction=0.)
                if alarm is not None:
                    cd=max(cd,3);force_target=True
                    if alarm_log is not None:
                        alarm_log.append(dict(signal_index=k,action_index=k+1,ticker=str(tlist[t]),
                            barrier=float(PC[k,t]*(1-.055)),opening=float(O[k,t]),low=float(L[k,t]),close=close,
                            weak=weak,market_permission=bool(stop_armed),intended_gross=.25))
                continue
            order=_fill(stop_policy,float(O[k,t]),float(L[k,t]),close,float(PC[k,t]),float(O[k+1,t]),
                observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),next_observed=bool(obs[k+1,t]),friction=stop_friction)
            if order is None:continue
            rawfill,fill,offset=order
            qty=float(units[t]);barrier=float(PC[k,t]*(1-.055))
            if event_log is not None:
                event_log.append(dict(signal_index=k,execution_index=k+offset,ticker=str(tlist[t]),
                    raw_price=rawfill,fill_price=fill,barrier=barrier,opening=float(O[k,t]),low=float(L[k,t]),close=close,
                    next_open=float(O[k+1,t]),weak=weak,market_permission=bool(stop_armed),
                    quantity=qty,carried_quantity=float(carried_units[t]),
                    newly_bought_quantity=max(0.,qty-float(carried_units[t])),opening_breach=bool(O[k,t]<=barrier),
                    fee=qty*fill*fee,slippage=qty*(rawfill-fill),raw_proceeds=qty*rawfill,
                    counterfactual_next_open_proceeds=qty*O[k+1,t]))
            ledger[k,24]+=qty*(rawfill-O[k+1,t])
            ledger[k,6]+=qty*fill*fee;ledger[k,7]+=qty*(rawfill-fill);ledger[k,8]+=1
            free+=qty*fill*(1-fee);units[t]=0.;cd=max(cd,3)
''' +_s[end:]
# Compile against original numerical operations; only the stop block differs.
_ns=dict(_eligible=_eligible,_fill=_fill)
exec(compile(_s,'<OLC18_instrumented_stop_engine>','exec'),_ns)
_impl=_ns['simulate']
LEDGER_COLUMNS=_ns['LEDGER_COLUMNS']

def simulate(q,events,*,contract='LEGACY',friction=None,fee=.001,event_log=None,alarm_log=None):
 if contract not in POLICIES:raise ValueError('Unknown stop contract')
 if contract not in ('LEGACY','PREVIOUS','NO_STOP') and friction is None:friction=.001
 exposure='NOW' if contract=='LEGACY' else 'PREVIOUS'
 stop='PREVIOUS' if contract in ('PREVIOUS','PREVIOUS_UNIFORM') else 'NOW'
 if contract=='NO_STOP':stop='OFF'
 return _impl(q,events,fee=fee,exposure_timing=exposure,stop_timing=stop,
              stop_policy=contract,stop_friction=friction,event_log=event_log,alarm_log=alarm_log)
