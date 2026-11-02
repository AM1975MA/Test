"""Fit registered models with annual checkpoints and construct label-blind scores."""
from __future__ import annotations
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import argparse,json,time
import numpy as np,pandas as pd
from experiment import *
from context_model import fit_model,predict_weights
from parent_chrono import anchor_scale
from core import compose_current

def fit_all(groups,years=None):
    # Annual batches keep work within the runtime call ceiling. No fit definition changes.
    old=ROOT/'results/ANNUAL_MODELS.json'
    models={int(k):v for k,v in json.loads(old.read_text()).items()} if years and old.exists() else {}
    audit_path=ROOT/'results/FIT_AUDIT.csv'
    audit=pd.read_csv(audit_path).to_dict('records') if years and audit_path.exists() else []
    t=time.time()
    for year in years if years else range(2021,2027):
        audit=[r for r in audit if r['year']!=year]
        models[year]={}
        for kind in ['pair','top2']:
            for contextual in [False,True]:
                name=kind.upper()+('_CONTEXT' if contextual else '_STATIC')
                p=fit_year(groups,year,kind,contextual)
                models[year][name]=p;dump(ROOT/f'models/{year}_{name}.json',p)
                audit.append(dict(year=year,variant=name,penalty=p.get('penalty'),
                                  inner_fits=p['inner_fits'],max_training_exit=p.get('max_training_exit'),
                                  EU=p['training_groups']['EU'],USA=p['training_groups']['USA'],loss=p.get('loss')))
                print('MODEL',year,name,'CV',p['inner_fits'],'elapsed',round(time.time()-t,1),flush=True)
            for seed in [1601,1602]:
                name=f'{kind.upper()}_NULL{seed}';main=models[year][kind.upper()+'_CONTEXT']
                tr=eligible(groups,pd.Timestamp(year,1,1));sh=shuffled_context_groups(tr,seed)
                p=fit_model(sh,True,kind,main.get('penalty',.1))
                p.update(year=year,cutoff=str(pd.Timestamp(year,1,1)),null_seed=seed,fallback=False,
                         max_training_exit=str(max(g['available'] for g in tr)),inner_fits=0)
                models[year][name]=p;dump(ROOT/f'models/{year}_{name}.json',p)
        dump(ROOT/'results/ANNUAL_MODELS.json',models)
        pd.DataFrame(audit).to_csv(ROOT/'results/FIT_AUDIT.csv',index=False)
        dump(ROOT/'results/TRAIN_PROGRESS.json',dict(last_complete_year=year,saved_models=sum(len(v) for v in models.values()),seconds=time.time()-t))
    if set(models)!=set(range(2021,2027)):return models
    dump(ROOT/'results/TRAINING_COMPLETE.json',dict(main_models=len(audit),null_models=24,
           inner_fits=sum(r['inner_fits'] for r in audit),base_ETF_refits=0,
           optimization_starts=3*(len(audit)+24+sum(r['inner_fits'] for r in audit))))
    return models

def build_scores(groups,frames,controls,models):
    traces=[];scores={}
    for m in MARKETS:
        f=frames[m];c=controls[m];out=c[['signal_date','ticker','RETURN']].copy()
        for v in CONTROLS:
            for stage in ['CURRENT','SMOOTH','FUSION']:
                out[v+'_'+stage]=c[v+'_'+('MAPPED' if stage=='CURRENT' else stage)]
        for v in BASE_NATIVE[len(CONTROLS):]:out[v+'_CURRENT']=np.nan
        for g in groups:
            if g['market']!=m:continue
            for v in BASE_NATIVE[len(CONTROLS):]:
                key=v.replace('_LAG','_CONTEXT');model=models.get(g['date'].year,{}).get(key)
                x=g['xlag'] if v.endswith('_LAG') else g['x']
                beta=predict_weights(model,x) if model else PRIOR.copy()
                raw=g['z']@beta
                current=anchor_scale(raw,g['anchor']) if model else g['anchor'].copy()
                out.loc[g['positions'],v+'_CURRENT']=current
                traces.append(dict(market=m,date=g['date'],variant=v,adapted=model is not None,
                         beta21=float(beta[0]),beta42=float(beta[1]),beta63=float(beta[2]),
                         model_year=g['date'].year if model else None,
                         penalty=model.get('penalty') if model else None,
                         context_missing=int(np.isnan(x).sum()),score_gap23=float(np.sort(current)[-2]-np.sort(current)[-3])))
        dates=pd.DatetimeIndex(sorted(f.signal_date.unique()));ticks=sorted(f.ticker.unique())
        di=dates.get_indexer(f.signal_date);ti=pd.Index(ticks).get_indexer(f.ticker)
        def mat(col):return out.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=ticks).to_numpy(float)
        for v in BASE_NATIVE[len(CONTROLS):]:
            sm,fu=compose_current(mat('RETURN'),mat(v+'_CURRENT'));out[v+'_SMOOTH']=sm[di,ti];out[v+'_FUSION']=fu[di,ti]
        for v in CONTROLS:
            sm,fu=compose_current(mat('RETURN'),mat(v+'_CURRENT'))
            np.testing.assert_allclose(fu[di,ti],out[v+'_FUSION'],atol=2e-15,rtol=0,equal_nan=True)
        out.to_csv(ROOT/f'results/{m}_SCORES.csv.gz',index=False,compression='gzip');scores[m]=out
    pd.DataFrame(traces).to_csv(ROOT/'results/PARAMETER_TRACE.csv',index=False)
    return scores

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--resume-scores',action='store_true');ap.add_argument('--year',type=int);args=ap.parse_args()
    g,f,c=load_groups()
    if not (ROOT/'results/PARITY.json').exists():raise RuntimeError('Run controls before training')
    models={int(k):v for k,v in json.loads((ROOT/'results/ANNUAL_MODELS.json').read_text()).items()} if args.resume_scores else fit_all(g,[args.year] if args.year else None)
    if set(models)!=set(range(2021,2027)):
        print('ANNUAL_BATCH_SAVED',sorted(models),flush=True);raise SystemExit(0)
    build_scores(g,f,c,models)
    print('SCORES_COMPLETE',flush=True)
