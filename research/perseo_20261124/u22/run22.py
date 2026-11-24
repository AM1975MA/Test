from core22 import *
from engine22 import simulate
import shutil,time

def initialize():
    upstream=ROOT.parent/'perseo_u20'
    rows=[]
    for m in MARKETS:
        fam='NATIVE_REFERENCE' if m=='USA' else 'TRANSFER_LOCAL'
        source=upstream/'states'/f'{m}_{fam}.npz'
        dst=INPUT/f'{m}_STATE.npz'
        if not dst.exists():shutil.copy2(source,dst)
        ref=upstream/'results'/(f'{m}_NATIVE_REFERENCE_BASE_15.npz' if m=='USA' else f'{m}_TRANSFER_LOCAL_TRANSFER_BASE_15.npz')
        if not (INPUT/f'{m}_REFERENCE.npz').exists():
            with np.load(ref) as z:np.savez_compressed(INPUT/f'{m}_REFERENCE.npz',nav=z['nav'],dates=z['dates'])
        rows.append(dict(market=m,file=dst.name,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),source=str(source)))
    (INPUT/'MANIFEST.json').write_text(json.dumps(rows,indent=2))

def run(m,rule,bps,models,q=None,f=None,save=True):
    if q is None:q=state(m)
    if rule!='BASE' and f is None:f=features(q)
    gate=None if rule=='BASE' else Gate(q,f,models,rule,bps)
    orders=[];stops=[]
    r=simulate(q,q['events'],policy='IMMEDIATE',fraction=1,fee=0,stop_friction=0,exposure_timing='PREVIOUS',stop_timing='NOW',ordinary_alarm=False,fast_stop=True,lock_days=3,risk_on=True,broker={'initial':10000.,'ticket':1.,'impact':bps/10000},broker_log=orders,event_log=stops,selection_hook=gate)
    nav=r['ledger'][:,0];units=r['primary_units']+r['defensive_units'];od=pd.DataFrame(orders)
    wealth_error=float(abs((units[:-1]*q['O'][1:]).sum(1)+r['free_cash'][:-1]-nav[1:]).max())
    accounting_error=float(abs(r['ledger'][:-1,-1]).max())
    fee=od.groupby('index').cost_eur.sum().reindex(range(len(nav)),fill_value=0).to_numpy()/10000
    fee_error=float(abs(fee-r['ledger'][:,5]-r['ledger'][:,6]).max())
    assert max(wealth_error,accounting_error,fee_error)<1e-9
    if rule=='BASE' and bps==15:
        ref=load(INPUT/f'{m}_REFERENCE.npz');assert np.array_equal(nav,ref['nav'])
    tag=f'{m}_{rule}_{bps}';dec=pd.DataFrame(gate.log if gate else [])
    row=dict(market=m,rule=rule,bps=bps,**metrics(q['dates'],nav),orders=len(od),stops=len(stops),cost_currency=float(od.cost_eur.sum()),turnover_currency=float(od.notional_eur.sum()),reviews=len(dec),accepted=int(dec.allow.sum()) if len(dec) else 0,wealth_error=wealth_error,accounting_error=accounting_error,fee_error=fee_error)
    if save:
        np.savez_compressed(OUT/f'{tag}.npz',dates=q['dates'],nav=nav,**{key:r[key] for key in ['primary_units','defensive_units','free_cash','ledger','targets']})
        od.to_csv(OUT/f'{tag}_ORDERS.csv',index=False);pd.DataFrame(stops).to_csv(OUT/f'{tag}_STOPS.csv',index=False)
        dec.to_csv(OUT/f'{tag}_DECISIONS.csv',index=False)
        print(tag,round(row['cagr']*100,3),round(row['maxdd']*100,3),'orders',len(od),'reviews',len(dec),flush=True)
    return row,r,dec

def training():
    rows=[]
    for m in MARKETS:
        q=state(m);f=features(q);old=load(OUT/f'{m}_BASE_15.npz');history=[]
        cash=np.array(['CASH_' in s for s in q['tickers']])
        for k in np.flatnonzero(q['events']):
            p=target(q,k);past=list(history[-3:]);history.append(p)
            if k==0 or p[cash].sum()>0:continue
            held=old['primary_units'][k-1]*q['PC'][k]
            if held.sum()>1e-12:past.append(held/held.sum())
            seen=set()
            for h in past:
                key=tuple(np.round(h,8))
                if key in seen or np.max(abs(p-h))<1e-8 or h[cash].sum()>0:continue
                seen.add(key);x=pair_x(f,k,p,h)
                if x is None:continue
                for hor in HORIZONS:
                    result=forward(q,k,p,h,hor)
                    if result is None:continue
                    y,exit_date=result;dt=pd.Timestamp(q['dates'][k])
                    rows.append(dict(market=m,signal_date=str(dt.date()),month=str(dt.to_period('M')),index=k,horizon=hor,exit_date=exit_date,y=y,**dict(zip(XNAMES,x))))
        print('TRAIN_ROWS',m,len(rows),flush=True)
    a=pd.DataFrame(rows);a.to_csv(OUT/'TRAINING_PAIRS.csv',index=False);return a

def main():
    initialize();rows=[]
    for m in MARKETS:
        q=state(m)
        for bps in [15,30]:
            row,_,_=run(m,'BASE',bps,None,q=q);rows.append(row)
    data=training();models=fit_models(data)
    for m in MARKETS:
        q=state(m);f=features(q)
        for rule in RULES[1:]:
            for bps in [15,30]:
                row,_,_=run(m,rule,bps,models,q=q,f=f);rows.append(row)
                pd.DataFrame(rows).to_csv(OUT/'SUMMARY.csv',index=False)
    print('COMPLETE',len(rows),flush=True)

if __name__=='__main__':main()
