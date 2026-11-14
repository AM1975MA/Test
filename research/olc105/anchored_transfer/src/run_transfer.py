from settings import *
import numpy as np,pandas as pd,json,math,itertools,time
import native_broker_engine as eng
from transfer_contract import require_allowed
F=['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']

def load_q(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def allocate(q,method):
    z={k:v.copy() for k,v in q.items()}
    if method=='MINVAR63':
        import data_transfer as d
        fs,_=d.anchored_data()
        master=pd.DataFrame({t:f.Close for t,f in fs.items()}).sort_index().index
        for k in np.flatnonzero(z['events']):
            i,j=int(z['d1'][0,k]),int(z['d2'][0,k]);w=.5
            # Full pre-signal Close window is restored separately for the first event.
            if i>=0 and j>=0 and i!=j:
                import data_transfer as d
                fs,_=d.anchored_data();day=pd.Timestamp(z['dates'][k]);ticks=z['tickers'];names=[ticks[i],ticks[j]]
                end=pd.Timestamp(day);dates=pd.DatetimeIndex(z['dates'])
                hist=pd.DataFrame({n:fs[n].Close for n in names}).reindex(master)
                c=hist.loc[hist.index<end].tail(64);observed=c.notna();filled=c.ffill();ok=(observed&observed.shift(1,fill_value=False)).all(axis=1)
                lr=np.log(filled/filled.shift()).loc[ok].replace([np.inf,-np.inf],np.nan).dropna()
                if len(lr)>=math.ceil(.8*63):
                    cv=np.cov(lr.to_numpy().T,ddof=1);a,b,co=cv[0,0],cv[1,1],cv[0,1];den=a+b-2*co
                    if den>1e-13 and min(a,b)>1e-15:w=float(np.clip((b-co)/den,.25,.75))
            z['weights'][0,k:]=w
    return z

def sim(q,timing='IMMEDIATE',broker=None,legacy=False,stops=True):
    z={k:v for k,v in q.items() if k!='events'};ev=q['events'];orders=[];stoplog=[]
    r=eng.simulate(z,ev,policy='DELAY' if timing=='DELAY3' else 'IMMEDIATE',fraction=3 if timing=='DELAY3' else 1,fee=.001 if legacy else 0.,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001 if legacy else 0.,ordinary_alarm=False,fast_stop=stops,lock_days=3,broker=broker,broker_log=orders,event_log=stoplog)
    return r,orders,stoplog

def parity():
    checks=[]
    for m in ['EU','USA']:
        q=load_q(BASE/f'data/{"EU165" if m=="EU" else "USA149"}_ORIGINAL_STATE.npz')
        r,_,_=sim(q,legacy=True)
        path=N19/f'results/paths/{m}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz';ref=load_q(path)
        arrays={key:bool(np.array_equal(r[key],ref[key])) for key in F};assert all(arrays.values()),(m,arrays)
        checks.append({'market':m,'arrays':arrays})
    (ROOT/'results/ORIGINAL_ACCOUNTING_PARITY.json').write_text(json.dumps({'status':'PASS_14_ARRAYS_BITWISE','checks':checks},indent=2));print('ACCOUNT_PARITY_PASS',flush=True)

def benchmark(q,which):
    z={k:v.copy() for k,v in q.items()};z['g'][:]=1.;z['alt'][:]=-1;z['d1'][:]=-1;z['d2'][:]=-1;z['events'][:]=False
    names=list(z['tickers']);dates=pd.DatetimeIndex(z['dates'])
    if which=='WORLD_PASSIVE':
        i=names.index('IE00BFY0GT14');z['d1'][:]=i;z['d2'][:]=i;z['weights'][:]=1.;z['events'][0]=True
    else:
        ev=pd.read_csv(ROOT/'results/MOMENTUM_SIGNALS_CORRECTED.csv',parse_dates=['effective_date'])
        for e in ev.itertuples():
            k=dates.get_indexer([e.effective_date])[0];assert k>=0
            z['d1'][0,k:]=names.index(e.isin1);z['d2'][0,k:]=names.index(e.isin2);z['events'][k]=True
        z['weights'][:]=.5
    # risk_on=False below is required for truly passive/simple controls.
    return z

def metric(open_nav,dates,initial):
    v=np.asarray(open_nav,float);d=pd.DatetimeIndex(dates);chain=np.r_[1.,v]
    span=(d[-1]-d[0]).days
    return {'net_cumulative':float(v[-1]-1),'cagr_calendar':float(v[-1]**(365.2425/span)-1) if span>0 else 0.,'maxdd_openings':float((chain/np.maximum.accumulate(chain)-1).min()),'end_equity_eur':float(initial*v[-1]),'sessions':len(v),'start_open':str(d[0].date()),'end_open':str(d[-1].date())}

def run():
    parity();q=load_q(ROOT/'data/TRANSFER_STATE.npz');dates=pd.DatetimeIndex(q['dates']);allowed=set(pd.read_csv(ROOT/'results/CANDIDATE_SOURCE_QA.csv')['isin']);allrows=[];dailies=[];logs=[];stoprows=[];maxresid=0.;st=time.time()
    arms=[(f'TRANSFER_{alloc}_{timing}',allocate(q,alloc),timing,True) for alloc in ['HALF','MINVAR63'] for timing in ['IMMEDIATE','DELAY3']]
    arms += [(nm,benchmark(q,nm),'IMMEDIATE',False) for nm in ['WORLD_PASSIVE','MOM252_TOP2']]
    scenarios=[(10000.,None,None,'GROSS'),(10000.,None,None,'LEGACY')]+[(c,t,b,'BROKER') for c in [5000.,10000.,50000.] for t in [1.,2.] for b in [5.,15.,30.]]
    for name,state,timing,stops in arms:
        np.savez_compressed(ROOT/f'data/{name}_STATE.npz',**state)
        for initial,ticket,bps,mode in scenarios:
            if mode=='LEGACY' and not stops:continue
            broker=None if mode!='BROKER' else {'initial':initial,'ticket':ticket,'impact':bps/10000}
            if stops:r,orders,sl=sim(state,timing,broker,mode=='LEGACY',True)
            else:
                orders=[];sl=[]
                r=eng.simulate({k:v for k,v in state.items() if k!='events'},state['events'],policy='IMMEDIATE',fee=0.,risk_on=False,exposure_timing='OFF',stop_timing='OFF',fast_stop=False,broker=broker,broker_log=orders)
            held=np.any((r['primary_units']+r['defensive_units'])>1e-12,axis=0);require_allowed(state['tickers'][held],allowed)
            res=float(abs(r['ledger'][:,25]).max());maxresid=max(maxresid,res);assert res<1e-10,(name,res)
            ident={'arm':name,'mode':mode,'initial_eur':initial,'ticket_fee_eur':ticket,'shortfall_bps_per_side':bps}
            # Ledger[:,0] is actual opening wealth before current-session trading.
            # Every portfolio is valued on the exact same opening dates.
            daily=pd.DataFrame({'date':dates,'nav_open':r['ledger'][:,0],'cash_after_session':r['free_cash'],'stops':r['ledger'][:,8],'rebalance_cost':r['ledger'][:,5]*initial,'stop_cost':r['ledger'][:,6]*initial,'stop_slippage':r['ledger'][:,7]*initial})
            for k,v in ident.items():daily[k]=v
            dailies.append(daily)
            for row in orders:row.update(ident,date=str(dates[row['index']].date()));logs.append(row)
            for row in sl:row.update(ident,date=str(dates[row['signal_index']].date()));stoprows.append(row)
            for window,end in [('COMPLETED_CYCLES','2026-11-02'),('INCLUDING_PARTIAL_NOVEMBER','2026-11-13')]:
                mask=dates<=end;dd=dates[mask];v=r['ledger'][mask,0]
                before=dates<pd.Timestamp(end);tr=[o for o in orders if pd.Timestamp(o['date'])<pd.Timestamp(end)]
                allrows.append({**ident,'window':window,**metric(v,dd,initial),'ticket_orders':len(tr),'modelled_cost_eur':float((r['ledger'][before,5]+r['ledger'][before,6]+r['ledger'][before,7]).sum()*initial),'stop_count':int(r['ledger'][before,8].sum()),'accounting_max_error':res})
            if mode=='LEGACY' or (mode=='BROKER' and initial==10000 and ticket==1 and bps==15):
                np.savez_compressed(ROOT/f'results/{name}_{mode}_PATH.npz',**r)
        print('ECONOMICS',name,'seconds',round(time.time()-st,1),flush=True)
    pd.DataFrame(allrows).to_csv(ROOT/'results/TRANSFER_SCORECARD.csv',index=False)
    pd.concat(dailies,ignore_index=True).to_csv(ROOT/'results/TRANSFER_DAILY.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(logs).to_csv(ROOT/'results/TRANSFER_ORDERS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(stoprows).to_csv(ROOT/'results/TRANSFER_STOPS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    (ROOT/'results/ECONOMIC_QA.json').write_text(json.dumps({'status':'NATIVE_TRANSFER_EXECUTED','replays':len(dailies),'score_rows':len(allrows),'no_anchor_holdings':True,'max_accounting_error':maxresid,'frozen_model_refit':False,'fractional_adjusted_units':True,'whole_shares_simulated':False,'broker_quotes_certified':False,'prospective':False},indent=2))
    print(pd.DataFrame(allrows).query("mode=='BROKER' and initial_eur==10000 and ticket_fee_eur==1 and shortfall_bps_per_side==15 and window=='COMPLETED_CYCLES'")[['arm','cagr_calendar','maxdd_openings','net_cumulative','ticket_orders','modelled_cost_eur']].to_string(index=False))
if __name__=='__main__':run()
