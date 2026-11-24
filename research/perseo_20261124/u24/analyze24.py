from core24 import *

def main():
    summary=pd.read_csv(OUT/'SUMMARY.csv');monthly=[];annual=[];regimes=[];exposure=[]
    for m in MARKETS:
        q=state(m);cash=np.array(['CASH_' in t for t in q['tickers']]);ds=pd.DatetimeIndex(q['dates'])
        for row in summary[summary.market==m].itertuples():
            z=load(OUT/f'{tag(m,row.rule,row.bps,row.lag)}.npz');nav=z['nav'];meta=dict(market=m,rule=row.rule,bps=row.bps,lag=row.lag)
            mo=months(ds,nav)
            monthly.extend(dict(**meta,month=str(d),net_return=float(v)) for d,v in mo.items())
            annual.extend(dict(**meta,year=int(y),net_return=float((1+v).prod()-1)) for y,v in mo.groupby(mo.index.year))
            for period,lo,hi in [('2020_2022','2020-01-02','2023-01-03'),('2023_2026','2023-01-03','2026-07-01')]:
                take=(ds>=lo)&(ds<=hi);regimes.append(dict(**meta,period=period,**metrics(ds[take],nav[take])))
            units=z['primary_units']+z['defensive_units'];cashval=(units[:,cash]*q['O'][:,cash]).sum(1)+z['free_cash']
            total=(units*q['O']).sum(1)+z['free_cash'];exposure.append(dict(**meta,average_cash_weight=float(np.mean(cashval[:-1]/total[:-1]))))
    monthly=pd.DataFrame(monthly);monthly.to_csv(OUT/'MONTHLY.csv',index=False)
    pd.DataFrame(annual).to_csv(OUT/'ANNUAL.csv',index=False);pd.DataFrame(regimes).to_csv(OUT/'REGIMES.csv',index=False);pd.DataFrame(exposure).to_csv(OUT/'EXPOSURE.csv',index=False)
    diagnosis=[]
    for (m,rule,bps,lag),a in monthly[monthly.rule!='BASE'].groupby(['market','rule','bps','lag']):
        b=monthly[(monthly.market==m)&(monthly.rule=='BASE')&(monthly.bps==bps)&(monthly.lag==lag)].set_index('month').net_return
        for r in a.itertuples():diagnosis.append(dict(market=m,rule=rule,bps=bps,lag=lag,month=r.month,base_return=float(b[r.month]),new_return=r.net_return,delta=r.net_return-float(b[r.month])))
    diagnosis=pd.DataFrame(diagnosis);diagnosis.to_csv(OUT/'MONTHLY_DIAGNOSIS.csv',index=False)
    stat=[];n=78;rng=np.random.default_rng(240024);ix=((rng.integers(0,n,(3000,7,1))+np.arange(12))%n).reshape(3000,-1)[:,:n]
    for (rule,bps,lag),a in diagnosis.groupby(['rule','bps','lag']):
        dif=[]
        for m in MARKETS:
            s=a[a.market==m].sort_values('month');assert len(s)==n
            d=(np.log1p(s.new_return)-np.log1p(s.base_return)).to_numpy();dif.append(d);boot=d[ix].mean(1)*12
            stat.append(dict(market=m,rule=rule,bps=bps,lag=lag,annual_log_delta=float(d.mean()*12),ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),bootstrap_fraction_positive=float(np.mean(boot>0))))
        ar=np.array(dif).T;boot=np.min(ar[ix].mean(1)*12,axis=1)
        stat.append(dict(market='WORST_OF_THREE',rule=rule,bps=bps,lag=lag,annual_log_delta=float(ar.mean(0).min()*12),ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),bootstrap_fraction_positive=float(np.mean(boot>0))))
    pd.DataFrame(stat).to_csv(OUT/'STATISTICS.csv',index=False)
    print('ANALYZED',len(summary),'accounts',len(monthly),'monthly rows')

if __name__=='__main__':main()
