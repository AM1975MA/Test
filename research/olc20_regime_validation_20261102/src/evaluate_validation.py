"""Common-outcome diagnostics for every registered authentic/null procedure."""
import json
import numpy as np,pandas as pd
from scipy.stats import rankdata
from paths import ROOT,P16
from experiment import load_groups,readcsv,dump
from evaluate_all import periods
from layer_metrics import opportunity_metrics,ranking_metrics

def direct_selected(y,p):
    """Independent expected mean under uniform tie resolution at the second score."""
    order=np.argsort(-p);edge=p[order[1]]
    hi=np.flatnonzero(p>edge);tie=np.flatnonzero(p==edge)
    return float((y[hi].sum()+(2-len(hi))*y[tie].mean())/2)

def main():
    gs,frames,controls=load_groups();summaries=[];targets=[];choices=[];allmonths=[];checks=0;maxerr=0.
    names=sorted(p.parent.name for p in (ROOT/'results/trials').glob('*/COMPLETE.json'))+['ORIGINAL','CUM_FIT']
    for trial in names:
        monthly=[];trg=[]
        for market in ('EU','USA'):
            if trial in ('ORIGINAL','CUM_FIT'):
                src=readcsv(P16/f'results/{market}_SCORES.csv.gz')
                out=src[['signal_date','ticker','RETURN']].copy()
                for stage in ('CURRENT','FUSION'):out[stage]=src[trial+'_'+stage]
            else:out=readcsv(ROOT/f'results/trials/{trial}/{market}_SCORES.csv.gz')
            for g in [x for x in gs if x['market']==market]:
                for stage in ('CURRENT','FUSION'):
                    p=out.loc[g['positions'],stage].to_numpy();assert np.isfinite(p).all()
                    order=np.lexsort((g['tickers'],-p))[:2]
                    choices.append(dict(trial=trial,market=market,date=g['date'],stage=stage,
                         pair='|'.join(sorted(g['tickers'][order])),gap23=float(np.sort(p)[-2]-np.sort(p)[-3])))
                    if not g['full']:continue
                    ps=periods(g['date'],g['available'])
                    if not ps:continue
                    r=g['returns'];ys={'U42':g['u'],'0_21':r[:,0],'0_42':r[:,1],'0_63':r[:,2],
                        '21_42':(1+r[:,1])/(1+r[:,0])-1,'42_63':(1+r[:,2])/(1+r[:,1])-1}
                    base=dict(trial=trial,market=market,date=g['date'],available=g['available'],stage=stage)
                    for horizon,y in ys.items():
                        a=opportunity_metrics(y,p);direct=direct_selected(y,p)
                        err=abs(direct-a['top2_return']);assert err<1e-12;maxerr=max(maxerr,err);checks+=1
                        for per in ps:monthly.append(dict(**base,period=per,horizon=horizon,**a))
                    a=ranking_metrics(g['target'],p)
                    for per in ps:trg.append(dict(**base,period=per,**a))
        f=pd.DataFrame(monthly);tf=pd.DataFrame(trg);allmonths.append(f)
        print('NATIVE_DONE',trial,flush=True)
        keys=['trial','market','stage','period','horizon']
        values=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']
        summaries.append(f.groupby(keys).agg(months=('date','nunique'),**{c:(c,'mean') for c in values}).reset_index())
        tvalues=['ndcg2','ndcg5','ic','selected_target','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']
        targets.append(tf.groupby(keys[:-1]).agg(months=('date','nunique'),**{c:(c,'mean') for c in tvalues}).reset_index())
    summary=pd.concat(summaries);summary.to_csv(ROOT/'results/NATIVE_SUMMARY.csv',index=False)
    pd.concat(targets).to_csv(ROOT/'results/TARGET_SUMMARY.csv',index=False)
    pd.concat(allmonths).to_csv(ROOT/'results/NATIVE_MONTHS.csv.gz',index=False)
    pd.DataFrame(choices).to_csv(ROOT/'results/CHOICES.csv.gz',index=False)
    contrasts=[]
    for keys,g in summary.groupby(['market','stage','period','horizon']):
        authentic=g[g.trial=='AUTH'].iloc[0];static=g[g.trial=='STATIC'].iloc[0]
        null=g[g.trial.str.startswith('NULL')]
        for metric in ('top2_excess','bottom_quintile_fraction'):
            vals=null[metric].to_numpy();av=authentic[metric];sv=static[metric]
            better=(vals>=av) if metric=='top2_excess' else (vals<=av)
            contrasts.append(dict(zip(['market','stage','period','horizon'],keys),metric=metric,
              authentic=av,static=sv,authentic_minus_static=av-sv,nulls=len(vals),at_least_as_good=int(better.sum()),
              null_min=float(vals.min()),null_q05=float(np.quantile(vals,.05)),null_median=float(np.median(vals)),
              null_q95=float(np.quantile(vals,.95)),null_max=float(vals.max()),
              qualification='Descriptive structured training negative controls; not exact p-values or success probabilities.'))
    pd.DataFrame(contrasts).to_csv(ROOT/'results/NULL_NATIVE_COMPARISON.csv',index=False)
    dump(ROOT/'results/NATIVE_VERIFICATION.json',dict(procedures=len(names),independent_selected_payoffs=checks,maximum_error=maxerr))
    print('PRIMARY FUSION U42 (%log points)')
    print(summary[(summary.period=='PRE2025')&(summary.stage=='FUSION')&(summary.horizon=='U42')&~summary.trial.str.startswith('NULL')].pivot(index='trial',columns='market',values='top2_excess').mul(100).round(6).to_string())
    co=pd.DataFrame(contrasts);print(co[(co.period=='PRE2025')&(co.horizon=='U42')&(co.metric=='top2_excess')].to_string(index=False))
if __name__=='__main__':main()
