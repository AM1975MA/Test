from run_transitions import *
rows=[];aud=[]
for m in ['EU','USA']:
 for w in ['HALF','ORIGINAL']:
  q,e,cal=load(m,w)
  for fee in [.001,.003]:
   for days in [5,21]:
    name=f'PHASE{days}';key=f'{m}_{w}_{name}_C{int(fee*10000)}'
    r=simulate(q,e,policy='PHASE',fraction=days,fee=fee)
    actual=((r['primary_units'][:-1]+r['defensive_units'][:-1])*q['O'][1:]).sum(1)+r['free_cash'][:-1]
    err=float(np.max(abs(actual-r['nav'][:-1])));assert err<1e-10
    np.savez_compressed(PATHS/f'{key}.npz',dates=q['dates'],tickers=q['tickers'],**r)
    aud.append({'config':key,'nav_reconstruction_error':err,'pnl_identity_error':float(np.max(abs(r['ledger'][:,25]))),'sha256':digest(PATHS/f'{key}.npz')})
    ms=metrics(q,r)
    for row in ms:rows.append({'market':m,'weight':w,'strategy':name,'fee':fee,'config':key,**row})
    z=next(x for x in ms if x['period']=='ACTIVE2021_2024');print(key,round(z['cagr']*100,2),round(z['maxdd']*100,2),flush=True)
pd.DataFrame(rows).to_csv(OUT/'FINITE_SCORECARD.csv',index=False);pd.DataFrame(aud).to_csv(OUT/'FINITE_VERIFICATION.csv',index=False)
