"""Independent arithmetic checks, serialized-model refits and causal-prefix tests."""
from __future__ import annotations
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import json,argparse
import numpy as np,pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import ndcg_score
from experiment import *
from context_model import fit_model,predict_weights
from revalue_memory import revalue
from core import benchmark_context

def check_accounts():
    metrics=readcsv(ROOT/'results/SCORECARD.csv');records=[];n=0
    for m in MARKETS:
        q=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));dates=pd.DatetimeIndex(q['dates'])[1:]
        for cfg,rows in metrics[metrics.market==m].groupby('config'):
            p=np.load(ROOT/f'results/paths/{cfg}.npz');nav=p['nav'][:-1]
            cap=np.einsum('ij,ij->i',p['primary_units'][:-1]+p['defensive_units'][:-1],q['O'][1:])+p['free_cash'][:-1]
            ce=float(np.max(abs(nav-cap)));assert ce<1e-10
            rets=nav/np.r_[1.,nav[:-1]];maxerr=0.
            for row in rows.itertuples():
                mask=(dates>=pd.Timestamp(row.first_valuation))&(dates<=pd.Timestamp(row.last_valuation));gross=rets[mask]
                eq=np.cumprod(gross);cummax=np.maximum.accumulate(np.r_[1.,eq])[1:]
                expected=[eq[-1]**(252/len(gross))-1,float((eq/cummax-1).min()),eq[-1]-1]
                err=max(abs(np.array(expected)-np.array([row.cagr,row.maxdd,row.period_return])))
                assert err<1e-10,(cfg,row.period,err);maxerr=max(maxerr,float(err));n+=3
            records.append(dict(config=cfg,capital_intervals=len(nav),capital_error=ce,metric_error=maxerr))
    pd.DataFrame(records).to_csv(ROOT/'results/INDEPENDENT_ACCOUNTS.csv',index=False)
    dump(ROOT/'results/ACCOUNT_CHECK.json',dict(paths=len(records),intervals=sum(r['capital_intervals'] for r in records),metrics=n,
        max_capital_error=max(r['capital_error'] for r in records),max_metric_error=max(r['metric_error'] for r in records)))
    print('ACCOUNTS',len(records),n,flush=True)

def native(m):
    groups,_,_=load_groups();sc=readcsv(ROOT/f'results/{m}_SCORES.csv.gz')
    o=readcsv(ROOT/f'results/OPPORTUNITY_MONTHS_{m}.csv.gz').drop(columns='period').drop_duplicates()
    t=readcsv(ROOT/f'results/TARGET_MONTHS_{m}.csv.gz').drop(columns='period').drop_duplicates()
    o=o.set_index(['date','variant','stage','horizon']);t=t.set_index(['date','variant','stage'])
    assert not o.index.duplicated().any() and not t.index.duplicated().any()
    checked=0;nd=0;maxerr=0.;maxnd=0.
    for g in groups:
        if g['market']!=m or g['date'] not in o.index.get_level_values('date'):continue
        r=g['returns'];logs=np.log1p(r)
        # Independent expression of discounted block utility.
        q=np.sqrt(.5);u=(logs[:,0]+q*(logs[:,1]-logs[:,0])+.5*(logs[:,2]-logs[:,1]))/(1+q+.5)
        end={'U42':u,'0_21':r[:,0],'0_42':r[:,1],'0_63':r[:,2],
             '21_42':np.expm1(logs[:,1]-logs[:,0]),'42_63':np.expm1(logs[:,2]-logs[:,1])}
        for v in NATIVE_VARIANTS:
            for stage in ['CURRENT','SMOOTH','FUSION']:
                s=sc.loc[g['positions'],v+'_'+stage].to_numpy();threshold=np.partition(s,-2)[-2]
                w=np.zeros(len(s));w[s>threshold]=.5;w[s==threshold]=(1-w.sum())/np.count_nonzero(s==threshold)
                for horizon,a in end.items():
                    selected=float(np.sum(w*a));ranks=rankdata(a)/len(a)
                    expected=np.array([selected,selected-a.mean(),np.partition(a,-2)[-2:].mean()-selected,
                         np.sum(w*(a<0)),np.sum(w*(ranks<=.2)),np.sum(w*(rankdata(a)>len(a)-5))])
                    old=o.loc[(g['date'],v,stage,horizon),['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']].to_numpy(float)
                    e=float(np.max(abs(expected-old)));assert e<1e-12;maxerr=max(maxerr,e);checked+=len(expected)
                expected=float(ndcg_score([g['target']],[s],k=2));old=float(t.loc[(g['date'],v,stage),'ndcg2'])
                e=abs(expected-old);assert e<1e-12;maxnd=max(maxnd,e);nd+=1
    dump(ROOT/f'results/NATIVE_CHECK_{m}.json',dict(market=m,arithmetic_values=checked,ndcg_values=nd,max_error=maxerr,max_ndcg_error=maxnd))
    print('NATIVE_CHECK',m,checked,nd,flush=True)

def refit(year):
    groups,_,_=load_groups();tr=eligible(groups,pd.Timestamp(year,1,1));records=[]
    for path in sorted((ROOT/'models').glob(f'{year}_*.json')):
        old=json.loads(path.read_text());training=shuffled_context_groups(tr,old['null_seed']) if 'null_seed' in old else tr
        fresh=fit_model(training,old['contextual'],old['kind'],old['penalty'])
        error=float(np.max(abs(np.array(old['theta'])-np.array(fresh['theta']))))
        assert error<1e-9,(path,error)
        pred_error=max(float(np.max(abs(predict_weights(old,g['x'])-predict_weights(fresh,g['x'])))) for g in groups if g['date'].year==year)
        assert pred_error<1e-10
        records.append(dict(model=path.name,parameter_error=error,prediction_error=pred_error))
    pd.DataFrame(records).to_csv(ROOT/f'results/REFIT_CHECK_{year}.csv',index=False);print('REFIT',year,len(records),flush=True)

def causal():
    groups,_,_=load_groups();rows=[];cutoff=pd.Timestamp('2023-01-01')
    changed=[]
    for g in groups:
        h=dict(g)
        if not g['full'] or g['available']>=cutoff:
            h['u']=np.nan_to_num(g['u'])*-10+100
        if g['date']>=cutoff:h['x']=np.array([100.,-100.,0.])
        changed.append(h)
    for kind in ['pair','top2']:
        a=fit_year(groups,2023,kind,True);b=fit_year(changed,2023,kind,True)
        np.testing.assert_array_equal(a['theta'],b['theta']);assert a['penalty']==b['penalty']
        rows.append(dict(test='future_outcome_and_context_refit_'+kind,pass_exact=True))
    model=json.loads((ROOT/'models/2023_TOP2_CONTEXT.json').read_text())
    for m in MARKETS:
        gs=[g for g in groups if g['market']==m];bs=[predict_weights(model,g['x']) for g in gs]
        a=revalue(gs,bs);future=pd.Timestamp('2024-01-01')
        alt=[dict(g,z=1-g['z']) if g['date']>=future else g for g in gs]
        b=revalue(alt,bs)
        for i,g in enumerate(gs):
            if g['date']<future:np.testing.assert_array_equal(a[i],b[i])
        rows.append(dict(test='future_forecast_memory_'+m,pass_exact=True))
        close=readcsv(ROOT/f'inputs/{m}_BENCHMARK_CLOSE.csv').set_index('date')['close']
        a=benchmark_context(close);changed=close.copy();changed.loc[changed.index>=future]*=np.linspace(.5,2,(changed.index>=future).sum())
        b=benchmark_context(changed);pd.testing.assert_frame_equal(a.loc[a.index<future],b.loc[b.index<future])
        rows.append(dict(test='future_benchmark_context_'+m,pass_exact=True))
    dump(ROOT/'results/CAUSAL_CHECKS.json',rows);print('CAUSAL',len(rows),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--accounts',action='store_true');ap.add_argument('--native',choices=MARKETS);ap.add_argument('--refit',type=int);ap.add_argument('--causal',action='store_true');a=ap.parse_args()
    if a.accounts:check_accounts()
    if a.native:native(a.native)
    if a.refit:refit(a.refit)
    if a.causal:causal()
