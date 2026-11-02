"""Fresh refits, loaded-score identity, accounting replay and causal-prefix checks.
Verification refits do not count as new trial configurations.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(k,'1')
import argparse,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np,pandas as pd
from paths import ROOT,P16
from experiment import load_groups,eligible,readcsv,dump
from context_model import fit_model
from context_views import transformed
from score_validation import build_scores
from nested_validation import fit_annual
from portfolio_validation import prepare_state
from combined_engine import simulate
from run_trials import TRIALS,source_hash

def models_and_scores(trial):
    g,f,c=load_groups();models={};maxerr=0.;spec=TRIALS[trial]
    for y in range(2021,2027):
        saved=json.loads((ROOT/f'models/{trial}/{y}.json').read_text())
        assert saved['source_hash']==source_hash()
        model=saved['model'];tr=eligible(g,pd.Timestamp(y,1,1))
        view,au=transformed(tr,seed=spec.get('seed'),omit=spec.get('omit'))
        recreated=fit_model(view,model['contextual'],'top2',model['penalty'])
        e=float(np.max(abs(np.asarray(recreated['theta'])-np.asarray(model['theta']))))
        assert e<1e-12,(trial,y,e);maxerr=max(maxerr,e);models[y]=model
        for record in saved['audit']['views']:
            cutoff=pd.Timestamp(record['cutoff'])
            admissible={(x['market'],str(x['date'])) for x in eligible(g,cutoff)}
            for z in record['mapping']:
                assert (z['market'],z['date']) in admissible
                assert (z['market'],z['donor_date']) in admissible
    out,trace=build_scores(g,f,c,models,omit=spec.get('omit'))
    for market,df in out.items():
        old=readcsv(ROOT/f'results/trials/{trial}/{market}_SCORES.csv.gz')
        for col in ('CURRENT','SMOOTH','FUSION','RETURN'):
            np.testing.assert_array_equal(df[col].to_numpy(),old[col].to_numpy())
    return dict(trial=trial,refits=6,maximum_theta_error=maxerr,loaded_scores_exact=True)

def portfolio_replay(trial,market):
    q,ev,_=prepare_state(market,trial);keys=[]
    for contract in ('ALARM','FAST_LOCK3'):
        for fee in (.001,.003):
            key=f'{market}_{contract}_{round(fee*10000)}'
            old=np.load(ROOT/f'results/portfolios/{trial}/{key}.npz',allow_pickle=False)
            new=simulate(q,ev,contract=contract,fee=fee,friction=.001)
            for name in new:np.testing.assert_array_equal(new[name],old[name])
            keys.append(key)
    return dict(trial=trial,market=market,paths_exact=len(keys))

def prefixes():
    g,f,c=load_groups();rows=[]
    for trial in ('AUTH','NULL20025'):
        spec=TRIALS[trial]
        for year in (2022,2025):
            cutoff=pd.Timestamp(year,1,1);changed=[]
            for row in g:
                z=dict(row)
                if pd.isna(row['available']) or row['available']>=cutoff:
                    z['u']=np.nan_to_num(row['u'])*300+99
                if row['date']>=cutoff:z['x']=np.nan_to_num(row['x'])*-5+9
                changed.append(z)
            model,audit=fit_annual(changed,year,**spec)
            original=json.loads((ROOT/f'models/{trial}/{year}.json').read_text())['model']
            np.testing.assert_array_equal(model['theta'],original['theta'])
            assert model['penalty']==original['penalty']
            rows.append(dict(trial=trial,year=year,training_prefix_unchanged=True))
    for market in ('EU','USA'):
        q,ev,_=prepare_state(market,'AUTH');k=1100
        for contract in ('ALARM','FAST_LOCK3'):
            old=simulate(q,ev,contract=contract);pert={n:v.copy() for n,v in q.items()}
            for n in ('O','C','L'):pert[n][k:]*=1.4
            pert['gap'][k:]=-.5;pert['ud1'][k:]=1.;pert['uneg'][k:]=1.
            new=simulate(pert,ev,contract=contract)
            for name in ('primary_units','targets','risk_trace'):
                np.testing.assert_array_equal(old[name][:k-1],new[name][:k-1])
            np.testing.assert_array_equal(old['nav'][:k-1],new['nav'][:k-1])
            rows.append(dict(market=market,contract=contract,account_prefix_unchanged=True))
    dump(ROOT/'results/FUTURE_PREFIX_VERIFICATION.json',rows)
    return rows

def main(workers):
    results=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs=[pool.submit(models_and_scores,n) for n in TRIALS]
        for j in as_completed(jobs):
            z=j.result();results.append(z);print('REFIT',z['trial'],z['maximum_theta_error'],flush=True)
    dump(ROOT/'results/MODEL_RELOAD_VERIFICATION.json',results)
    names=list(TRIALS)+['CONTEXT_LAG','ORIGINAL','CUM_FIT'];accounts=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs=[pool.submit(portfolio_replay,n,m) for n in names for m in ('EU','USA')]
        for j in as_completed(jobs):
            z=j.result();accounts.append(z);print('REPLAY',z['trial'],z['market'],flush=True)
    dump(ROOT/'results/ACCOUNT_RELOAD_VERIFICATION.json',accounts)
    future=prefixes()
    dump(ROOT/'results/FINAL_VERIFICATION.json',dict(model_refits=sum(x['refits'] for x in results),
       maximum_parameter_error=max(x['maximum_theta_error'] for x in results),
       reloaded_score_procedures=len(results),paths_replayed=sum(x['paths_exact'] for x in accounts),
       future_checks=len(future),external_independent_review=False))
    print('ALL_VERIFIED',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);a=p.parse_args();main(a.workers)
