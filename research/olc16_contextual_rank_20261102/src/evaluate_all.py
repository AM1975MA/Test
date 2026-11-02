"""Evaluate identical mature outcomes for every frozen/learned ranking."""
import numpy as np,pandas as pd
from experiment import ROOT,MARKETS,NATIVE_VARIANTS,load_groups,readcsv,dump
from layer_metrics import opportunity_metrics,ranking_metrics,topk_weights

def periods(date,available):
    if pd.isna(available) or available>pd.Timestamp('2026-07-01'):return []
    out=[]
    if pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01'):
        out.append('ALL48_2021_2024')
        if available<pd.Timestamp('2025-01-01'):out.append('PRE2025')
    if date>=pd.Timestamp('2021-01-01'):out.append('ADAPTIVE_FULL')
    if date.year==2025:
        out.append('Y2025_ALL_OBSERVED')
        if available<pd.Timestamp('2026-01-01'):out.append('Y2025')
    if date.year==2026:out.append('Y2026_PARTIAL')
    return out

def main(market=None):
    selected=(market,) if market else MARKETS
    suffix='_'+market if market else ''
    groups,_,_=load_groups();groups=[g for g in groups if g['market'] in selected];scores={m:readcsv(ROOT/f'results/{m}_SCORES.csv.gz') for m in selected}
    rows=[];targets=[];choices=[];decisions=[]
    for g in groups:
        s=scores[g['market']].loc[g['positions']]
        for v in NATIVE_VARIANTS:
            for stage in ['CURRENT','SMOOTH','FUSION']:
                p=s[v+'_'+stage].to_numpy();assert np.isfinite(p).all()
                order=np.lexsort((g['tickers'],-p))[:2]
                if g['date']>=pd.Timestamp('2021-01-01'):
                    decisions.append(dict(market=g['market'],date=g['date'],variant=v,stage=stage,
                         pair='|'.join(sorted(g['tickers'][order])),top1=g['tickers'][order[0]],top2=g['tickers'][order[1]],
                         gap23=float(np.sort(p)[-2]-np.sort(p)[-3])))
                if not g['full']:continue
                ps=periods(g['date'],g['available'])
                if not ps:continue
                r=g['returns'];endpoints={'U42':g['u'],'0_21':r[:,0],'0_42':r[:,1],'0_63':r[:,2],
                  '21_42':(1+r[:,1])/(1+r[:,0])-1,'42_63':(1+r[:,2])/(1+r[:,1])-1}
                info=dict(market=g['market'],date=g['date'],available=g['available'],variant=v,stage=stage,n=len(p))
                for horizon,u in endpoints.items():
                    a=opportunity_metrics(u,p)
                    for per in ps:rows.append(dict(**info,period=per,horizon=horizon,**a))
                a=ranking_metrics(g['target'],p)
                for per in ps:targets.append(dict(**info,period=per,**a))
                if stage in ['CURRENT','FUSION']:
                    w=topk_weights(p)
                    for i in np.flatnonzero(w):choices.append(dict(**info,ticker=g['tickers'][i],weight=w[i],utility=g['u'][i],return21=r[i,0]))
    o=pd.DataFrame(rows);t=pd.DataFrame(targets);d=pd.DataFrame(decisions)
    o.to_csv(ROOT/f'results/OPPORTUNITY_MONTHS{suffix}.csv.gz',index=False,compression='gzip')
    t.to_csv(ROOT/f'results/TARGET_MONTHS{suffix}.csv.gz',index=False,compression='gzip')
    pd.DataFrame(choices).to_csv(ROOT/f'results/TOP2_DECISIONS{suffix}.csv.gz',index=False,compression='gzip')
    d.to_csv(ROOT/f'results/CHOICES{suffix}.csv.gz',index=False,compression='gzip')
    ks=['market','variant','stage','period']
    om=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']
    tm=['ndcg2','ndcg5','ic','selected_target','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']
    os=o.groupby(ks+['horizon']).agg(months=('date','nunique'),**{k:(k,'mean') for k in om}).reset_index()
    ts=t.groupby(ks).agg(months=('date','nunique'),**{k:(k,'mean') for k in tm}).reset_index()
    os.to_csv(ROOT/f'results/OPPORTUNITY_SUMMARY{suffix}.csv',index=False);ts.to_csv(ROOT/f'results/TARGET_SUMMARY{suffix}.csv',index=False)
    contrasts=[]
    for stage in ['CURRENT','FUSION']:
        for m in selected:
            sub=d[(d.market==m)&(d.stage==stage)].pivot(index='date',columns='variant',values='pair')
            for a,b in [('PAIR_CONTEXT','PAIR_STATIC'),('TOP2_CONTEXT','TOP2_STATIC'),('TOP2_STATIC','PAIR_STATIC'),('PAIR_CONTEXT','CUM_FIT'),('TOP2_CONTEXT','CUM_FIT'),('PAIR_LAG','PAIR_CONTEXT'),('TOP2_LAG','TOP2_CONTEXT')]:
                contrasts.append(dict(market=m,stage=stage,candidate=a,baseline=b,signals=len(sub),changed=int((sub[a]!=sub[b]).sum())))
    pd.DataFrame(contrasts).to_csv(ROOT/f'results/CHOICE_CONTRASTS{suffix}.csv',index=False)
    dump(ROOT/f'results/EVALUATION_COMPLETE{suffix}.json',dict(native_rows=len(o),target_rows=len(t),decision_rows=len(d),variants=len(NATIVE_VARIANTS)))
    print('PRIMARY CURRENT U EXCESS log percentage points:')
    print(os[(os.period=='PRE2025')&(os.stage=='CURRENT')&(os.horizon=='U42')].pivot(index='variant',columns='market',values='top2_excess').mul(100).to_string())
    print('CHOICES\n',pd.DataFrame(contrasts).to_string(index=False))
if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--market',choices=['EU','USA']);main(a.parse_args().market)
