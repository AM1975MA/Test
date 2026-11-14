from settings import *
import hashlib,json
src=BASE/'src/frozen_state_engine.py';s=src.read_text();original=s
s=s.replace('from methods import transition_weights,main_turnover','from engine_methods import transition_weights,main_turnover\nfrom broker_cost import solve_budget')
(ROOT/'src/engine_methods.py').write_text((BASE/'src/methods.py').read_text())
assert s.count('lock_days=0, order_log=None):')==1
s=s.replace('lock_days=0, order_log=None):','lock_days=0, order_log=None, broker=None, broker_log=None):')
old='''            newval=val-ledger[k,5]
            if newval<=0:raise ValueError('Nonpositive capital after fees')'''
new='''            newval=val-ledger[k,5]
            if broker is not None:
                old_values=units*O[k]
                if at>=0:old_values[at]+=au*O[k,at]
                desired=tar*f
                if nat>=0:desired=desired.copy();desired[nat]+=aw
                old_values[bil]=old_values[shv]=0.;desired[bil]=desired[shv]=0.
                newval,broker_fee,n_orders=solve_budget(val,old_values,desired,broker['ticket']/broker['initial'],broker['impact'])
                ledger[k,5]=broker_fee
                if broker_log is not None:
                    diff=newval*desired-old_values
                    for ii in np.flatnonzero(np.abs(diff)>max(1e-12,val*1e-10)):
                        broker_log.append(dict(kind='REBALANCE',index=k,ticker=str(tlist[ii]),notional_eur=float(abs(diff[ii])*broker['initial']),signed_notional_eur=float(diff[ii]*broker['initial']),cost_eur=float(broker['ticket']+broker['impact']*abs(diff[ii])*broker['initial'])))
            if newval<=0:raise ValueError('Nonpositive capital after fees')'''
assert s.count(old)==1;s=s.replace(old,new)
old='''            ledger[k,6]+=qty*fill*fee;ledger[k,7]+=qty*(rawfill-fill);ledger[k,8]+=1
            free+=qty*fill*(1-fee);units[t]=0.;cd=max(cd,3)'''
new='''            stop_cost=qty*fill*fee if broker is None else broker['ticket']/broker['initial']+qty*fill*broker['impact']
            ledger[k,6]+=stop_cost;ledger[k,7]+=qty*(rawfill-fill);ledger[k,8]+=1
            free+=qty*fill-stop_cost;units[t]=0.;cd=max(cd,3)
            if broker is not None and broker_log is not None:
                broker_log.append(dict(kind='STOP',index=k,ticker=str(tlist[t]),notional_eur=float(qty*fill*broker['initial']),signed_notional_eur=float(-qty*fill*broker['initial']),cost_eur=float(stop_cost*broker['initial'])))'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('fee=qty*fill*fee,slippage=qty*(rawfill-fill),','fee=stop_cost,slippage=qty*(rawfill-fill),')
(ROOT/'src/native_broker_engine.py').write_text(s)
(ROOT/'results/ENGINE_ADAPTER_HASH.json').write_text(json.dumps({'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'adapter_sha256':hashlib.sha256(s.encode()).hexdigest(),'edits':['optional absolute per-instrument ticket and side shortfall budget','broker order audit logging','stops charged per order'],'unchanged':['selection','native DELAY scheduler','V6 inputs','stop barrier','LOCK3','reentry'],'fractional_adjusted_units':True,'whole_share_execution':False},indent=2))
