#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib

ap=argparse.ArgumentParser()
ap.add_argument('--input',required=True)
ap.add_argument('--output',required=True)
a=ap.parse_args()
p=Path(a.input); s=p.read_text()

repls=[
(
"models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2",
"models_dir.mkdir(parents=True,exist_ok=True); params=dict(objective='rank:pairwise',eval_metric='ndcg',n_estimators=60,max_depth=4,learning_rate=0.05,min_child_weight=20,subsample=0.80,colsample_bytree=0.75,reg_lambda=12.0,reg_alpha=0.2,tree_method='hist',n_jobs=2,verbosity=0)"
),
(
"tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])",
"tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_21.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
),
(
"groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]",
"groups=tr.groupby('signal_date',sort=True).size().tolist();y=np.minimum(4,np.floor(tr.target_rank_21.to_numpy(float)*5.0)).astype(int);seed_parts=[]"
),
(
"(pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.tail_rank>=.80)",
"(pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.titanium_score_pre_macro>=.80)"
),
(
"for target,w in OPP_WEIGHTS.items(): op[target+'_pred_rank']=op.groupby('signal_date')[target+'_pred'].rank(pct=True,method='average')\n    op['opp_raw']=sum(w*op[target+'_pred_rank'] for target,w in OPP_WEIGHTS.items());op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))",
"op['opp_raw']=op['target_excess_max_pred'];op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))"
),
]
for old,new in repls:
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'Patch pattern count={n}, expected 1: {old[:120]}')
    s=s.replace(old,new)
# Mark identity and force manifest description.
s=s.replace("'compact_trees':args.n_estimators", "'compact_trees':60,'compact_historical_params':True,'compact_target':'fwd_ret_21','compact_relevance_bins':5")
Path(a.output).write_text(s)
print('patched_sha256',hashlib.sha256(s.encode()).hexdigest())
