#!/usr/bin/env python3
"""Aggregate V2 large-leaf year-shards without refitting or changing inputs."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import v2_large_leaf_sweep as x

VARIANTS=['reference_depth4','leaves_31','leaves_63','leaves_127','leaves_255','leaves_511']
U=['ic','raw_ic','raw_top1_hit','raw_top3_capture','top1_hit','top3_capture','winner_rank','regret','selected_return_21','selected_excess_21']
B=['raw_top1_hit','raw_selected_excess_21','top1_hit','top3_capture','regret','selected_excess_21']

def paired_bands(basket):
    monthly=basket.groupby(['variant','signal_date'],as_index=False)[B].mean()
    base=monthly[monthly.variant=='leaves_31'].sort_values('signal_date').set_index('signal_date')
    rows=[]
    for name in [v for v in VARIANTS if v!='leaves_31']:
        other=monthly[monthly.variant==name].sort_values('signal_date').set_index('signal_date')
        if not base.index.equals(other.index):
            raise RuntimeError('Mismatched evaluation dates for '+name)
        for metric in ['top1_hit','top3_capture','regret','selected_excess_21','raw_top1_hit']:
            d=(other[metric]-base[metric]).to_numpy(float)
            if not np.isfinite(d).all(): raise RuntimeError('Nonfinite metric')
            n=len(d)
            for block in (3,6,12):
                rng=np.random.default_rng(20261020+block)
                reps=4000
                starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
                indices=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
                means=d[indices].mean(axis=1)
                rows.append({'variant':name,'reference':'leaves_31','metric':metric,
                    'n_shared_months':n,'bootstrap_block_months':block,
                    'mean_delta':float(d.mean()),
                    'ci95_lo':float(np.quantile(means,.025)),
                    'ci95_hi':float(np.quantile(means,.975)),
                    'sampling_unit':'months shared by 500 correlated baskets'})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--shard-dir',default='runs')
    ap.add_argument('--raw',default='etf_trader_raw')
    ap.add_argument('--baskets',default='regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv')
    ap.add_argument('--out',default='runs/v2_large_leaf_complete')
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    paths=sorted(Path(a.shard_dir).glob('shard_*/OOS_SCORES.csv'))
    if len(paths)!=3: raise RuntimeError(f'Expected three independent year-shards, found {paths}')
    scores=pd.concat([pd.read_csv(p,parse_dates=['signal_date','entry_date','exit_date','exit_date_21']) for p in paths],ignore_index=True)
    if scores.duplicated(['variant','signal_date','ticker']).any():
        raise RuntimeError('Duplicate date/name prediction: duplicated year-shards')
    if set(scores.variant)!=set(VARIANTS):raise RuntimeError('Unexpected variants: '+str(scores.variant.unique()))
    date_sets={v:tuple(sorted(t.signal_date.unique())) for v,t in scores.groupby('variant')}
    if len(set(date_sets.values()))!=1:raise RuntimeError('Not all variants cover identical signal dates')
    audit=[];leaf=[]
    for p in paths:
        audit+=json.loads((p.parent/'FIT_AUDIT.json').read_text())
        leaf.append(pd.read_csv(p.parent/'REALIZED_LEAF_COUNTS.csv'))
    leaf=pd.concat(leaf,ignore_index=True)
    if leaf.duplicated(['year','variant']).any(): raise RuntimeError('Duplicated yearly leaf-count audit')
    expected_years=set(range(2018,2027))
    fitted=set(int(o['year']) for o in audit if o['status']=='FIT')
    if fitted!=expected_years:raise RuntimeError(f'Missing annual out-of-sample years: {expected_years-fitted}')
    n_expected=9*len(VARIANTS)
    if len(leaf)!=n_expected:raise RuntimeError(f'Expected {n_expected} tree-size audits, got {len(leaf)}')
    sha=hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()
    if sha!=x.BSHA:raise RuntimeError('Basket membership mutated')
    mats,cats,manifest=x.load_ticker_csv_folder(a.raw)
    if len(cats)!=149:raise RuntimeError('Noncanonical raw universe')
    mats={key:v.loc[v.index>=pd.Timestamp(2011,1,1)] for key,v in mats.items()}
    baskets=x.load_baskets(a.baskets,cats)
    if len(baskets)!=500 or any(len(b)!=24 for b in baskets):raise RuntimeError('Wrong basket membership')
    scores.to_csv(out/'OOS_SCORES.csv',index=False)
    universe,basket=x.assess(scores,baskets)
    universe.to_csv(out/'UNIVERSE_MONTHLY.csv',index=False)
    basket.to_csv(out/'BASKET_MONTHLY.csv',index=False)
    tree_path=out/'REALIZED_LEAF_COUNTS.csv'
    leaf.to_csv(tree_path,index=False)
    ci=paired_bands(basket)
    ci.to_csv(out/'PAIRED_MONTHLY_BOOTSTRAP.csv',index=False)
    replay_rows=[]
    for variant,g in scores.groupby('variant',sort=True):
        dates,e,t=x.replay(g[['signal_date','ticker','score']],mats,baskets,cost=.001)
        for period,(a_year,b_year) in x.PERIODS.items():
            mask=(dates.year>=a_year)&(dates.year<=b_year)
            if mask.sum()>1:
                replay_rows.append({'variant':variant,'period':period,
                    **x.metrics(x.subpath(e,mask),t[:,mask])})
        print('REPLAY_DONE',variant,flush=True)
    replay=pd.DataFrame(replay_rows)
    replay.to_csv(out/'REPLAY.csv',index=False)
    aggregate={'status':'SUCCESS','source_only':True,
        'etfs':149,'baskets':500,'basket_size':24,'basket_sha256':sha,
        'fitted_years':sorted(fitted),'test_signal_dates':len(date_sets[VARIANTS[0]]),
        'test_start':str(min(date_sets[VARIANTS[0]])), 'test_end':str(max(date_sets[VARIANTS[0]])),
        'configs':x.configurations(),'seeds':x.k.COMPACT_SEEDS,'n_features':len(x.k.F2D_FEATURES),
        'label':'mature forward 21-day cross-sectional rank, next-session entry',
        'fixed_mix':'V2 Compact21 70% + Tail 30% + macro',
        'fixed_unchanged_training_windows':True,
        'past_scores_used_for_fit':False,
        'data_file_manifest':manifest,
        'fit_audit':audit,
        'mean_realized_leaf_counts':leaf.groupby('variant')[['mean_realized_leaves','p90_realized_leaves','max_realized_leaves','fraction_at_cap']].mean().reset_index().to_dict('records'),
        'basket_overall':basket.groupby('variant')[B].mean().reset_index().to_dict('records'),
        'basket_yearly':basket.groupby(['variant','year'])[B].mean().reset_index().to_dict('records'),
        'universe_overall':universe.groupby('variant')[U].mean().reset_index().to_dict('records'),
        'universe_yearly':universe.groupby(['variant','year'])[U].mean().reset_index().to_dict('records'),
        'replay':replay_rows,'paired_monthly_bootstrap':ci.to_dict('records')}
    (out/'RESULT.json').write_text(json.dumps(aggregate,indent=2,default=str))
    print('FINAL_RANKING',json.dumps({
        'year_count':len(fitted),
        'signal_months':aggregate['test_signal_dates'],
        'basket_overall':aggregate['basket_overall'],
        'universe_overall':aggregate['universe_overall'],
        'leaf_usage':aggregate['mean_realized_leaf_counts'],
        'replay_full':[v for v in replay_rows if v['period']=='full']},default=str),flush=True)

if __name__=='__main__':
    main()
