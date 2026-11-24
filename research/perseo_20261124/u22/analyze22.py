from core22 import *

def main():
    monthly=[];annual=[];regimes=[];decisions=[];diagnosis=[];cal=[]
    for m in MARKETS:
        q=state(m);ds=pd.DatetimeIndex(q['dates'])
        for rule in RULES:
            for bps in [15,30]:
                tag=f'{m}_{rule}_{bps}';z=load(OUT/f'{tag}.npz');nav=z['nav'];meta=dict(market=m,rule=rule,bps=bps)
                mo=month_returns(ds,nav)
                monthly.extend(dict(**meta,month=str(dt),net_return=float(r)) for dt,r in mo.items())
                annual.extend(dict(**meta,year=int(y),net_return=float((1+a).prod()-1)) for y,a in mo.groupby(mo.index.year))
                for label,lo,hi in [('2020_2022','2020-01-02','2023-01-03'),('2023_2026','2023-01-03','2026-07-01')]:
                    take=(ds>=lo)&(ds<=hi);regimes.append(dict(**meta,period=label,**metrics(ds[take],nav[take])))
                if rule=='BASE':continue
                a=pd.read_csv(OUT/f'{tag}_DECISIONS.csv')
                for r in a.to_dict('records'):
                    p=np.zeros(len(q['tickers']));h=p.copy()
                    for i,v in json.loads(r['proposal']).items():p[int(i)]=v
                    for i,v in json.loads(r['held']).items():h[int(i)]=v
                    future=forward(q,int(r['index']),p,h,int(r['horizon']))
                    if future is None:continue
                    y,exit_date=future
                    decisions.append(dict(meta,**r,realized_gross_advantage=y,realized_net_advantage=y-r['estimated_cost'],outcome_date=exit_date))
    monthly=pd.DataFrame(monthly);annual=pd.DataFrame(annual);dec=pd.DataFrame(decisions)
    monthly.to_csv(OUT/'MONTHLY.csv',index=False);annual.to_csv(OUT/'ANNUAL.csv',index=False)
    pd.DataFrame(regimes).to_csv(OUT/'REGIMES.csv',index=False);dec.to_csv(OUT/'FORECASTS_VS_OUTCOMES.csv',index=False)
    for (m,rule,bps,allow),a in dec.groupby(['market','rule','bps','allow']):
        # This is descriptive and overlapping, not a sample of independent trades.
        cal.append(dict(market=m,rule=rule,bps=bps,accepted=allow,reviews=len(a),mean_prediction=a['mean'].mean(),mean_realized_net=a.realized_net_advantage.mean(),positive_net_fraction=(a.realized_net_advantage>0).mean(),mean_estimated_cost=a.estimated_cost.mean(),correlation=a['mean'].corr(a.realized_gross_advantage)))
    pd.DataFrame(cal).to_csv(OUT/'ADMISSION_DIAGNOSIS.csv',index=False)
    for (m,rule,bps),a in monthly[monthly.rule!='BASE'].groupby(['market','rule','bps']):
        base=monthly[(monthly.market==m)&(monthly.rule=='BASE')&(monthly.bps==bps)].set_index('month')
        for r in a.itertuples():
            br=float(base.loc[r.month,'net_return']);diagnosis.append(dict(market=m,rule=rule,bps=bps,month=r.month,base_return=br,new_return=r.net_return,delta=r.net_return-br))
    pd.DataFrame(diagnosis).to_csv(OUT/'MONTHLY_DIAGNOSIS.csv',index=False)
    stats=[];rng=np.random.default_rng(220023)
    # Only the active evaluation period, avoiding three unchanged years diluting uncertainty.
    active=monthly[monthly.month>='2023-01'];dates=sorted(active.month.unique());n=len(dates)
    ix=((rng.integers(0,n,(3000,int(np.ceil(n/12)),1))+np.arange(12))%n).reshape(3000,-1)[:,:n]
    for bps in [15,30]:
        for rule in RULES[1:]:
            dif=[]
            for m in MARKETS:
                a=active[(active.market==m)&(active.rule==rule)&(active.bps==bps)].set_index('month').reindex(dates).net_return.to_numpy()
                b=active[(active.market==m)&(active.rule=='BASE')&(active.bps==bps)].set_index('month').reindex(dates).net_return.to_numpy()
                d=np.log1p(a)-np.log1p(b);dif.append(d);bs=d[ix].mean(1)*12
                stats.append(dict(market=m,rule=rule,bps=bps,annual_log_delta=float(12*d.mean()),ci_low=float(np.quantile(bs,.025)),ci_high=float(np.quantile(bs,.975)),months=n))
            ar=np.array(dif).T;bs=np.min(ar[ix].mean(1)*12,axis=1)
            stats.append(dict(market='WORST_OF_THREE',rule=rule,bps=bps,annual_log_delta=float(min(ar.mean(0)*12)),ci_low=float(np.quantile(bs,.025)),ci_high=float(np.quantile(bs,.975)),months=n))
    pd.DataFrame(stats).to_csv(OUT/'STATISTICS.csv',index=False)
    s=pd.read_csv(OUT/'SUMMARY.csv');print(s[s.bps==15][['market','rule','cagr','maxdd','orders']].to_string(index=False))
    print('VETO_DIAGNOSIS');print(pd.DataFrame(cal).query('bps == 15 and accepted == False').to_string(index=False))
    print('WORST_MONTHS');print(pd.DataFrame(diagnosis).query('rule == "NET21" and bps == 15').sort_values('delta').head(9).to_string(index=False))

if __name__=='__main__':main()
