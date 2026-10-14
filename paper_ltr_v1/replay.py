"""Replay canonico da cache verificata: cambia soltanto Compact21, senza fit."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
KEYS=['signal_date','ticker']

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def one(root,name):
    direct=Path(root)/name
    if direct.is_file():return direct
    paths=list(Path(root).rglob(name))
    if len(paths)!=1:raise ValueError(f'Cache ambigua o incompleta: {name}: {paths}')
    return paths[0]

def read_frame(path):
    f=pd.read_csv(path,float_precision='round_trip')
    for name in ('signal_date','entry_date','exit_date'):
        if name in f:f[name]=pd.to_datetime(f[name])
    return f

def replace_exact(frame, replacement, column, value_column):
    """Richiede identico insieme di chiavi; preserva ordine e altre colonne."""
    if frame[KEYS].isna().any().any() or replacement[KEYS].isna().any().any():raise ValueError('Chiavi mancanti')
    if frame.duplicated(KEYS).any() or replacement.duplicated(KEYS).any():raise ValueError('Chiavi duplicate')
    old=frame[KEYS].sort_values(KEYS).reset_index(drop=True)
    new=replacement[KEYS].sort_values(KEYS).reset_index(drop=True)
    if not old.equals(new):raise ValueError('Copertura chiavi diversa: nessuna approssimazione ammessa')
    values=frame[KEYS].merge(replacement[KEYS+[value_column]],on=KEYS,how='left',validate='one_to_one')[value_column].to_numpy(float)
    if not np.isfinite(values).all():raise ValueError('Score non finiti')
    result=frame.copy();result[column]=values
    pd.testing.assert_frame_equal(frame.drop(columns=column),result.drop(columns=column),check_exact=True)
    return result

def verify_cache(cache,raw):
    result_path=one(cache,'RESULT_BASE.json');contract_path=one(cache,'INPUT_CONTRACT.json')
    result=json.loads(result_path.read_text());contract=json.loads(contract_path.read_text())
    actual={p.name:sha(p) for p in sorted(Path(raw).glob('*.csv'))}
    if not actual or actual!=contract.get('raw_files_sha256'):raise ValueError('Hash raw diversi dalla baseline congelata')
    evidence=one(cache,'ANNUAL_PREDICTIONS.csv').parent
    expected=result.get('evidence_files_sha256',{})
    if not expected:raise ValueError('Manifest hash cache assente')
    checked={}
    for relative,digest in expected.items():
        path=evidence/relative
        if not path.is_file() or sha(path)!=digest:raise ValueError(f'Cache modificata o mancante: {relative}')
        checked[relative]=digest
    for key,path in [('canonical_models_sha256',ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only/models.py'),
                     ('canonical_compare_sha256',ROOT/'holdout70/v2_canonical_same_source_compare.py')]:
        if sha(path)!=contract.get(key):raise ValueError(f'Fonte canonica baseline diversa: {key}')
    for relative,expected_digest in contract.get('ma3_reference_contract',{}).get('canonical_sources_sha256',{}).items():
        if sha(ROOT/relative)!=expected_digest:raise ValueError(f'Fonte canonica diversa: {relative}')
    return result,contract,evidence,dict(raw_identity_PASS=True,cache_identity_PASS=True,
        raw_files_sha256=actual,verified_cache_files_sha256=checked,
        baseline_result_sha256=sha(result_path),baseline_input_contract_sha256=sha(contract_path))

def assert_replay_parity(result,reference,actual_npz,expected_npz,actual_leaders,expected_leaders):
    fields=('candidate_count','sessions','start','end','completed_signals')
    if any(result[k]!=reference[k] for k in fields):raise ValueError('Calendario/universo replay BASE diverso')
    differences={}
    for scope in ('v2_full_universe','equal_weight_buy_hold'):
        for field,value in reference[scope].items():
            delta=abs(float(result[scope][field])-float(value));differences[f'{scope}.{field}']=delta
            if delta>1e-12:raise ValueError(f'Parità metriche BASE fallita: {scope}.{field} delta={delta}')
    arrays={}
    with np.load(actual_npz) as actual,np.load(expected_npz) as expected:
        if set(actual.files)!=set(expected.files):raise ValueError('Schema NPZ baseline diverso')
        for key in expected.files:
            a,b=actual[key],expected[key]
            if a.shape!=b.shape or a.dtype!=b.dtype:raise ValueError(f'Schema array BASE diverso: {key}')
            if np.issubdtype(a.dtype,np.floating):
                if not np.allclose(a,b,rtol=0,atol=1e-12,equal_nan=True):raise ValueError(f'Percorso BASE diverso: {key}')
                arrays[key]=float(np.nanmax(np.abs(a-b)))
            else:
                if not np.array_equal(a,b):raise ValueError(f'Array BASE diverso: {key}')
                arrays[key]=0.
    pd.testing.assert_frame_equal(pd.read_csv(actual_leaders),pd.read_csv(expected_leaders),check_exact=True)
    return dict(PASS=True,absolute_tolerance=1e-12,metric_max_abs=differences,npz_max_abs=arrays,daily_leaders_exact=True)

def load_compare(raw):
    os.environ['FROZEN_149_ROOT']=str(raw.parent);os.environ['FROZEN_HOLDOUT70_ROOT']=str(raw.parent)
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
    path=ROOT/'holdout70/v2_canonical_same_source_compare.py'
    spec=importlib.util.spec_from_file_location('paper_ltr_canonical_replay',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.FROZEN149=raw;module.FROZEN70=raw
    return module

def titanium_from_annual(annual,models):
    scores=models.variants(annual)['baseline'].rename(columns={'score':'TIT_R'})
    calendar=annual[KEYS+['entry_date','exit_date']].drop_duplicates(KEYS)
    return scores.merge(calendar,on=KEYS,validate='one_to_one')[['signal_date','entry_date','exit_date','ticker','TIT_R']].sort_values(KEYS).reset_index(drop=True)

def write_state(out,raw,tickers,tit,ensemble,panel_path):
    out.mkdir(parents=True,exist_ok=True)
    tit_path=out/'TIT_R_SOURCE_ONLY.csv';candidate_path=out/'TIT_R_CANDIDATES_ONLY.csv';pred_path=out/'ENSEMBLE_TAIL_OOS.csv'
    tit.to_csv(tit_path,index=False);candidate=tit[tit.ticker.isin(tickers)].copy();candidate.to_csv(candidate_path,index=False)
    ensemble.to_csv(pred_path,index=False)
    return dict(base=out,candidate_raw=raw,titanium_raw=raw,candidate_tickers=tickers,tit=candidate,
        tit_full_path=tit_path,tit_candidate_path=candidate_path,pred=ensemble,pred_path=pred_path,ma3_panel_path=panel_path)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',required=True);ap.add_argument('--baseline',required=True)
    ap.add_argument('--candidate',required=True,help='Directory artifact con NATIVE_PREDICTIONS.parquet e RESULT.json')
    ap.add_argument('--repeat',required=True,type=int,choices=[1,2,3]);ap.add_argument('--out',required=True)
    a=ap.parse_args();raw=Path(a.raw).resolve();cache=Path(a.baseline).resolve();out=Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Output deve essere nuovo')
    out.mkdir(parents=True,exist_ok=True)
    baseline,contract,evidence,audit=verify_cache(cache,raw)
    candidate_path=one(a.candidate,'NATIVE_PREDICTIONS.parquet');candidate_result=json.loads(one(a.candidate,'RESULT.json').read_text())
    if (candidate_result.get('status')!='PAPER_LTR_V1_COMPLETE'
        or candidate_result.get('variant')!='LISTNET_DECILE_64'
        or candidate_result.get('ALL_MATURITY_PASS') is not True):raise ValueError('Fit candidato incompleto o contratto diverso')
    if set(candidate_result.get('per_year',{}))!=set(map(str,range(2017,2027))):raise ValueError('Fold candidato incompleti')
    expected_candidate_hash=candidate_result.get('files_sha256',{}).get('NATIVE_PREDICTIONS.parquet')
    if not expected_candidate_hash or sha(candidate_path)!=expected_candidate_hash:raise ValueError('Hash previsioni candidato diverso dal manifest')
    candidate=pd.read_parquet(candidate_path);candidate=candidate[candidate.vintage.eq(a.repeat)].copy()
    candidate.signal_date=pd.to_datetime(candidate.signal_date)
    compare=load_compare(raw)
    from etf_trader.source_only import models
    tickers=compare.load_universe(raw).ticker.tolist()
    if len(tickers)!=149:raise ValueError('Universo deve essere Original149')
    annual=read_frame(evidence/'ANNUAL_PREDICTIONS.csv');tit=read_frame(evidence/'TIT_R_SOURCE_ONLY.csv')
    ensemble=read_frame(evidence/'ENSEMBLE_TAIL_OOS.csv');panel_path=one(cache,'RAW_FEATURE_PANEL.pkl')
    fit_audit=read_frame(evidence/'ENSEMBLE_FIT_AUDIT.csv')
    if 'maturity_ok' not in fit_audit or not fit_audit.maturity_ok.all():raise ValueError('Maturazione MA3 cache fallita')
    recomputed=titanium_from_annual(annual,models)
    aligned=replace_exact(tit,recomputed,'TIT_R','TIT_R')
    if not np.allclose(tit.TIT_R,aligned.TIT_R,rtol=0,atol=1e-12):raise ValueError('TIT_R baseline non ricostruibile da cache annuale')
    # Prima di utilizzare il candidato, il replay immutato deve riprodurre ogni percorso.
    base_state=write_state(out/'baseline_control',raw,tickers,tit,ensemble,panel_path)
    base_result=compare.replay_full_universe(base_state)
    audit['baseline_replay']=assert_replay_parity(base_result,baseline,
        base_state['base']/'FULL_UNIVERSE_PATH.npz',evidence/'FULL_UNIVERSE_PATH.npz',
        base_state['base']/'DAILY_LEADERS.csv',one(cache,'DAILY_LEADERS_BASE.csv'))
    base_result['source_only'].update(historical_scores_consumed=True,cached_unchanged_models_used=True,
        historical_paths_consumed=False,historical_paths_used_for_certification_only=True,new_fits_executed=0)
    (base_state['base']/'RESULT.json').write_text(json.dumps(base_result,indent=2,allow_nan=False)+'\n')
    candidate_annual=replace_exact(annual,candidate,'compact21','pred')
    candidate_tit=titanium_from_annual(candidate_annual,models)
    replacement=candidate_tit[candidate_tit.ticker.isin(tickers)][KEYS+['TIT_R']]
    candidate_ensemble=replace_exact(ensemble,replacement,'BASE','TIT_R')
    pd.testing.assert_frame_equal(ensemble.drop(columns='BASE'),candidate_ensemble.drop(columns='BASE'),check_exact=True)
    state=write_state(out/'candidate',raw,tickers,candidate_tit,candidate_ensemble,panel_path)
    candidate_annual.to_csv(state['base']/'ANNUAL_PREDICTIONS.csv',index=False)
    candidate_metrics=compare.replay_full_universe(state)
    candidate_metrics['source_only'].update(historical_scores_consumed=True,cached_unchanged_models_used=True,
        historical_paths_consumed=False,historical_paths_used_for_certification_only=True,new_fits_executed=0)
    (state['base']/'RESULT.json').write_text(json.dumps(candidate_metrics,indent=2,allow_nan=False)+'\n')
    audit.update(candidate_predictions_sha256=sha(candidate_path),candidate_result_sha256=sha(one(a.candidate,'RESULT.json')),
        candidate_repeat=a.repeat,annual_rows=len(annual),ensemble_rows=len(ensemble),candidate_keys_exact_PASS=True,
        annual_columns_unchanged_except_compact21=True,ensemble_columns_unchanged_except_BASE=True,
        new_fits_executed=0,other_models_reused_unchanged=True,negative_feedback_changed=False,
        canonical_compare_sha256=sha(ROOT/'holdout70/v2_canonical_same_source_compare.py'),
        canonical_models_sha256=sha(ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only/models.py'),
        ma3_panel_sha256=sha(panel_path))
    audit['ensemble_unchanged_columns_sha256']=hashlib.sha256(ensemble.drop(columns='BASE').to_csv(index=False,lineterminator='\n').encode()).hexdigest()
    audit['candidate_ensemble_unchanged_columns_sha256']=hashlib.sha256(candidate_ensemble.drop(columns='BASE').to_csv(index=False,lineterminator='\n').encode()).hexdigest()
    result=dict(status='PAPER_LTR_CACHE_REPLAY_COMPLETE',repeat=a.repeat,baseline=base_result,
        candidate=candidate_metrics,audit=audit,production_adoption=False)
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(repeat=a.repeat,baseline=base_result['v2_full_universe'],candidate=candidate_metrics['v2_full_universe']),indent=2),flush=True)

if __name__=='__main__':main()
