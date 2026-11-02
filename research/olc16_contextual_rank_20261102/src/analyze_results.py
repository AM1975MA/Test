"""Paired temporal diagnostics, no further parameter or strategy selection."""
import numpy as np,pandas as pd,json
from experiment import ROOT,MARKETS,readcsv,dump
PAIRS=[('PAIR_CONTEXT','PAIR_STATIC'),('TOP2_CONTEXT','TOP2_STATIC'),
 ('PAIR_CONTEXT_REVALUE','PAIR_STATIC_REVALUE'),('TOP2_CONTEXT_REVALUE','TOP2_STATIC_REVALUE'),
 ('TOP2_CONTEXT_REVALUE','TOP2_CONTEXT'),('TOP2_CONTEXT_REVALUE','CUM_FIT'),
 ('TOP2_CONTEXT_REVALUE','ORIGINAL')]

def intervals(values,annual=1):
    a=np.asarray(values,float);n=len(a);rng=np.random.default_rng(20261102)
    starts=rng.integers(0,n,(4000,(n+5)//6));idx=(starts[:,:,None]+np.arange(6)[None,None,:])%n
    sampled=a[idx.reshape(4000,-1)[:,:n]];boot=np.nanmean(sampled,axis=1)*annual
    lo,hi=np.quantile(boot,[.025,.975])
    return float(np.nanmean(a)*annual),float(lo),float(hi)

def main():
    o=readcsv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz');out=[];grid=pd.period_range('2021-01','2024-12',freq='M')
    for m in MARKETS:
        for stage in ['CURRENT','FUSION']:
            p=o[(o.market==m)&(o.stage==stage)&(o.period=='PRE2025')&(o.horizon=='U42')].pivot(index='date',columns='variant',values='top2_excess');p.index=p.index.to_period('M');p=p.reindex(grid)
            for a,b in PAIRS:
                vals=(p[a]-p[b]).to_numpy();d,lo,hi=intervals(vals)
                out.append(dict(market=m,stage=stage,candidate=a,baseline=b,metric='U42',n=int(np.isfinite(vals).sum()),difference=d,lower=lo,upper=hi))
    pd.DataFrame(out).to_csv(ROOT/'results/PAIRED_UNCERTAINTY.csv',index=False)
    choices=readcsv(ROOT/'results/CHOICES.csv.gz');cr=[]
    for m in MARKETS:
        for stage in ['CURRENT','FUSION']:
            p=choices[(choices.market==m)&(choices.stage==stage)].pivot(index='date',columns='variant',values='pair')
            for a,b in PAIRS:cr.append(dict(market=m,stage=stage,candidate=a,baseline=b,n=len(p),changed=int((p[a]!=p[b]).sum())))
    pd.DataFrame(cr).to_csv(ROOT/'results/FINAL_CHOICE_CONTRASTS.csv',index=False)
    score=readcsv(ROOT/'results/SCORECARD.csv');ddrows=[];monthly=[]
    for m in MARKETS:
        for v in ['ORIGINAL','CUM_FIT','TOP2_STATIC_REVALUE','TOP2_CONTEXT_REVALUE']:
            p=np.load(ROOT/f'results/paths/{m}_{v}_IMMEDIATE_FULL_C10.npz');dates=pd.DatetimeIndex(p['dates'])[1:];nav=p['nav'][:-1]
            dd=nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1;k=int(dd.argmin());peak=int(np.argmax(np.r_[1.,nav[:k+1]]))
            ddrows.append(dict(market=m,variant=v,drawdown=float(dd[k]),trough=str(dates[k].date()),peak=str(dates[max(peak-1,0)].date())))
            lr=np.log(nav/np.r_[1.,nav[:-1]])
            frame=pd.DataFrame({'date':dates,'log_return':lr});frame['month']=frame.date.dt.to_period('M').astype(str)
            z=frame.groupby('month').log_return.sum().reset_index();z['market']=m;z['variant']=v;monthly.append(z)
    mon=pd.concat(monthly,ignore_index=True);mon.to_csv(ROOT/'results/MONTHLY_LOG_RETURNS.csv',index=False)
    portci=[];contrib=[]
    for m in MARKETS:
        p=mon[mon.market==m].pivot(index='month',columns='variant',values='log_return').reindex(grid.astype(str))
        for b in ['TOP2_STATIC_REVALUE','CUM_FIT','ORIGINAL']:
            vals=p.TOP2_CONTEXT_REVALUE-p[b];delta,lo,hi=intervals(vals,12)
            portci.append(dict(market=m,candidate='TOP2_CONTEXT_REVALUE',baseline=b,metric='annual_log_return_difference',difference=delta,lower=lo,upper=hi,n=48))
            for date,x in vals.items():contrib.append(dict(market=m,baseline=b,month=date,difference=float(x)))
    pd.DataFrame(portci).to_csv(ROOT/'results/PORTFOLIO_UNCERTAINTY.csv',index=False)
    pd.DataFrame(contrib).to_csv(ROOT/'results/MONTHLY_DIFFERENCES.csv',index=False)
    pd.DataFrame(ddrows).to_csv(ROOT/'results/DRAWDOWN_DATES.csv',index=False)
    # Export usable compact tables; keep every variant in the full tables.
    score[(score.policy=='IMMEDIATE')&(score['mode']=='FULL')&(score.fee==.001)].to_csv(ROOT/'results/MAIN_PORTFOLIO_COMPARISONS.csv',index=False)
    refs=pd.concat([pd.read_csv(p) for p in sorted((ROOT/'results').glob('REFIT_CHECK_*.csv'))])
    dump(ROOT/'results/VERIFIED_SUMMARY.json',dict(new_main_models=24,training_context_null_models=24,inner_fits=66,optimization_starts=342,
       ETF_base_refits=0,portfolio_paths=208,reference_paths=48,new_tests=19,parent15_tests=25,
       model_refits_verified=len(refs),max_parameter_refit_error=float(refs.parameter_error.max()),max_model_prediction_error=float(refs.prediction_error.max()),
       accounting=json.loads((ROOT/'results/ACCOUNT_CHECK.json').read_text()),
       native_checks=[json.loads((ROOT/f'results/NATIVE_CHECK_{m}.json').read_text()) for m in MARKETS],
       causal_checks=len(json.loads((ROOT/'results/CAUSAL_CHECKS.json').read_text())),
       self_review_not_external=True,reused_history=True,memory_extension_post_observation=True))
    print(pd.DataFrame(out).query("candidate=='TOP2_CONTEXT_REVALUE' and baseline=='TOP2_STATIC_REVALUE' and stage=='FUSION'").to_string(index=False))
    print(pd.DataFrame(ddrows).to_string(index=False))
if __name__=='__main__':main()
