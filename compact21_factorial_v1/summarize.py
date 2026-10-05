"""Independent factorial reconstruction, equal-date and equal-pair diagnostics."""
import argparse,json
from pathlib import Path
from statistics import mean
import numpy as np
import pandas as pd
from compact21_factorial_v1.run import MODELS,KEYS,PAIRS,LINE,ROOT,sha,keys_hash
from compact21_factorial_v1.metrics import evaluate_factorial
from compact21_predictive_v2.summarize import normalized_numeric
from compact21_predictive_v2.metrics import evaluate

def load_cell(path,ref):
    r=json.loads(path.read_text());model=r['model'];year=r['year']
    if r['status']!=LINE+'_COMPLETE' or model not in MODELS or year not in range(2017,2027):raise ValueError('Incomplete factorial job')
    expected={f'X{x}Y{y}' for x in (1,2,3) for y in (1,2,3)}
    if set(r['cells'])!=expected or r['old_run']!=37229180477 or r['negative_feedback_changed'] or r['production_adoption']:
        raise ValueError('Wrong registry/invariants')
    if sha(path.parent/'PREDICTIONS.parquet')!=r['prediction_file_sha256']:raise ValueError('Changed retained factorial vectors')
    p=pd.read_parquet(path.parent/'PREDICTIONS.parquet')
    if p.duplicated(KEYS).any() or p.empty or not np.isfinite(p[list(expected)]).all().all():raise ValueError('Invalid factorial vectors')
    if not p.signal_date.dt.year.eq(year).all() or (p.signal_date>pd.Timestamp('2026-06-30')).any() or keys_hash(p)!=r['inference_keys_sha256']:
        raise ValueError('Wrong inference date/key contract')
    if r['reference_sha256']!=sha(ref['path']) or r['input_sha256']!=ref['result']['input_sha256']:
        raise ValueError('Reference provenance mismatch')
    if normalized_numeric(r['numeric_contract'])!=normalized_numeric(ref['result']['numeric_contract']):raise ValueError('Original reference numeric profile differs')
    old=ref['common'];old=old[old.signal_date.dt.year==year]
    cutoff=pd.Timestamp(year,1,1)
    prepared=json.loads((ROOT/'compact21_factorial_v1/PREPARED_CONTRACT.json').read_text())
    if r['prepared_contract_sha256']!=sha(ROOT/'compact21_factorial_v1/PREPARED_CONTRACT.json'):raise ValueError('Prepared registry changed')
    if r['train_keys_sha256']!=ref['result']['per_year'][str(year)]['evaluation_coverage']['train_keys_sha256']:
        raise ValueError('Native training cohort differs')
    for name,c in r['cells'].items():
        if c['determinism_PASS'] is not True or c['feature_repeat']!=int(name[1]) or c['target_repeat']!=int(name[3]):raise ValueError('Cell registry/refit failed')
        for a in (c['audit'],c['refit_audit']):
            dates=[pd.Timestamp(a[key]) for key in ('cutoff','max_signal_date','max_exit_date_21')]
            if any(pd.isna(date) for date in dates) or a['maturity_PASS'] is not True or dates[0]!=cutoff or dates[1]>=cutoff or dates[2]>=cutoff:
                raise ValueError('Immature factorial donor')
            x=prepared['training'][f'{year}_r{c["feature_repeat"]}'];y=prepared['training'][f'{year}_r{c["target_repeat"]}']
            label_key='continuous_labels_sha256' if model in ('RIDGE','ADDITIVE_RIDGE') else 'integer_labels_sha256'
            if a['train_matrix_sha256']!=x['matrix_sha256'] or a['train_labels_sha256']!=y[label_key] or a['train_rows']!=x['rows']:
                raise ValueError('Wrong feature/target donor audit')
            if a['feature_names']!=ref['result']['per_year'][str(year)]['transforms']['1']['feature_names']:
                raise ValueError('Feature registry changed')
        if c['audit']['prediction_sha256']!=c['refit_audit']['prediction_sha256']:raise ValueError('Refit audit disagrees')
        from compact21_learner_swap_v1.learners import array_hash
        if array_hash(p[name].to_numpy())!=c['prediction_sha256'] or c['audit']['prediction_sha256'][0]!=c['prediction_sha256']:
            raise ValueError('Prediction hash disagrees')
        if name[1]==name[3]:
            o=old[old.vintage==int(name[1])].sort_values(KEYS).reset_index(drop=True)
            if not o[KEYS].equals(p[KEYS].reset_index(drop=True)) or o.pred.to_numpy().tobytes()!=p[name].to_numpy().tobytes() or c['diagonal_control_PASS'] is not True:
                raise ValueError('Old diagonal control differs')
    native=ref['native'];native=native[(native.vintage==2)&(native.signal_date.dt.year==year)].sort_values(KEYS).reset_index(drop=True)
    targetcols=KEYS+['target_rank_21','exit_date_21','target_ret_21']
    pd.testing.assert_frame_equal(p[targetcols].reset_index(drop=True),native[targetcols].reset_index(drop=True))
    return r,p

def aggregate_pairs(pairs):
    if not pairs:raise ValueError('Empty pair aggregation')
    for p in pairs.values():
        if any(v is None or not np.isfinite(v) for v in p['aggregate']['effects'].values()):raise ValueError('Undefined/nonfinite attribution magnitude')
        for c in p['aggregate']['contrasts'].values():
            if any(c[k] is None or not np.isfinite(c[k]) for k in ('rank_mad','top1_flip','top5_jaccard')):raise ValueError('Undefined/nonfinite contrast')
            if c['spearman'] is not None and not np.isfinite(c['spearman']):raise ValueError('Nonfinite Spearman')
    average={'effects':{k:mean(p['aggregate']['effects'][k] for p in pairs.values()) for k in next(iter(pairs.values()))['aggregate']['effects']},'contrasts':{}}
    for name in next(iter(pairs.values()))['aggregate']['contrasts']:
        values=[p['aggregate']['contrasts'][name] for p in pairs.values()]
        rho=[v['spearman'] for v in values if v['spearman'] is not None and np.isfinite(v['spearman'])]
        average['contrasts'][name]={k:mean(v[k] for v in values) for k in ('rank_mad','top1_flip','top5_jaccard')}
        average['contrasts'][name].update(spearman=mean(rho) if rho else None,defined_spearman_pairs=len(rho))
    return average

def summarize(root,reference_root,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    refs={}
    for path in Path(reference_root).rglob('RESULT.json'):
        r=json.loads(path.read_text());model=r.get('variant')
        if model not in MODELS:continue
        if model in refs:raise ValueError('Duplicate old reference')
        if r['status']!='COMPACT21_PREDICTIVE_V2_COMPLETE':raise ValueError('Incomplete old reference')
        for name,digest in r['files_sha256'].items():
            if sha(path.parent/name)!=digest:raise ValueError('Old vector hash mismatch')
        refs[model]={'path':path,'result':r,'common':pd.read_parquet(path.parent/'COMMON_PREDICTIONS.parquet'),'native':pd.read_parquet(path.parent/'NATIVE_PREDICTIONS.parquet')}
    if set(refs)!=set(MODELS):raise ValueError('Missing original references')
    jobs={};base_contract=None
    for path in Path(root).rglob('RESULT.json'):
        r=json.loads(path.read_text())
        if r.get('line')!=LINE:continue
        key=(r['model'],r['year'])
        if key in jobs:raise ValueError('Duplicate model/year')
        r,p=load_cell(path,refs[key[0]])
        contract={k:r[k] for k in ('input_sha256','fit_sources','factorial_sources','protocol_sha256','prepared_contract_sha256')}
        contract['numeric']=normalized_numeric(r['numeric_contract'])
        if base_contract is None:base_contract=contract
        if contract!=base_contract:raise ValueError('Mixed sources/protocol/runtime')
        jobs[key]=(r,p)
    if set(jobs)!={(m,y) for m in MODELS for y in range(2017,2027)}:raise ValueError('Incomplete 40-job matrix')
    summaries={};retained=[];date_records=[];quality={}
    for model in MODELS:
        frame=pd.concat([jobs[(model,y)][1] for y in range(2017,2027)],ignore_index=True).sort_values(KEYS).reset_index(drop=True)
        quality[model]={}
        for x in (1,2,3):
            for y in (1,2,3):
                cell=f'X{x}Y{y}';v=frame.rename(columns={cell:'pred'})
                quality[model][cell]=evaluate(v,quality_exit_cutoff='2026-07-01')
        pairs={}
        for a,b in PAIRS:
            pair=f'{a}-{b}'
            cells={'predAA':f'X{a}Y{a}','predBA':f'X{b}Y{a}','predAB':f'X{a}Y{b}','predBB':f'X{b}Y{b}'}
            f=frame[KEYS+list(cells.values())].rename(columns={v:k for k,v in cells.items()})
            ev=evaluate_factorial(f,expected_keys=frame[KEYS])
            for row in ev.pop('rank_effects'):retained.append({'model':model,'pair':pair,**row})
            for row in ev['per_date']:date_records.append({'model':model,'pair':pair,**row})
            pairs[pair]=ev
        average=aggregate_pairs(pairs)
        summaries[model]={'pairs':pairs,'equal_date_equal_pair':average}
    pd.DataFrame(retained).to_parquet(out/'RANK_ATTRIBUTIONS.parquet',index=False)
    (out/'DATE_DIAGNOSTICS.json').write_text(json.dumps(date_records,indent=2,allow_nan=False)+'\n')
    result={'status':LINE+'_SUMMARY_COMPLETE','all_360_refits_PASS':True,'all_120_diagonal_controls_PASS':True,'models':summaries,
      'fixed_repeat2_quality':quality,'registry':{'jobs':40,'unique_cells':360,'independent_fit_calls':720,'model_year_pair_cell_observations':480},
      'contract':base_contract,'production_adoption':False,'negative_feedback_changed':False,
      'interpretation':'Signed feature+label contributions equal total rank response; their absolute magnitudes are not additive shares. Interaction is separate. Historical constructed training interventions, not economic causal effects or fresh holdout evidence.'}
    result['files_sha256']={p.name:sha(p) for p in (out/'RANK_ATTRIBUTIONS.parquet',out/'DATE_DIAGNOSTICS.json')}
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({m:r['equal_date_equal_pair'] for m,r in summaries.items()},indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--references',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    summarize(a.inputs,a.references,a.out)
