"""Independent retained-vector evidence and preregistered predictive gates."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from statistics import mean
import numpy as np
import pandas as pd
from compact21_predictive_v2.metrics import evaluate, paired_compare
from compact21_predictive_v2.run import VARIANTS, KEYS, PAIRS, LINE

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def normalized_numeric(contract):
    keys=('python','machine','numpy','pandas','scipy','sklearn','execution_env','numpy_build_config','effective_cpu_features')
    if any(key not in contract for key in keys):raise ValueError('Incomplete numeric contract')
    result={key:contract[key] for key in keys if key!='effective_cpu_features'}
    # show_config retains the compiled dispatch target availability. The raw
    # inventory also contains constituent hardware flags (VL, BW, etc.) that
    # cannot dispatch independently in this pinned NumPy wheel.
    simd=contract['numpy_build_config']['SIMD Extensions']
    if contract['numpy']!='2.3.5':raise ValueError('Unregistered NumPy dispatch semantics')
    groups=('AVX512F','AVX512CD','AVX512_KNL','AVX512_KNM','AVX512_SKX','AVX512_CLX','AVX512_CNL','AVX512_ICL','AVX512_SPR')
    active=simd['baseline']+simd['found'];inactive=simd['not found']
    expected={'SSE','SSE2','SSE3','SSSE3','SSE41','POPCNT','SSE42','AVX','F16C','FMA3','AVX2',*groups}
    if set(active)&set(inactive) or set(active+inactive)!=expected:raise ValueError('Incomplete compiled dispatch inventory')
    features=contract['effective_cpu_features']
    if any(features.get(key) is not True for key in active) or any(features.get(key) is not False for key in inactive):
        raise ValueError('Dispatch report contradicts retained CPU availability')
    if any(features[key] for key in groups) or not features['AVX2'] or not features['FMA3']:
        raise ValueError('Not the frozen AVX2 numerical profile')
    result['compiled_cpu_targets']={key:features[key] for key in sorted(expected)}
    result['threadpools']=[{key:p.get(key) for key in ('user_api','internal_api','num_threads','version','threading_layer','architecture')} for p in contract['threadpools']]
    return result

def load_variant(root,variant):
    paths=[p for p in Path(root).rglob('RESULT.json') if json.loads(p.read_text()).get('variant')==variant]
    if len(paths)!=1:raise ValueError('Missing/duplicate variant '+variant)
    p=paths[0];q=json.loads(p.read_text())
    if q['status']!=LINE+'_COMPLETE' or q['years']!=list(range(2017,2027)):raise ValueError('Incomplete folds/status')
    if set(q['per_year'])!={str(y) for y in range(2017,2027)}:raise ValueError('Missing annual fit evidence')
    if set(q['files_sha256'])!={'NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet'}:raise ValueError('Missing retained vector hashes')
    for year,cell in q['per_year'].items():
        if cell['determinism_PASS'] is not True or set(cell['transforms'])!={'1','2','3'}:raise ValueError('Failed/missing refit evidence')
        cutoff=pd.Timestamp(int(year),1,1)
        for audit in cell['transforms'].values():
            if audit['maturity_PASS'] is not True or pd.Timestamp(audit['cutoff'])!=cutoff or pd.Timestamp(audit['max_signal_date'])>=cutoff or pd.Timestamp(audit['max_exit_date_21'])>=cutoff:
                raise ValueError('Training maturity failed')
        if variant in ('BASE','RIDGE','LGBM_LAMBDARANK') and not all(cell['legacy_control'].values()):
            # Retain unexplained mismatches, but do not allow qualification.
            q['LEGACY_PARITY_PASS']=False
    for name,digest in q['files_sha256'].items():
        if sha(p.parent/name)!=digest:raise ValueError('Altered prediction evidence')
    native=pd.read_parquet(p.parent/'NATIVE_PREDICTIONS.parquet')
    common=pd.read_parquet(p.parent/'COMMON_PREDICTIONS.parquet')
    ev=evaluate(native,quality_exit_cutoff='2026-07-01')
    if ev!=q['predictive']:raise ValueError('Reported metrics differ from retained evidence')
    if set(native.vintage)!={1,2,3} or set(common.vintage)!={1,2,3}:raise ValueError('Missing vintage')
    for frame in (native,common):
        if not frame.groupby('signal_date').vintage.nunique().eq(3).all():raise ValueError('Date lacks all vintages')
    # The frozen reference was created on Linux. Canonical LF serialization
    # makes independent Windows verification invariant to host CSV newlines.
    def keys_hash(frame):
        data=frame[KEYS].sort_values(KEYS).to_csv(index=False,date_format='%Y-%m-%dT%H:%M:%S',lineterminator='\n')
        return hashlib.sha256(data.encode()).hexdigest()
    for year,cell in q['per_year'].items():
        coverage=cell['evaluation_coverage']
        for repeat in (1,2,3):
            f=native[(native.vintage==repeat)&(native.signal_date.dt.year==int(year))]
            if keys_hash(f)!=coverage['test_keys_sha256'][str(repeat)]:raise ValueError('Native key evidence mismatch')
            c=common[(common.vintage==repeat)&(common.signal_date.dt.year==int(year))]
            if keys_hash(c)!=coverage['common_keys_sha256']:raise ValueError('Common key evidence mismatch')
    if not q['ALL_DETERMINISM_PASS'] or q['negative_feedback_changed'] or q['production_adoption']:raise ValueError('Invalid invariants')
    return {'result':q,'native':native,'common':common,'eval':ev,'path':str(p),'sha256':sha(p)}

def stability_by_date(frame):
    result={}
    if frame.duplicated(['vintage']+KEYS).any() or not np.isfinite(frame.pred).all():raise ValueError('Invalid stability vectors')
    for i,j in PAIRS:
        a=frame[frame.vintage==i].sort_values(KEYS);b=frame[frame.vintage==j].sort_values(KEYS)
        keys=a[KEYS].merge(b[KEYS],on=KEYS,how='inner',validate='one_to_one').sort_values(KEYS)
        if keys.empty:raise ValueError('Empty aligned stability')
        if len(keys)!=len(a) or len(keys)!=len(b):raise ValueError('Unexplained native/common coverage loss')
        aa=keys.merge(a,on=KEYS,validate='one_to_one');bb=keys.merge(b,on=KEYS,validate='one_to_one')
        rows=[]
        for date,ga in aa.groupby('signal_date',sort=True):
            gb=bb[bb.signal_date==date]
            ar=ga.pred.rank(method='average',pct=True).to_numpy();br=gb.pred.rank(method='average',pct=True).to_numpy()
            ta=ga.sort_values(['pred','ticker'],ascending=[False,True],kind='stable');tb=gb.sort_values(['pred','ticker'],ascending=[False,True],kind='stable')
            sa=set(ta.head(5).ticker);sb=set(tb.head(5).ticker)
            rows.append({'signal_date':pd.Timestamp(date).isoformat(),'rank_mad':float(np.mean(np.abs(ar-br))),
                         'top1_disagreement':float(ta.ticker.iloc[0]!=tb.ticker.iloc[0]),'top5_jaccard':len(sa&sb)/len(sa|sb),
                         'top1_a':ta.ticker.iloc[0],'top1_b':tb.ticker.iloc[0],'aligned_tickers':len(ga)})
        result[f'{i}-{j}']={'dates':rows,'mean':{key:mean(r[key] for r in rows) for key in ('rank_mad','top1_disagreement','top5_jaccard')},
                            'coverage':{'rows_a':len(a),'rows_b':len(b),'aligned_rows':len(keys),'lost_a':len(a)-len(keys),'lost_b':len(b)-len(keys)}}
    return {'pairs':result,'mean':{key:mean(p['mean'][key] for p in result.values()) for key in ('rank_mad','top1_disagreement','top5_jaccard')}}

def reduction_gate(candidate,base):
    return candidate==0 if base==0 else candidate<=.75*base

def gate(candidate,base,paired,common,native,bc,bn,controls_pass):
    delta=paired['difference']['top1_realized_percentile']
    interval=paired['bootstrap']['3']['intervals_95pct']['top1_realized_percentile']
    vintage_checks={}
    for repeat in ('1','2','3'):
        ar=[r['top1_realized_percentile'] for r in candidate['eval']['per_date'] if r['vintage']==repeat]
        br=[r['top1_realized_percentile'] for r in base['eval']['per_date'] if r['vintage']==repeat]
        vintage_checks[repeat]=mean(ar)>=mean(br)
    checks={'all_controls_reproduced':controls_pass,
            'primary_positive':delta>0,'primary_familywise_lower_positive':interval is not None and interval['lower98_75_one_sided']>0,
            'primary_each_vintage_not_worse':all(vintage_checks.values()),
            'top5_precision_not_worse':candidate['eval']['aggregate_by_date']['top5_overlap']>=base['eval']['aggregate_by_date']['top5_overlap'],
            'common_rank_mad_reduced_ge25pct':reduction_gate(common['mean']['rank_mad'],bc['mean']['rank_mad']),
            'native_top1_disagreement_reduced_ge25pct':reduction_gate(native['mean']['top1_disagreement'],bn['mean']['top1_disagreement']),
            'each_common_pair_mad_not_worse':all(common['pairs'][p]['mean']['rank_mad']<=bc['pairs'][p]['mean']['rank_mad'] for p in bc['pairs']),
            'each_native_pair_top1_not_worse':all(native['pairs'][p]['mean']['top1_disagreement']<=bn['pairs'][p]['mean']['top1_disagreement'] for p in bn['pairs'])}
    return {'checks':checks,'vintage_checks':vintage_checks,'DEVELOPMENT_CANDIDATE':all(checks.values()),'production_adoption':False}

def summarize(root):
    rows={v:load_variant(root,v) for v in VARIANTS};base=rows['BASE'];br=base['result']
    for v,row in rows.items():
        r=row['result']
        for key in ('input_sha256','input_contract','sources','preregistration_sha256','environment'):
            if r[key]!=br[key]:raise ValueError('Mixed contract/source/runtime '+key)
        if normalized_numeric(r['numeric_contract'])!=normalized_numeric(br['numeric_contract']):raise ValueError('Effective numerical environment differs')
        if not row['native'][['vintage']+KEYS].equals(base['native'][['vintage']+KEYS]):raise ValueError('Native cohort differs')
        if not row['common'][['vintage']+KEYS].equals(base['common'][['vintage']+KEYS]):raise ValueError('Common cohort differs')
    controls=all(rows[v]['result']['LEGACY_PARITY_PASS'] is True for v in ('BASE','RIDGE','LGBM_LAMBDARANK'))
    sc={v:stability_by_date(r['common']) for v,r in rows.items()};sn={v:stability_by_date(r['native']) for v,r in rows.items()}
    output={}
    for v,row in rows.items():
        comparison=None if v=='BASE' else paired_compare(row['eval'],base['eval'])
        output[v]={'predictive':row['eval'],'common_stability':sc[v],'native_stability':sn[v],'paired_vs_BASE':comparison,
                   'gate':None if v=='BASE' else gate(row,base,comparison,sc[v],sn[v],sc['BASE'],sn['BASE'],controls),
                   'result_path':row['path'],'result_sha256':row['sha256']}
    return {'status':LINE+'_SUMMARY_COMPLETE','all_controls_reproduced':controls,'models':output,'production_adoption':False,
            'interpretation':'Preregistered development comparison; historical/conditional intervals do not establish untouched holdout or forward generalization.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    result=summarize(a.inputs);p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'controls':result['all_controls_reproduced'],'models':{v:{'primary':m['predictive']['aggregate_by_date']['top1_realized_percentile'],'gate':m['gate']} for v,m in result['models'].items()}},indent=2))

if __name__=='__main__':main()
