from core24 import *

def main():
    allrows=[];errors=[];sensitivity=[]
    for m in MARKETS:
        q=state(m);ds=pd.DatetimeIndex(q['dates']);ids={t:i for i,t in enumerate(q['tickers'])};D,N=q['O'].shape
        for rule in ['BASE','PROFIT_RAMP','CONFIRM_RAMP','WF_ECONOMIC','WF_PRUDENT']:
            name=tag(m,rule,15);z=load(OUT/f'{name}.npz');u=z['primary_units']+z['defensive_units'];nav=z['nav']
            orders=pd.read_csv(OUT/f'{name}_ORDERS.csv');stops=pd.read_csv(OUT/f'{name}_STOPS.csv')
            fills={(int(r.signal_index),r.ticker):r.fill_price for r in stops.itertuples()}
            groups={int(k):v for k,v in orders.groupby('index')};month=None;contribution={};mx=0.
            for k in range(D-1):
                this=str(ds[k].to_period('M'))
                if this!=month:
                    if month is not None:
                        allrows.extend(dict(market=m,rule=rule,month=month,ticker=t,contribution=x) for t,x in contribution.items())
                    month=this;start_nav=nav[k];contribution={}
                current=u[k-1] if k else np.zeros(N);pnl=current*(q['O'][k+1]-q['O'][k]);cost=0.
                if k in groups:
                    for r in groups[k].itertuples():
                        j=ids[r.ticker];price=q['O'][k,j] if r.kind=='REBALANCE' else fills[k,r.ticker]
                        qty=r.signed_notional_eur/10000/price
                        pnl[j]+=qty*(q['O'][k+1,j]-price);cost+=r.cost_eur/10000
                mx=max(mx,abs(pnl.sum()-cost-(nav[k+1]-nav[k])))
                for j in np.flatnonzero(abs(pnl)>1e-15):
                    t=str(q['tickers'][j]);contribution[t]=contribution.get(t,0)+float(pnl[j]/start_nav)
                contribution['COSTS']=contribution.get('COSTS',0)-cost/start_nav
            allrows.extend(dict(market=m,rule=rule,month=month,ticker=t,contribution=x) for t,x in contribution.items())
            assert mx<1e-9,(name,mx)
            errors.append(dict(market=m,rule=rule,pnl_error=mx))
    a=pd.DataFrame(allrows);a.to_csv(OUT/'MONTHLY_TICKER_ATTRIBUTION.csv',index=False)
    mo=pd.read_csv(OUT/'MONTHLY.csv');linked=a.groupby(['market','rule','month']).contribution.sum().reset_index().merge(mo.query('bps==15 and lag==0'),on=['market','rule','month']);err=float(abs(linked.contribution-linked.net_return).max());assert err<1e-9
    base=a.query('rule=="BASE"').drop(columns='rule').rename(columns={'contribution':'base_contribution'})
    differences=[]
    for rule in a.rule.unique():
        if rule=='BASE':continue
        c=a[a.rule==rule].merge(base,on=['market','month','ticker'],how='outer').fillna({'contribution':0.,'base_contribution':0.,'rule':rule})
        c['delta_contribution']=c.contribution-c.base_contribution;differences.append(c)
    pd.concat(differences,ignore_index=True).to_csv(OUT/'MONTHLY_TICKER_DELTA.csv',index=False)
    diag=pd.read_csv(OUT/'MONTHLY_DIAGNOSIS.csv').query('bps==15 and lag==0')
    for (m,rule),g in diag.groupby(['market','rule']):
        d=np.log1p(g.new_return)-np.log1p(g.base_return);total=float(d.sum());best=d.nlargest(3)
        # Descriptive removal: not an investable return series and not a retrained model.
        sensitivity.append(dict(market=m,rule=rule,annual_log_delta=float(12*d.mean()),annual_log_delta_without_best3=float(12*d.drop(best.index).mean()),share_log_advantage_best3=float(best.sum()/total) if total>1e-12 else None,best3_months=';'.join(g.loc[best.index,'month']),months_gain_over_5bp=int((g.delta>.0005).sum()),months_loss_over_5bp=int((g.delta<-.0005).sum())))
    pd.DataFrame(sensitivity).to_csv(OUT/'CONCENTRATION_SENSITIVITY.csv',index=False)
    (OUT/'ATTRIBUTION_QA.json').write_text(json.dumps(dict(status='PASS',account_errors=errors,max_monthly_return_error=err),indent=2));print('ATTRIBUTION_PASS',len(a),err,flush=True)

if __name__=='__main__':main()
