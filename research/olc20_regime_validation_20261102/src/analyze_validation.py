"""Descriptive negative controls and fixed sensitivity panels; no winner selection."""
import json
import numpy as np,pandas as pd
from paths import ROOT
from experiment import dump

def main():
    r=ROOT/'results';f=pd.concat([pd.read_csv(p) for p in (r/'portfolios').glob('*/*_SCORECARD.csv')],ignore_index=True)
    assert len(f[['trial','market','contract','fee']].drop_duplicates())==480
    f.to_csv(r/'SCORECARD.csv',index=False)
    out=[]
    for keys,g in f.groupby(['market','contract','fee','period']):
        au=g[g.trial=='AUTH'].iloc[0];st=g[g.trial=='STATIC'].iloc[0];nu=g[g.trial.str.startswith('NULL')]
        assert len(nu)==50
        for metric in ('cagr','maxdd','cvar05'):
            vals=nu[metric].to_numpy();av=au[metric]
            out.append(dict(zip(['market','contract','fee','period'],keys),metric=metric,authentic=av,static=st[metric],
               nulls=50,at_least_as_good=int((vals>=av-1e-14).sum()),null_min=vals.min(),null_q05=np.quantile(vals,.05),
               null_median=np.median(vals),null_q95=np.quantile(vals,.95),null_max=vals.max()))
    pd.DataFrame(out).to_csv(r/'NULL_PORTFOLIO_COMPARISON.csv',index=False)
    choices=pd.read_csv(r/'CHOICES.csv.gz',parse_dates=['date']);choice=[]
    for (m,stage),g in choices[choices.date>='2021-01-01'].groupby(['market','stage']):
        a=g.pivot(index='date',columns='trial',values='pair')
        for t in a.columns:
            choice.append(dict(market=m,stage=stage,trial=t,signals=len(a),changes_vs_auth=int((a[t]!=a.AUTH).sum()),changes_vs_static=int((a[t]!=a.STATIC).sum())))
    pd.DataFrame(choice).to_csv(r/'CHOICE_STABILITY.csv',index=False)
    joint=[]
    for (contract,fee,period),g in f.groupby(['contract','fee','period']):
        p=g.pivot(index='trial',columns='market',values='cagr');n=p[p.index.str.startswith('NULL')]
        joint.append(dict(contract=contract,fee=fee,period=period,
           nulls_beating_authentic_both=int(((n.EU>=p.loc['AUTH','EU'])&(n.USA>=p.loc['AUTH','USA'])).sum()),
           nulls_beating_static_both=int(((n.EU>=p.loc['STATIC','EU'])&(n.USA>=p.loc['STATIC','USA'])).sum()),nulls=len(n)))
    pd.DataFrame(joint).to_csv(r/'JOINT_NULL_COUNTS.csv',index=False)
    # Descriptive paired calendar bootstrap; uncertainty from the history, not posterior probability.
    months=pd.period_range('2021-01','2024-12',freq='M')
    rng=np.random.default_rng(20261102);idx=((rng.integers(0,48,(4000,8))[:,:,None]+np.arange(6))%48).reshape(4000,48)
    cis=[]
    for market in ('EU','USA'):
        for contract in ('ALARM','FAST_LOCK3'):
            def seq(name):
                x=pd.read_csv(r/f'portfolios/{name}/{market}_{contract}_10_RETURNS.csv.gz',parse_dates=['date'])
                return x.groupby(x.date.dt.to_period('M')).log_return.sum().reindex(months).to_numpy()
            a=seq('AUTH')
            for b in ('STATIC','ORIGINAL','CUM_FIT'):
                d=a-seq(b);samples=d[idx].mean(1)*12;lo,hi=np.quantile(samples,[.025,.975])
                cis.append(dict(market=market,contract=contract,baseline=b,annual_log=12*d.mean(),lower=lo,upper=hi,
                    best_three_sum=np.sort(d)[-3:].sum(),total_log=d.sum(),months=48))
    pd.DataFrame(cis).to_csv(r/'PAIRED_UNCERTAINTY.csv',index=False)
    fit=[];maps=[];convergence=[]
    for p in (ROOT/'models').glob('*/*.json'):
        d=json.loads(p.read_text());m=d['model'];year=m['year'];t=d['trial']
        fit.append(dict(trial=t,year=year,penalty=m['penalty'],EU_groups=m['training_groups']['EU'],USA_groups=m['training_groups']['USA'],inner_fits=m['inner_fits']))
        for v in d['audit']['views']:
            assert pd.Timestamp(v['max_training_exit'])<pd.Timestamp(v['cutoff'])
            for z in v['mapping']:assert pd.Timestamp(z['donor_date'])<pd.Timestamp(v['cutoff'])
            maps.append(dict(trial=t,year=year,cutoff=v['cutoff'],rows=v['rows'],changed=v['changed'],unshared=v['unshared'],common_months=v['common_months'],training_key=v['training_key_sha256']))
        for loc,starts in [('outer',m['starts'])]+[(str(f['year']),f['optimization_starts']) for tr in m['cv'] for f in tr['folds']]:
            for z in starts:convergence.append(dict(trial=t,year=year,fit=loc,**z))
    pd.DataFrame(fit).to_csv(r/'PENALTY_SELECTION.csv',index=False)
    pd.DataFrame(maps).to_csv(r/'PERMUTATION_AUDIT.csv',index=False)
    pd.DataFrame(convergence).to_csv(r/'OPTIMIZATION_AUDIT.csv',index=False)
    au=pd.DataFrame(maps);nu=au[au.trial.str.startswith('NULL')]
    dump(r/'ANALYSIS_COMPLETE.json',dict(portfolios=480,annual_models=len(fit),audited_training_views=len(maps),
       optimizer_starts=len(convergence),nonconverged_starts=int((~pd.DataFrame(convergence).success).sum()),
       mean_context_fraction_moved=float((nu.changed/nu.rows).mean()),
       zero_move_views=int((nu.changed==0).sum()),
       note='Model with best converged training loss; failed starts preserved, no evaluation-based choice.'))
    print(pd.DataFrame(out).query("period=='ACTIVE2021_2024' and fee==.001 and metric=='cagr'").to_string(index=False))
    print('SENSITIVITIES')
    print(f[(f.period=='ACTIVE2021_2024')&(f.fee==.001)&~f.trial.str.startswith('NULL')][['trial','market','contract','cagr','maxdd']].round(6).to_string(index=False))
if __name__=='__main__':main()
