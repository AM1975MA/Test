from engine20 import *
from allocation19 import *
import hashlib,time
NEW=Path(__file__).resolve().parent
DEST=NEW/'results';DEST.mkdir(exist_ok=True)
STATES=NEW/'states';STATES.mkdir(exist_ok=True)
MODES=['BASE','ISOLATED','VOLATILITY','REENTRY','COMBINED','GLOBAL_ONLY','NO_RISK']

def signals(q):
 c=pd.DataFrame(q['C']).where(q.get('low_observed',np.ones_like(q['C'],bool)))
 vol=c.pct_change(fill_method=None).rolling(21,min_periods=15).std().shift(1)
 stop=(3*vol).clip(.03,.10).fillna(.055).to_numpy()
 rebound=((c>c.rolling(5,min_periods=5).mean())&(c>c.shift(1))).shift(1,fill_value=False).to_numpy()
 return stop,rebound

def prepare(m,fam):
 path=STATES/f'{m}_{fam}.npz'
 if path.exists():return load(path)
 if fam=='NATIVE_REFERENCE':raw=base(m)
 else:
  dec=pd.read_csv(RESULTS/'DECISIONS.csv',parse_dates=['signal_date'])
  raw=state(m,dec[(dec.market==m)&(dec.candidate=='LOCAL')],start=None)
 if m=='USA':raw=add_cash(raw)
 raw['stop_threshold'],raw['rebound']=signals(raw)
 q=crop(raw,'2020-01-02');np.savez_compressed(path,**q);return q

def run(q,name,m,fam,bps=15,modes=None,save=True):
 sim=engine();q=q.copy();idx=MODES.index(name) if name in MODES else 0
 q['risk_mode']=np.full(len(q['dates']),idx if idx<6 else 0,int) if modes is None else modes
 orders=[];stops=[];risk=name!='NO_RISK'
 r=sim(q,q['events'],policy='IMMEDIATE',fraction=1,fee=0,stop_friction=0,exposure_timing='PREVIOUS' if risk else 'OFF',stop_timing='NOW' if risk else 'OFF',ordinary_alarm=False,fast_stop=risk,lock_days=3,risk_on=risk,broker={'initial':10000.,'ticket':1.,'impact':bps/10000},broker_log=orders,event_log=stops)
 nav=r['ledger'][:,0];units=r['primary_units']+r['defensive_units'];res=float(abs(r['ledger'][:-1,-1]).max());err=float(abs((units[:-1]*q['O'][1:]).sum(1)+r['free_cash'][:-1]-nav[1:]).max());assert res<1e-10 and err<1e-10
 od=pd.DataFrame(orders);fees=od.groupby('index').cost_eur.sum().reindex(range(len(nav)),fill_value=0).to_numpy()/10000
 feeerr=float(abs(fees-r['ledger'][:,5]-r['ledger'][:,6]).max());assert feeerr<1e-10
 tag=f'{m}_{fam}_{name}_{bps}'
 if name=='BASE' and bps==15:
  old=load(OUT/f'EXEC_{m}_{fam}_HALF_IMMEDIATE_2020-01-02.npz')
  assert np.array_equal(nav,old['ledger'][:,0]),(tag,float(abs(nav-old['ledger'][:,0]).max()))
 row=dict(market=m,family=fam,rule=name,bps=bps,**metrics(q['dates'],nav),orders=len(od),stops=len(stops),cost_currency=float(od.cost_eur.sum()),wealth_error=err,accounting_error=res,fee_error=feeerr)
 if save:
  np.savez_compressed(DEST/f'{tag}.npz',dates=q['dates'],nav=nav,risk_mode=q['risk_mode'],**{k:v for k,v in r.items() if k!='nav'})
  od.to_csv(DEST/f'{tag}_ORDERS.csv',index=False);pd.DataFrame(stops).to_csv(DEST/f'{tag}_STOPS.csv',index=False)
 print(tag,round(row['cagr']*100,3),round(row['maxdd']*100,3),flush=True)
 return row,periods(q['dates'],nav,dict(market=m,family=fam,rule=name,bps=bps))

def main():
 rows=[];months=[]
 for m in ['EU','USA','TR']:
  for fam in (['LOCAL','NATIVE_REFERENCE'] if m!='TR' else ['LOCAL']):
   q=prepare(m,fam)
   for mode in MODES:
    r,mo=run(q,mode,m,fam);rows.append(r);months.extend(mo)
   pd.DataFrame(rows).to_csv(DEST/'SCREEN.csv',index=False);pd.DataFrame(months).to_csv(DEST/'MONTHLY_SCREEN.csv',index=False)
 (NEW/'INPUTS.json').write_text(json.dumps({str(p.relative_to(OLD)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OLD/'results/DECISIONS.csv',OLD/'sources/unified/common_cost_engine.py',OLD/'cash_execution19.py']},indent=2))
if __name__=='__main__':main()
