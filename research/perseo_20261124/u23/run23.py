from core23 import *
from engine23 import simulate

def run(m,rule,bps=15,lag=0,q=None,built=None,plan=None,save=True):
    if q is None:q=state(m)
    if built is None:built=signals(q,m)
    targets,recovery,_,_=built;D=len(q['dates']);q=q.copy()
    if plan is None:choices=np.full(D,rule,dtype='U24')
    else:choices=np.array([plan.get(str(pd.Timestamp(d).year),'BASE') for d in q['dates']])
    target=np.empty_like(targets['BASE'])
    for name in np.unique(choices):target[choices==name]=targets[name][choices==name]
    modes=np.array([1 if x in ['RECOVERY','TREND_RECOVERY','LEG_RECOVERY'] else (2 if x=='RAMP' else 0) for x in choices])
    q['recovery']=recovery.copy();q['cooldown_rule']=modes
    if lag:
        target=np.concatenate([target[:1],target[:-1]])
        for key in ['g','recovery','cooldown_rule']:q[key]=np.concatenate([q[key][:1],q[key][:-1]])
        for key in ['d1','d2','alt']:q[key]=np.concatenate([q[key][:,:1],q[key][:,:-1]],axis=1)
        q['events']=np.r_[q['events'][0],q['events'][:-1]]
    orders=[];stops=[]
    hook=None if rule=='BASE' and lag==0 else lambda k,*args:target[k]
    r=simulate(q,q['events'],policy='IMMEDIATE',fraction=1,fee=0,stop_friction=0,exposure_timing='PREVIOUS',stop_timing='NOW',ordinary_alarm=False,fast_stop=True,lock_days=3,risk_on=True,broker={'initial':10000.,'ticket':1.,'impact':bps/10000},broker_log=orders,event_log=stops,selection_hook=hook)
    nav=r['ledger'][:,0];units=r['primary_units']+r['defensive_units'];od=pd.DataFrame(orders)
    err=float(abs((units[:-1]*q['O'][1:]).sum(1)+r['free_cash'][:-1]-nav[1:]).max());res=float(abs(r['ledger'][:-1,-1]).max())
    fees=od.groupby('index').cost_eur.sum().reindex(range(D),fill_value=0).to_numpy()/10000
    fe=float(abs(fees-r['ledger'][:,5]-r['ledger'][:,6]).max());assert max(err,res,fe)<1e-9
    if rule=='BASE' and bps==15 and lag==0:assert np.array_equal(nav,load(INPUT/f'{m}_REFERENCE.npz')['nav'])
    close_nav=(units*q['C']).sum(1)+r['free_cash']
    # Last snapshot is the final opening, not an executed final trading session.
    close_nav[-1]=nav[-1]
    row=dict(market=m,rule=rule,bps=bps,lag=lag,**metrics(q['dates'],nav),orders=len(od),stops=len(stops),cost_currency=float(od.cost_eur.sum()),notional_currency=float(od.notional_eur.sum()),wealth_error=err,accounting_error=res,fee_error=fe)
    if save:
        name=tag(m,rule,bps,lag)
        np.savez_compressed(OUT/f'{name}.npz',dates=q['dates'],nav=nav,close_nav=close_nav,choice=choices,**{key:r[key] for key in ['primary_units','defensive_units','free_cash','ledger','targets']})
        od.to_csv(OUT/f'{name}_ORDERS.csv',index=False);pd.DataFrame(stops).to_csv(OUT/f'{name}_STOPS.csv',index=False)
        print(name,round(row['cagr']*100,3),round(row['maxdd']*100,3),len(od),flush=True)
    return row,r,close_nav

def main():
    rows=[]
    for m in MARKETS:
        q=state(m);built=signals(q,m);built[3].to_csv(OUT/f'{m}_SIGNAL_AUDIT.csv',index=False)
        np.savez_compressed(OUT/f'{m}_FROZEN_SIGNALS.npz',recovery=built[1],reviews=built[2],**built[0])
        for rule in RULES:
            for bps,lag in [(15,0),(30,0),(15,1)]:
                row,_,_=run(m,rule,bps,lag,q,built);rows.append(row)
                pd.DataFrame(rows).to_csv(OUT/'SUMMARY_FIXED.csv',index=False)
    print('FIXED_COMPLETE',len(rows),flush=True)

if __name__=='__main__':main()
