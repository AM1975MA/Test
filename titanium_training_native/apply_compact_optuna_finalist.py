#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

CANDIDATES={
 'OPT_NDCG_A':dict(n_estimators=440,max_depth=5,learning_rate=0.0160697539674804,min_child_weight=79.5707692422253,subsample=0.7757528712268886,colsample_bytree=0.7056809499757816,reg_lambda=2.491426499316969,reg_alpha=0.0656373663671147,gamma=0.9696383189735136),
 'OPT_NDCG_B':dict(n_estimators=240,max_depth=6,learning_rate=0.043137,min_child_weight=77.461624,subsample=0.720032,colsample_bytree=0.852468,reg_lambda=29.044870,reg_alpha=0.162717,gamma=0.798866),
 'OPT_HIT_A':dict(n_estimators=600,max_depth=5,learning_rate=0.015366,min_child_weight=11.199928,subsample=0.789722,colsample_bytree=0.983545,reg_lambda=4.116873,reg_alpha=0.085729,gamma=0.387534),
}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--candidate',required=True,choices=sorted(CANDIDATES));a=ap.parse_args();p=Path(a.source);s=p.read_text();c=CANDIDATES[a.candidate]
    old="models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2"
    vals=", ".join(f"{k}={repr(v)}" for k,v in c.items())
    new=f"models_dir.mkdir(parents=True,exist_ok=True); params=dict(objective='rank:pairwise',eval_metric='ndcg@3',tree_method='hist',verbosity=0,n_jobs=2,{vals})"
    if s.count(old)!=1: raise RuntimeError(f'parameter anchor count={s.count(old)}')
    s=s.replace(old,new)
    s=s.replace("'compact_historical_params':'PUBLISHED_360x3_PLATINUM_COMPACT_PLUS_EXACT_JUL27_TAIL'",f"'compact_historical_params':'DEV_OPTUNA_{a.candidate}_3SEED_PLATINUM_EXACT_TAIL_CVAR'")
    s=s.replace("'compact_trees':args.n_estimators",f"'compact_trees':{c['n_estimators']}")
    p.write_text(s);print('Applied',a.candidate,c)
if __name__=='__main__':main()
