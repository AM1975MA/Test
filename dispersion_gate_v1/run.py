"""No-fit causal selection between completed full and discarded95 LINEAR forecasts."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dispersion_gate_v1.gate import historical_dispersion,annual_gate
from paper_ltr_v1.learner import KEYS
from compact21_predictive_v2.metrics import evaluate

VARIANT='DISPERSION_SWITCH'
FULL_SHA='19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f'
RESIDUAL_SHA='3062665742eb0ce1423eebfed8c5821201ddb75f258937679256759b498015c5'
FP=('train_keys_sha256','subtrain_keys_sha256','validation_keys_sha256','train_matrix_sha256','train_labels_sha256')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def reference(root,expected,variant):
    root=Path(root);r=json.loads((root/'RESULT.json').read_text())
    if sha(root/'RESULT.json')!=expected or r['variant']!=variant or r['status']!='PAPER_LTR_V2_COMPLETE' or not r['ALL_MATURITY_PASS']:raise ValueError('Unverified completed source model')
    p=root/'NATIVE_PREDICTIONS.parquet'
    if sha(p)!=r['files_sha256'][p.name]:raise ValueError('Source forecasts changed')
    f=pd.read_parquet(p);f['signal_date']=pd.to_datetime(f.signal_date)
    return r,f.sort_values(['vintage',*KEYS]).reset_index(drop=True)

def raw_gates(raw,expected):
    from etf_trader.source_only.raw_io import load_ticker_csv_folder
    actual={p.name:sha(p) for p in sorted(Path(raw).glob('*.csv'))}
    if actual!=expected:raise ValueError('Frozen Yahoo source changed')
    mats,cats,_=load_ticker_csv_folder(raw,allow_missing=True)
    if len(cats)!=149:raise ValueError('Original149 required')
    history=historical_dispersion(mats['Close'])
    return pd.concat([annual_gate(history,y) for y in range(2017,2027)],ignore_index=True)

def combine(full,residual,gates):
    pd.testing.assert_frame_equal(full[['vintage',*KEYS]],residual[['vintage',*KEYS]],check_exact=True)
    for name in ('target_rank_21','exit_date_21','target_ret_21'):
        pd.testing.assert_series_equal(full[name],residual[name],check_names=False,check_exact=True)
    z=full.merge(gates[['vintage','signal_date','use_full']],on=['vintage','signal_date'],how='left',validate='many_to_one',sort=False)
    if z.use_full.isna().any() or len(z)!=len(full):raise ValueError('Incomplete regime coverage')
    pd.testing.assert_frame_equal(z[['vintage',*KEYS]],full[['vintage',*KEYS]],check_exact=True)
    z['pred']=np.where(z.use_full,full.pred,residual.pred)
    if not np.isfinite(z.pred).all():raise ValueError('Invalid switched predictions')
    return z.drop(columns='use_full')

def verify_switch(result,repeat,raw):
    """Independently rebuild gate from raw and reconstruct switches from pinned forecasts."""
    for p,digest in result['sources'].items():
        if sha(ROOT/p)!=digest:raise ValueError('Switch source changed')
    _,full=reference(result['references']['full'],FULL_SHA,'LINEAR_NUMERICAL_REPAIR')
    _,residual=reference(result['references']['residual'],RESIDUAL_SHA,'LINEAR_PCA_DISCARDED')
    gates=raw_gates(raw,result['raw_files_sha256'][str(repeat)]);gates['vintage']=repeat
    ix=full.vintage==repeat
    expected=combine(full[ix].reset_index(drop=True),residual[ix].reset_index(drop=True),gates)
    root=Path(result['out_dir']);path=root/'NATIVE_PREDICTIONS.parquet'
    if sha(path)!=result['files_sha256'][path.name]:raise ValueError('Switch artifact changed')
    actual=pd.read_parquet(path);actual=actual[actual.vintage==repeat].sort_values(['vintage',*KEYS]).reset_index(drop=True)
    pd.testing.assert_frame_equal(actual,expected,check_exact=True)
    return dict(PASS=True,raw_identity_PASS=True,causal_gate_PASS=True,source_forecast_reconstruction_PASS=True,new_fits_executed=0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--annual',required=True);ap.add_argument('--residual',required=True);ap.add_argument('--raw',required=True);ap.add_argument('--bases',required=True);ap.add_argument('--ti',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    from paper_ltr_v2.replay import verify_training_fingerprints
    annual,full=reference(a.annual,FULL_SHA,'LINEAR_NUMERICAL_REPAIR');residual,other=reference(a.residual,RESIDUAL_SHA,'LINEAR_PCA_DISCARDED')
    if annual['input_sha256']!=residual['input_sha256']:raise ValueError('Different frozen panels')
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new')
    out.mkdir(parents=True,exist_ok=True)
    tables=[];hashes={};training_checks={}
    for i in (1,2,3):
        contracts=list((Path(a.bases)/f'r{i}').rglob('INPUT_CONTRACT.json'))
        if len(contracts)!=1:raise ValueError('Ambiguous frozen raw contract')
        hashes[str(i)]=json.loads(contracts[0].read_text())['raw_files_sha256']
        gates=raw_gates(Path(a.raw)/f'_repeat{i}',hashes[str(i)]);gates['vintage']=i;tables.append(gates)
        path=Path(a.ti)/f'r{i}'/'TI_COMPACT.parquet'
        if sha(path)!=annual['input_sha256'][str(i)]:raise ValueError('TI reference changed')
        ti=pd.read_parquet(path)
        for c in ('signal_date','exit_date_21'):ti[c]=pd.to_datetime(ti[c])
        training_checks[str(i)]=[verify_training_fingerprints(r,ti,i) for r in (annual,residual)]
    gates=pd.concat(tables,ignore_index=True);candidate=combine(full,other,gates)
    candidate.to_parquet(out/'NATIVE_PREDICTIONS.parquet',index=False);gates.to_csv(out/'GATES.csv',index=False)
    per_year={}
    for y in range(2017,2027):
        transforms={}
        for i in (1,2,3):
            original=annual['per_year'][str(y)]['transforms'][str(i)];restricted=residual['per_year'][str(y)]['transforms'][str(i)]
            if any(original[k]!=restricted[k] for k in FP):raise ValueError('Source training policy differs')
            transforms[str(i)]={k:original[k] for k in FP}
            transforms[str(i)].update(kind='CAUSAL_SWITCH_OF_FROZEN_MODELS',new_seed_fits=0,reused_source_models=2)
        per_year[str(y)]=dict(transforms=transforms,maturity_PASS=True)
    r=dict(status='PAPER_LTR_V2_COMPLETE',variant=VARIANT,ALL_MATURITY_PASS=True,per_year=per_year,
        new_fits_executed=0,production_adoption=False,out_dir=str(out),input_sha256=annual['input_sha256'],raw_files_sha256=hashes,
        references=dict(full=a.annual,residual=a.residual,full_sha256=FULL_SHA,residual_sha256=RESIDUAL_SHA),
        sources={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')},
        protocol_sha256=sha(Path(__file__).with_name('PROTOCOL.md')),predictive=evaluate(candidate,quality_exit_cutoff='2026-07-01'),
        files_sha256={p.name:sha(p) for p in out.glob('*') if p.is_file()})
    # Conditional ranking diagnosis: same ex-ante queries for both fixed experts.
    conditional={}
    for low in (True,False):
        q=gates[gates.use_full.eq(not low)][['vintage','signal_date']]
        label='low' if low else 'high';conditional[label]={}
        for name,f in [('full',full),('residual',other)]:
            z=f.merge(q,on=['vintage','signal_date'],validate='many_to_one')
            ev=evaluate(z,quality_exit_cutoff='2026-07-01')
            conditional[label][name]=ev['aggregate_by_date']
            conditional[label]['mature_dates']=int(z[z.exit_date_21<='2026-07-01'].signal_date.nunique())
        conditional[label]['residual_minus_full']={k:conditional[label]['residual'][k]-conditional[label]['full'][k] for k in ('top1_realized_percentile','ndcg5','rank_ic','top1_realized_return')}
    pivot=gates.pivot(index='signal_date',columns='vintage',values='use_full')
    if pivot.isna().any().any():raise ValueError('Regime calendars differ')
    r['regime_diagnostics']=dict(full_fraction=float(gates.use_full.mean()),download_regime_any_disagreement=float((pivot.nunique(axis=1)>1).mean()),
        conditional_quality=conditional,interpretation='Descriptive; correlated vintages, no independent statistical confirmation')
    write(out/'RESULT.json',r)
    checks={str(i):verify_switch(r,i,Path(a.raw)/f'_repeat{i}') for i in (1,2,3)}
    write(out/'AUDIT.json',dict(all_PASS=True,records=checks,source_training_checks=training_checks,candidate_result_sha256=sha(out/'RESULT.json')))
    print(json.dumps(dict(status='DISPERSION_SWITCH_ZERO_FIT_COMPLETE',diagnostics=r['regime_diagnostics']),indent=2))

if __name__=='__main__':main()
