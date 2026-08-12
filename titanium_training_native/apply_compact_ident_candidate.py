#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

CANDIDATES={
 'D3_240_MCW30':dict(n_estimators=240,max_depth=3,learning_rate=.035,min_child_weight=30.,subsample=.85,colsample_bytree=.65,reg_lambda=12.,reg_alpha=.50),
 'ANCESTOR_D3_180':dict(n_estimators=180,max_depth=3,learning_rate=.040,min_child_weight=20.,subsample=.85,colsample_bytree=.65,reg_lambda=12.,reg_alpha=1.00),
 'D5_300_SLOW':dict(n_estimators=300,max_depth=5,learning_rate=.025,min_child_weight=20.,subsample=.85,colsample_bytree=.70,reg_lambda=16.,reg_alpha=.50),
}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--candidate',required=True,choices=sorted(CANDIDATES));a=ap.parse_args();p=Path(a.source);s=p.read_text();c=CANDIDATES[a.candidate]
    old="models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2"
    vals=", ".join(f"{k}={repr(v)}" for k,v in c.items())
    new=f"models_dir.mkdir(parents=True,exist_ok=True); params=dict(objective='rank:pairwise',eval_metric='ndcg@3',tree_method='hist',verbosity=0,n_jobs=2,{vals})"
    if s.count(old)!=1: raise RuntimeError(f'parameter anchor count={s.count(old)}')
    s=s.replace(old,new)
    marker="'compact_historical_params':'PUBLISHED_360x3_PLATINUM_COMPACT_PLUS_EXACT_JUL27_TAIL'"
    s=s.replace(marker,f"'compact_historical_params':'IDENTIFIED_{a.candidate}_3SEED_PLATINUM_EXACT_TAIL_CVAR'")
    s=s.replace("'compact_trees':args.n_estimators",f"'compact_trees':{c['n_estimators']}")
    p.write_text(s);print('Applied',a.candidate,c)
if __name__=='__main__':main()
