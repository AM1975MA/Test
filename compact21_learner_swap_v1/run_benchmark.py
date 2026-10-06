#!/usr/bin/env python3
"""Frozen Compact21 learner swap; native training, common and native inference."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from etf_trader.source_only import kernel as k
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality
from compact21_learner_swap_v1.learners import fit, VARIANTS
KEYS=['signal_date','ticker']
PAIRS=((1,2),(1,3),(2,3))

def keys_hash(frame):
    return hashlib.sha256(frame[KEYS].sort_values(KEYS).to_csv(index=False,date_format='%Y-%m-%dT%H:%M:%S').encode()).hexdigest()

def evaluation_coverage(trains, tests, common):
    result={'train_keys_sha256':{str(i):keys_hash(trains[i]) for i in (1,2,3)},
            'test_keys_sha256':{str(i):keys_hash(tests[i]) for i in (1,2,3)},
            'common_keys_sha256':keys_hash(common),'common_rows':len(common),
            'common_queries':common.signal_date.nunique(),'quality_keys_sha256':{},
            'quality_rows':{},'quality_queries':{}}
    for i in (1,2,3):
        z=tests[i]; mask=z.target_rank_21.notna()&z.exit_date_21.notna()&(z.exit_date_21<=pd.Timestamp('2026-07-01'))
        q=z.loc[mask]; result['quality_keys_sha256'][str(i)]=keys_hash(q)
        result['quality_rows'][str(i)]=len(q); result['quality_queries'][str(i)]=q.signal_date.nunique()
    return result


def score_gap(keys, pa, pb):
    """Empirical sufficient-margin diagnostic on one fixed aligned query panel.

    Center each snapshot score vector and divide by its own query RMS. Positive
    scaling leaves ranks unchanged. Observed epsilon is the maximum difference
    on this specific pair, not a future bound or an investment confidence score.
    The diagnostic never influences fitting, eligibility, or execution.
    """
    if len(keys)!=len(pa) or len(keys)!=len(pb) or not np.isfinite(pa).all() or not np.isfinite(pb).all():
        raise ValueError('Invalid aligned score gap input')
    records=[]
    for date,group in keys.reset_index(drop=True).groupby('signal_date',sort=True):
        ix=group.index.to_numpy(); a=np.asarray(pa,float)[ix]; b=np.asarray(pb,float)[ix]
        a=a-a.mean(); b=b-b.mean()
        ra=float(np.sqrt(np.mean(a*a))); rb=float(np.sqrt(np.mean(b*b)))
        if ra: a=a/ra
        if rb: b=b/rb
        # Keys are ticker-sorted, matching deterministic tie handling in stability.
        oa=np.argsort(-a,kind='stable'); ob=np.argsort(-b,kind='stable')
        margin_a=float(a[oa[0]]-a[oa[1]]) if len(a)>1 else 0.
        margin_b=float(b[ob[0]]-b[ob[1]]) if len(b)>1 else 0.
        epsilon=float(np.max(np.abs(a-b))); swap=bool(oa[0]!=ob[0])
        sufficient=bool(margin_a>2*epsilon)
        if sufficient and swap: raise ValueError('Margin sufficient-condition violated')
        records.append({'signal_date':date.isoformat(),'query_rows':len(group),
            'top1_a':str(group.iloc[oa[0]].ticker),'top1_b':str(group.iloc[ob[0]].ticker),
            'top1_swap':swap,'margin_a':margin_a,'margin_b':margin_b,
            'observed_epsilon':epsilon,'rms_a':ra,'rms_b':rb,
            'a_margin_gt_2epsilon':sufficient,
            'flat_a':ra==0,'flat_b':rb==0})
    if not records: raise ValueError('Empty score gap diagnostic')
    return {'normalization':'per_query_centered_unit_RMS',
        'interpretation':'Sufficient condition for this observed score perturbation only; no universal noise bound. All actual swaps necessarily fail certification, so this cannot classify economic near-ties or identify causes.',
        'queries':records,'summary':{'query_count':len(records),
        'top1_swaps':sum(z['top1_swap'] for z in records),
        'sufficient_margin_queries':sum(z['a_margin_gt_2epsilon'] for z in records),
        'certified_fraction':float(np.mean([z['a_margin_gt_2epsilon'] for z in records])),
        'margin_a_quantiles':{str(q):float(np.quantile([z['margin_a'] for z in records],q)) for q in (.1,.5,.9)},
        'epsilon_quantiles':{str(q):float(np.quantile([z['observed_epsilon'] for z in records],q)) for q in (.1,.5,.9)},
        'mean_margin_a':float(np.mean([z['margin_a'] for z in records])),
        'mean_observed_epsilon':float(np.mean([z['observed_epsilon'] for z in records]))}}

def compare_native(tests,predictions):
    frames=[]
    for i in (1,2,3):
        z=tests[i][KEYS].copy();z['p']=predictions[i];frames.append(z)
    a=align(frames)
    return {f'{i}-{j}':stability(a[0][KEYS],a[i-1].p.to_numpy(),a[j-1].p.to_numpy()) for i,j in PAIRS}

def label_compare(trains,ys):
    # Compare each variant across snapshots only. Ridge continuous labels and
    # legacy integer labels are on different scales, so value differences are
    # not a cross-model comparison. Relation flips/tie transitions are invariant.
    frames=[]
    for i in (1,2,3):
        z=trains[i][KEYS].copy();z['y']=ys[i];frames.append(z)
    a=align(frames);out={}
    for i,j in PAIRS:
        flips=[];total=0;changed=0
        for _,g in a[0].groupby('signal_date'):
            ix=g.index.to_numpy();va=a[i-1].loc[ix,'y'].to_numpy();vb=a[j-1].loc[ix,'y'].to_numpy()
            tri=np.triu_indices(len(ix),1)
            ca=np.sign(va[:,None]-va[None,:])[tri];cb=np.sign(vb[:,None]-vb[None,:])[tri]
            total+=len(ca);changed+=int(np.sum(ca!=cb))
        out[f'{i}-{j}']={'label_value_disagreement':float(np.mean(a[i-1].y!=a[j-1].y)),'pair_relation_disagreement':changed/total if total else 0.0,'pairs':total}
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=VARIANTS,required=True)
    for i in (1,2,3): ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--years',default=','.join(map(str,range(2017,2027))))
    a=ap.parse_args();years=list(map(int,a.years.split(',')))
    if not years or len(years)!=len(set(years)) or any(y not in range(2017,2027) for y in years): raise ValueError('Invalid annual folds')
    R={i:load(Path(getattr(a,f'r{i}'))) for i in (1,2,3)}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    res={'status':'RUNNING','variant':a.variant,'years':years,'per_year':{},'environment':{n:importlib.metadata.version(n) for n in ('numpy','pandas','scikit-learn','xgboost','lightgbm','scipy','pyarrow')},'input_sha256':{str(i):hashlib.sha256((Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet').read_bytes()).hexdigest() for i in (1,2,3)}}
    from etf_trader.source_only import models
    res['input_contract']={'protocol':'COMPACT21_LEARNER_SWAP_V1','years':years,
        'train_cohorts':'native_no_intersection','common_inference_repeat':2,
        'signal_cutoff':'2026-06-30','quality_exit_cutoff':'2026-07-01',
        'canonical_source_sha256':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in
             [('kernel',Path(k.__file__)),('models',Path(models.__file__)),('worker',Path(k.__file__).with_name('_xgb_worker.py'))]},
        'learner_source_sha256':{'learners.py':hashlib.sha256((Path(__file__).with_name('learners.py')).read_bytes()).hexdigest()}}
    with tempfile.TemporaryDirectory() as td:
        for year in years:
            trains={i:train_frame(R[i],year) for i in (1,2,3)}
            tests={}
            for i in (1,2,3):
                f=R[i];valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
                tests[i]=f[(f.signal_date.dt.year==year)&(f.signal_date<='2026-06-30')&valid].sort_values(KEYS).reset_index(drop=True)
                if tests[i].duplicated(KEYS).any() or trains[i].duplicated(KEYS).any():raise ValueError('Duplicate keys')
            common=align([tests[i] for i in (1,2,3)])[1]
            if common.empty: raise ValueError('No common evaluation rows')
            pcs={};pns={};ys={};audits={};times={}
            for i in (1,2,3):
                p,au,y,t=fit(trains[i],[common,tests[i]],a.variant,year,Path(td),f'{year}_{i}')
                pcs[i],pns[i]=p;ys[i]=y;audits[str(i)]=au;times[str(i)]=t
            pp,_,_,_=fit(trains[2],[common,tests[2]],a.variant,year,Path(td),f'{year}_det')
            delta=float(max(np.max(np.abs(x-y)) for x,y in zip(pp,[pcs[2],pns[2]])))
            detbytes=all(x.tobytes()==y.tobytes() for x,y in zip(pp,[pcs[2],pns[2]]))
            qualities={}
            for i in (1,2,3):
                eval_mask=(tests[i].target_rank_21.notna()&tests[i].exit_date_21.notna()&(tests[i].exit_date_21<=pd.Timestamp('2026-07-01'))).to_numpy()
                if not eval_mask.any(): raise ValueError('No mature quality rows')
                target=tests[i].loc[eval_mask,'target_rank_21'].to_numpy(float)
                if not np.isfinite(target).all() or ((target<0)|(target>1)).any(): raise ValueError('Invalid mature quality target')
                qualities[str(i)]=quality(tests[i].loc[eval_mask],pns[i][eval_mask])
            matpass=all(bool((trains[i].signal_date<pd.Timestamp(year,1,1)).all()&(trains[i].exit_date_21<pd.Timestamp(year,1,1)).all()) for i in (1,2,3))
            cell={'common_inference':{f'{i}-{j}':stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},'common_score_gap':{f'{i}-{j}':score_gap(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},'native_inference':compare_native(tests,pns),'quality':qualities,'label_changes':label_compare(trains,ys),'transforms':audits,'train_rows':{str(i):len(trains[i]) for i in (1,2,3)},'test_rows':{str(i):len(tests[i]) for i in (1,2,3)},'common_test_rows':len(common),'maturity_PASS':matpass,'determinism':{'max_abs':delta,'PASS':delta==0.0 and detbytes,'common_and_native_bytes_exact':detbytes},'fit_seconds':times}
            cell['evaluation_coverage']=evaluation_coverage(trains,tests,common)
            res['per_year'][str(year)]=cell;out.write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
            print(json.dumps({'year':year,'variant':a.variant,'rank_mad_mean':np.mean([q['rank_mean_abs'] for q in cell['common_inference'].values()]),'maturity':matpass,'determinism':delta}),flush=True)
    res['aggregate']={}
    for scope in ('common_inference','native_inference','quality'):
        rows=[q for y in res['per_year'].values() for q in y[scope].values()]
        res['aggregate'][scope]={f:float(np.mean([z[f] for z in rows])) for f in rows[0]}
    res['aggregate_by_pair']={scope:{pair:{f:float(np.mean([z[scope][pair][f] for z in res['per_year'].values()])) for f in next(iter(res['per_year'].values()))[scope][pair]} for pair in ('1-2','1-3','2-3')} for scope in ('common_inference','native_inference')}
    res['ALL_MATURITY_PASS']=all(z['maturity_PASS'] for z in res['per_year'].values())
    res['ALL_DETERMINISM_PASS']=all(z['determinism']['PASS'] for z in res['per_year'].values())
    res['status']='COMPACT21_LEARNER_SWAP_V1_BENCHMARK_COMPLETE';out.write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
