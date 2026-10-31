from io_common import *
from vector_engine import simulate,LEDGER_COLUMNS
import time
OUT=ROOT/'results';PATHS=OUT/'paths';PATHS.mkdir(exist_ok=True)

def metrics(q,res):
 ds=pd.DatetimeIndex(q['dates']);nav=res['nav'];l=res['ledger'];lr=np.diff(np.log(np.r_[1.,nav]));actual=ds[1:];log=lr[:-1]
 periods={'FULL':(actual[0],actual[-1]),'PRE2025':(pd.Timestamp('2019-02-01'),pd.Timestamp('2024-12-31')),
 'ACTIVE2021_2024':(pd.Timestamp('2021-01-01'),pd.Timestamp('2024-12-31')),
 'CRASH2020':(pd.Timestamp('2020-02-01'),pd.Timestamp('2020-03-31')),
 'LATE2021_2023':(pd.Timestamp('2021-11-01'),pd.Timestamp('2023-12-31')),
 **{str(y):(pd.Timestamp(y,1,1),pd.Timestamp(y,12,31)) for y in range(2019,2027)}}
 out=[]
 for p,(lo,hi) in periods.items():
  mask=(actual>=lo)&(actual<=hi)
  if mask.sum()<10:continue
  x=log[mask];eq=np.exp(x.cumsum());dd=eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1
  ll=l[:-1][mask]
  out.append({'period':p,'first_valuation':str(actual[mask][0].date()),'last_valuation':str(actual[mask][-1].date()),'n':int(mask.sum()),
   'cagr':float(np.expm1(x.mean()*252)),'annual_log':float(x.mean()*252),'period_return':float(np.expm1(x.sum())),'maxdd':float(dd.min()),
   'turnover_annual':float(ll[:,4].mean()*252),'actual_risk_exposure':float(ll[:,12].mean()),'effective_main_positions':float(ll[:,15].mean()),
   'mean_main_positions_above_1bp':float(ll[:,14].mean()),'stops':int(ll[:,8].sum()),'blocked':int(ll[:,11].sum()),'refreshes':int(ll[:,19].sum()),
   'fee_drag_sum':float(np.sum(ll[:,5:8].sum(1)/ll[:,0]))})
 return out

def targets_top4(q,cal,market):
 dates=pd.DatetimeIndex(q['dates']);ts=list(q['tickers']);score=pd.read_csv(SOURCE/f'inputs/{market}_SCORE.csv',index_col=0,parse_dates=True,float_precision='round_trip')
 a=np.zeros_like(q['O']);last=np.zeros(a.shape[1]);event={dates.get_loc(r.entry_date):r.signal_date for r in cal.itertuples() if r.entry_date in dates}
 for k in range(len(a)):
  if k in event:
   row=score.loc[event[k]].dropna().sort_values(ascending=False,kind='stable');chosen=row.index[:4]
   last=np.zeros(a.shape[1]);last[[ts.index(t) for t in chosen]]=1/len(chosen)
  a[k]=last
 return a

def main():
 rows=[];audit=[];start=time.time()
 for market in ['EU','USA']:
  for weight in ['HALF','ORIGINAL']:
   q,e,cal=load(market,weight);top4=targets_top4(q,cal,market)
   for fee in [.001,.003]:
    cfgs=[('LEGACY','IMMEDIATE',1.,True,True,False),('IMMEDIATE','IMMEDIATE',1.,False,True,False),
          ('PARTIAL25','PARTIAL',.25,False,True,False),('PARTIAL50','PARTIAL',.5,False,True,False),('PARTIAL75','PARTIAL',.75,False,True,False),
          ('TOP4','TOP4',1.,False,True,False),('COHORT2','COHORT2',1.,False,True,False)]
    if weight=='HALF':
     cfgs += [(n+'_'+suffix,p,lam,False,r,lag) for n,p,lam in [('IMMEDIATE','IMMEDIATE',1.),('PARTIAL50','PARTIAL',.5)] for suffix,r,lag in [('RISKOFF',False,False),('LAG1',True,True)]]
    for name,policy,lam,slots,risk,lag in cfgs:
     res=simulate(q,e,policy=policy,fraction=lam,fee=fee,legacy_slots=slots,top4=top4,risk_on=risk,lag_systemic=lag)
     key=f'{market}_{weight}_{name}_C{int(fee*10000)}'
     rebuilt=(res['primary_units'][:-1]*q['O'][1:]).sum(1)+(res['defensive_units'][:-1]*q['O'][1:]).sum(1)+res['free_cash'][:-1]
     err=float(np.max(abs(rebuilt-res['nav'][:-1])));aerr=float(np.max(abs(res['ledger'][:-1,25])))
     assert err<1e-10 and aerr<1e-10 and res['nav'].min()>0,(key,err,aerr)
     np.savez_compressed(PATHS/f'{key}.npz',dates=q['dates'],tickers=q['tickers'],**res)
     audit.append({'config':key,'nav_reconstruction_error':err,'pnl_identity_error':aerr,'sha256':digest(PATHS/f'{key}.npz')})
     met=metrics(q,res)
     for row in met:rows.append({'market':market,'weight':weight,'strategy':name,'fee':fee,'config':key,**row})
     f=next(row for row in met if row['period']=='ACTIVE2021_2024');print(key,'CAGR',round(f['cagr']*100,3),'DD',round(f['maxdd']*100,3),'seconds',round(time.time()-start,1),flush=True)
     pd.DataFrame(rows).to_csv(OUT/'SCORECARD.csv',index=False)
     pd.DataFrame(audit).to_csv(OUT/'PATH_VERIFICATION.csv',index=False)
 (OUT/'LEDGER_COLUMNS.json').write_text(json.dumps(LEDGER_COLUMNS,indent=2));print('COMPLETE',len(audit),'paths',flush=True)
if __name__=='__main__':main()
