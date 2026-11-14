from settings import *
import json,numpy as np,pandas as pd
import data_transfer as d
P=ROOT/'results';fs,qa,checks=d.pc.load_frozen();sources=d.candidate_data()[0]
quality=[];risk=[];extremes=[]
for arm in ['TRANSFER_HALF_IMMEDIATE','TRANSFER_HALF_DELAY3','TRANSFER_MINVAR63_IMMEDIATE','TRANSFER_MINVAR63_DELAY3','WORLD_PASSIVE','MOM252_TOP2']:
    q=np.load(ROOT/f'data/{arm}_STATE.npz');a=np.load(P/f'{arm}_BROKER_PATH.npz');dates=pd.DatetimeIndex(q['dates']);names=list(q['tickers']);units=a['primary_units']+a['defensive_units']
    badholding=0;missinghold=0;zerohold=0;seen=set()
    for i in np.flatnonzero(np.any(units>1e-12,axis=0)):
        isin=names[i]
        if isin not in fs:continue
        f=fs[isin].reindex(dates);held=units[:,i]>1e-12
        bad=(f.geometry_flag.eq(True)).to_numpy();vol=f.Volume.eq(0).to_numpy();missing=~q['observed'][:,i]
        badholding+=int((held&bad).sum());zerohold+=int((held&vol).sum());missinghold+=int((held&missing).sum());seen.add(isin)
        for k in np.flatnonzero(held&bad):quality.append({'arm':arm,'date':dates[k],'isin':isin,'issue':'HELD_GEOMETRY'})
    stop=pd.read_csv(P/'TRANSFER_STOPS.csv.gz',parse_dates=['date']);stop=stop[(stop.arm==arm)&(stop['mode']=='BROKER')&(stop.initial_eur==10000)&(stop.ticket_fee_eur==1)&(stop.shortfall_bps_per_side==15)]
    stopbad=0
    for e in stop.itertuples():
        flag=bool(fs[e.ticker].loc[e.date,'geometry_flag']);stopbad+=int(flag)
    risk.append({'arm':arm,'unique_held_isins':len(seen),'held_bad_geometry_asset_days':badholding,'held_zero_volume_asset_days':zerohold,'held_missing_open_asset_days':missinghold,'stops_bad_geometry':stopbad,'stops_total':len(stop),'same_session_new_position_stops':int((stop.newly_bought_quantity>1e-12).sum()) if len(stop) else 0})
    nav=a['ledger'][:,0];rr=nav[1:]/nav[:-1]-1
    for k in np.argsort(rr)[:10]:
        u=a['primary_units'][k]+a['defensive_units'][k];ii=np.flatnonzero(u>1e-12)
        extremes.append({'arm':arm,'date_open':dates[k],'date_next_open':dates[k+1],'portfolio_return':rr[k],'held':';'.join(names[j] for j in ii),'stop_count':a['ledger'][k,8]})
pd.DataFrame(risk).to_csv(P/'QUOTE_RISK_INTERSECTION.csv',index=False);pd.DataFrame(quality).to_csv(P/'HELD_BAD_GEOMETRY.csv',index=False);pd.DataFrame(extremes).to_csv(P/'WORST_OPEN_INTERVALS.csv',index=False)
# Monthly/annual returns on opening valuation with all first-session costs included.
s=pd.read_csv(P/'TRANSFER_DAILY.csv.gz',parse_dates=['date']);s=s.query("mode=='BROKER' and initial_eur==10000 and ticket_fee_eur==1 and shortfall_bps_per_side==15")
rows=[]
for arm,g in s.groupby('arm'):
    g=g.sort_values('date');v=g.nav_open.to_numpy();rets=v[1:]/v[:-1]-1;dat=g.date.iloc[:-1]
    for freq in ['M','Y']:
        for key,ix in pd.Series(range(len(rets)),index=dat.to_numpy()).groupby(dat.dt.to_period(freq).to_numpy()):
            jj=ix.to_numpy();rows.append({'arm':arm,'frequency':freq,'period':str(key),'first_open':g.date.iloc[jj[0]],'last_open':g.date.iloc[jj[-1]+1],'net_return':float(np.prod(1+rets[jj])-1),'partial':str(key) in ['2020','2020-03','2026','2026-11']})
pd.DataFrame(rows).to_csv(P/'PERIOD_RETURNS.csv',index=False)
print(pd.DataFrame(risk).to_string(index=False))
