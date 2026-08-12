#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def one(s: str, old: str, new: str, label: str) -> str:
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)


CONFIGS={
    # Directly documented in the 20 Jul S3/S3B source family.
    'S3B60_B5': {
        'params': "dict(objective='rank:pairwise',eval_metric='ndcg',n_estimators=60,max_depth=4,learning_rate=0.05,min_child_weight=20,subsample=0.80,colsample_bytree=0.75,reg_lambda=12.0,reg_alpha=0.2,tree_method='hist',n_jobs=2,verbosity=0)",
        'y': "np.minimum(4,np.floor(tr.target_rank_pct.to_numpy(float)*5.0)).astype(int)",
        'evidence': '2026-07-20 S3/S3B documented LambdaRank block + 5 relevance bins',
    },
    'S3B60_R100': {
        'params': "dict(objective='rank:pairwise',eval_metric='ndcg',n_estimators=60,max_depth=4,learning_rate=0.05,min_child_weight=20,subsample=0.80,colsample_bytree=0.75,reg_lambda=12.0,reg_alpha=0.2,tree_method='hist',n_jobs=2,verbosity=0)",
        'y': "(tr.target_rank_pct*100).round().astype(int)",
        'evidence': '20 Jul tree block crossed only with later proven Titanium monthly relevance',
    },
    # Explicitly labelled reimplementation in the 24 Jul reconciliation notebook.
    'REIMPL360_B10': {
        'params': "dict(objective='rank:pairwise',eval_metric='ndcg@3',n_estimators=360,max_depth=4,learning_rate=0.035,subsample=0.85,colsample_bytree=0.80,min_child_weight=8.0,reg_lambda=8.0,reg_alpha=0.10,tree_method='hist',n_jobs=2,verbosity=0)",
        'y': "np.minimum(9,np.floor(tr.target_rank_pct.to_numpy(float)*10.0-1e-12)).astype(int)",
        'evidence': '24 Jul explicit Super Gold reimplementation block + its 10-bin relevance',
    },
    'REIMPL360_R100': {
        'params': "dict(objective='rank:pairwise',eval_metric='ndcg@3',n_estimators=360,max_depth=4,learning_rate=0.035,subsample=0.85,colsample_bytree=0.80,min_child_weight=8.0,reg_lambda=8.0,reg_alpha=0.10,tree_method='hist',n_jobs=2,verbosity=0)",
        'y': "(tr.target_rank_pct*100).round().astype(int)",
        'evidence': '27 Jul source-only Titanium retraining convention on 24 Jul reimplementation tree block',
    },
}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True)
    ap.add_argument('--config',choices=sorted(CONFIGS),required=True)
    a=ap.parse_args(); p=Path(a.source); s=p.read_text(); c=CONFIGS[a.config]

    old="models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2"
    new="models_dir.mkdir(parents=True,exist_ok=True); params="+c['params']
    s=one(s,old,new,'compact params')

    oldy="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]"
    newy="groups=tr.groupby('signal_date',sort=True).size().tolist();y="+c['y']+";seed_parts=[]"
    if a.config!='REIMPL360_R100':
        s=one(s,oldy,newy,'compact relevance')

    # Packaging bug is unrelated to economics but would otherwise fail after a full fit.
    oldpack="for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))"
    newpack="for k,x in mats.items():\n        q=x.stack(dropna=False).rename(k.lower()).reset_index(); q.columns=['date','ticker',k.lower()]; longs.append(q)"
    if oldpack in s:
        s=one(s,oldpack,newpack,'package')

    s=s.replace("'compact_historical_params':False", "'compact_historical_params':'FORENSIC_"+a.config+"'")
    s=s.replace("'compact_relevance':'rank_pct_x100_round'", "'compact_relevance':'"+a.config+"'")
    p.write_text(s)
    print('CONFIG',a.config)
    print('EVIDENCE',c['evidence'])
    print('PARAMS',c['params'])
    print('Y',c['y'])

if __name__=='__main__':
    main()
