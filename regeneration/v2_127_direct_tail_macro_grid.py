#!/usr/bin/env python3
"""ETF Trader V2 direct Tail+Macro coefficient ablation.
Fixed XGB 127-leaf OOS scores. Original 500 baskets. No new alpha fits, risk off.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'regeneration'))
import v2_large_leaf_sweep as source

SHAFILE='36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e'
TAIL_WEIGHTS=[0,.10,.20,.30,.40,.50,.60]
MACRO_BONUSES=[0,.05,.10,.15,.20,.30]
ALLOCATIONS={'top2_equal':[.5,.5],'top3_equal':[1/3,1/3,1/3],'top3_503020':[.5,.3,.2]}
def metrics(e,t):
    n=e.shape[1]
    r=np.diff(np.log(np.concatenate([np.ones((len(e),1)),e],axis=1)),axis=1)
    gr=np.expm1(r.sum(axis=1)*252/n)
    peak=np.maximum.accumulate(np.concatenate([np.ones((len(e),1)),e],axis=1),axis=1)[:,1:]
    dd=(e/peak-1).min(axis=1)
    aggregate=e.mean(axis=0)
    add=aggregate/np.maximum.accumulate(np.r_[1.,aggregate])[1:]-1.
    return {'mean_cagr':float(gr.mean()),'median_cagr':float(np.median(gr)),
            'mean_maxdd':float(dd.mean()),'aggregate_cagr':float(aggregate[-1]**(252/n)-1),
            'aggregate_maxdd':float(add.min()),
            'mean_annual_turnover':float(t.sum(axis=1).mean()*252/n)}

def simulate(score,kind,basket_indices,dates,O,signals,rebalance,start_i,end_i):
    """Sparse exactly-self-financing multi-basket open-to-open portfolio with fees."""
    B=basket_indices.shape[0];K=2 if kind in ('legacy','top2_equal') else 3
    local=score[:,basket_indices]
    order=np.argsort(-np.where(np.isfinite(local),local,-np.inf),axis=2,kind='stable')
    indices=np.take_along_axis(np.broadcast_to(basket_indices[None,:,:],local.shape),order,axis=2)[:,:,:K]
    values=np.take_along_axis(local,order,axis=2)[:,:,:K]
    if not np.isfinite(values).all():raise RuntimeError('Ineligible predicted ETF')
    if kind=='legacy':
        first=np.where(values[:,:,0]-values[:,:,1]>=.12,1.,.75)
        weights=np.stack([first,1-first],axis=2)
    else:
        weights=np.broadcast_to(np.array(ALLOCATIONS[kind],float),(len(signals),B,K))
    rows=np.arange(B)
    idx=np.zeros((B,K),dtype=np.int32);units=np.zeros((B,K),dtype=float);cash=np.ones(B)
    prev_idx=np.full((B,K),-1,dtype=np.int32);prev_weights=np.zeros((B,K))
    steps=end_i-start_i
    eq=np.empty((steps,B));tr=np.empty((steps,B))
    for j,i in enumerate(range(start_i,end_i)):
        p=O[i]; m=units*p[idx]; val=cash+m.sum(axis=1)
        t=np.zeros(B)
        if i in rebalance:
            n=rebalance[i]
            wanted_idx=indices[n]; wanted_w=weights[n]
            compat=(wanted_idx[:,:,None]==prev_idx[:,None,:])
            old_w_in_new=(compat*prev_weights[:,None,:]).sum(axis=2)
            new_w_in_old=(compat*wanted_w[:,:,None]).sum(axis=1)
            changed=(np.abs(wanted_w-old_w_in_new).sum(axis=1)
                     +np.abs(prev_weights-new_w_in_old).sum(axis=1))>1e-12
            if changed.any():
                match=(wanted_idx[:,:,None]==idx[:,None,:])
                old_by_new=(match*m[:,None,:]).sum(axis=2)
                old_left=(m*(~match.any(axis=1))).sum(axis=1)
                after=val.copy()
                for _ in range(10):
                    traded=np.abs(wanted_w*after[:,None]-old_by_new).sum(axis=1)+old_left
                    after=np.where(changed,val-.001*traded,val)
                t=np.where(changed,traded/val,0)
                idx=np.where(changed[:,None],wanted_idx,idx)
                units=np.where(changed[:,None],after[:,None]*wanted_w/p[wanted_idx],units)
                cash=np.where(changed,after*(1-wanted_w.sum(axis=1)),cash)
            prev_idx=wanted_idx.copy();prev_weights=wanted_w.copy()
        eq[j]=cash+(units*O[i+1,idx]).sum(axis=1)
        tr[j]=t
    return eq.T,tr.T

def monthly(e,dates,start_i,end_i):
    dt=dates[start_i+1:end_i+1]
    months=dt.to_period('M')
    if months[-1]==pd.Period('2026-07',freq='M'):
        months=np.array([min(x,pd.Period('2026-06',freq='M')) for x in months])
    a=[];label=[]
    for m in sorted(set(months)):
        if m<pd.Period('2018-02',freq='M'):continue
        ix=np.flatnonzero(months==m)
        start=np.ones(len(e)) if ix[0]==0 else e[:,ix[0]-1]
        end=e[:,ix[-1]]
        a.append(float(np.log(end/start).mean()));label.append(str(m))
    return label,np.array(a)

def bootstrap(comp,base,month_labels,reps=3000):
    n=len(base);d=np.asarray(comp)-np.asarray(base)
    rng=np.random.default_rng(20261020)
    block=6
    starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
    ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    means=d[ix].mean(axis=1)*12
    return {'delta_log_annual':float(d.mean()*12),
            'ci95_low':float(np.quantile(means,.025)),
            'ci95_high':float(np.quantile(means,.975)),
            'dev_2018_2023_annual':float(d[np.array([int(x[:4])<=2023 for x in month_labels])].mean()*12),
            'retrospective_2024_2026_annual':float(d[np.array([int(x[:4])>=2024 for x in month_labels])].mean()*12)}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument('--components',default='runs/v2_127_direct_components/FROZEN_COMPONENTS.csv')
    pa.add_argument('--audit',default='runs/v2_127_direct_components/COMPONENT_AUDIT.json')
    pa.add_argument('--raw',default='etf_trader_raw')
    pa.add_argument('--baskets',default='regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv')
    pa.add_argument('--out',default='runs/v2_127_tail_macro_direct')
    a=pa.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()!=SHAFILE:raise RuntimeError('Basket source mismatch')
    audited=json.loads(Path(a.audit).read_text())
    if audited['status']!='BASELINE_SCORE_PARITY_PASS':raise RuntimeError('Missing original score parity')
    z=pd.read_csv(a.components,parse_dates=['signal_date'],float_precision='round_trip')
    if z.duplicated(['signal_date','ticker']).any():raise RuntimeError('duplicated score rows')
    mats,cats,_=source.load_ticker_csv_folder(a.raw)
    mats={k:v.loc[v.index>=pd.Timestamp(2011,1,1)] for k,v in mats.items()}
    M=source.load_baskets(a.baskets,cats)
    cols=list(mats['Open'].columns);lut={x:i for i,x in enumerate(cols)}
    members=np.array([[lut[t] for t in sorted(b)] for b in M],dtype=np.int32)
    dates=mats['Open'].index;O=mats['Open'].to_numpy(float)
    signals=pd.DatetimeIndex(sorted(z.signal_date.unique()))
    rebalance={int(i):n for n,i in enumerate(dates.searchsorted(signals,side='right')) if i<len(dates)}
    start_i=int(dates.searchsorted(pd.Timestamp('2017-02-01')))
    end_i=int(dates.searchsorted(pd.Timestamp('2026-07-01'),side='right')-1)
    if len(signals)!=102 or len(M)!=500:raise RuntimeError('wrong OOS signal/basket count')
    def wide(x):
        return z.pivot(index='signal_date',columns='ticker',values=x).reindex(index=signals,columns=cols).to_numpy(float)
    R=wide('raw_rank');T=wide('tail_rank');G=wide('macro_fired')
    old=wide('score')
    if not np.isfinite(old[:,members]).all():raise RuntimeError('missing old scores in canonical basket')
    baseline=simulate(old,'legacy',members,dates,O,signals,rebalance,start_i,end_i)
    bmetr=metrics(*baseline)
    if max(abs(bmetr['mean_cagr']-.09437),abs(bmetr['mean_maxdd']+.52445))>1e-4:
        raise RuntimeError('Official portfolio baseline not replicated: '+str(bmetr))
    original_months,baseline_ml=monthly(baseline[0],dates,start_i,end_i)
    results=[{'name':'OFFICIAL_LEGACY','tail_weight':.30,'macro_bonus':.15,'alloc':'legacy',**bmetr}]
    monthly_rows=[{'name':'OFFICIAL_LEGACY','month':month,'mean_log':float(v)} for month,v in zip(original_months,baseline_ml)]
    for tw in TAIL_WEIGHTS:
        for mb in MACRO_BONUSES:
            base=(1-tw)*R+tw*T+mb*G
            ranked=pd.DataFrame(base,index=signals,columns=cols).rank(axis=1,pct=True).to_numpy(float)
            if abs(tw-.3)<1e-12 and abs(mb-.15)<1e-12:
                delta=np.nanmax(np.abs(ranked-old))
                if delta>1e-12:raise RuntimeError('Legacy score no longer matches original, error '+str(delta))
            for kind in ALLOCATIONS:
                name=f'tail{tw:.2f}_macro{mb:.2f}_{kind}'
                e,tr=simulate(ranked,kind,members,dates,O,signals,rebalance,start_i,end_i)
                m=metrics(e,tr)
                months,values=monthly(e,dates,start_i,end_i)
                if months!=original_months:raise RuntimeError('calendar mismatch')
                comp=bootstrap(values,baseline_ml,months)
                results.append({'name':name,'tail_weight':tw,'macro_bonus':mb,'alloc':kind,**m,**comp})
                monthly_rows.extend({'name':name,'month':month,'mean_log':float(v)} for month,v in zip(months,values))
                print('GRID_DONE',name,'cagr',round(m['mean_cagr'],5),'maxdd',round(m['mean_maxdd'],5),flush=True)
    res=pd.DataFrame(results)
    res.to_csv(out/'DIRECT_TAIL_MACRO_GRID.csv',index=False)
    pd.DataFrame(monthly_rows).to_csv(out/'PAIRED_MONTHLY_LOG_RETURNS.csv',index=False)
    score=res[res.name!='OFFICIAL_LEGACY']
    stability=score.sort_values('dev_2018_2023_annual',ascending=False)
    # Diagnostic only: this is not a prospective untouched period.
    top=stability.head(15)[['name','mean_cagr','mean_maxdd','aggregate_cagr','aggregate_maxdd','delta_log_annual','ci95_low','ci95_high','dev_2018_2023_annual','retrospective_2024_2026_annual']]
    selection={'status':'COMPLETE','score_parity_audit':audited,'n_grid':len(score),
       'periodic_outcomes_are_retrospective':True,
       'warning':'All 2018-2026 results are historically inspected; re-use is exploratory, no prospective validation.',
       'legacy_metrics':bmetr,'development_ranked_top15':top.to_dict('records'),
       'whole_sample_best_mean_cagr':score.sort_values('mean_cagr',ascending=False).head(15).to_dict('records'),
       'whole_sample_best_mean_maxdd':score.sort_values('mean_maxdd',ascending=False).head(10).to_dict('records')}
    (out/'RESULT.json').write_text(json.dumps(selection,indent=2,default=str))
    print('DIRECT_RETUNE_SUMMARY',json.dumps({
       'n_grid':len(score),'original':bmetr,
       'development_best':top.head(8).to_dict('records'),
       'mean_cagr_best':score.nlargest(5,'mean_cagr')[['name','mean_cagr','mean_maxdd','aggregate_cagr','aggregate_maxdd']].to_dict('records'),
       'mean_maxdd_best':score.nlargest(5,'mean_maxdd')[['name','mean_cagr','mean_maxdd']].to_dict('records')},default=str),flush=True)

if __name__=='__main__':main()
