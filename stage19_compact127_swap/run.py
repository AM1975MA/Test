#!/usr/bin/env python3
"""Isolated producer substitution: Compact21 XGBRanker(127) inside authentic V2 Stage19.

Re-use ORIGINAL full Stage19 engine, MA3 ET/XGB ensemble, Tail, V6, DD-first,
High-CAGR24, stops, commissions, universe and quotation vintage unchanged.
Only annual Compact21 forecasts are refitted with max_leaves=127.
The archived BASE must replay bit-identically before challenger replay.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from paper_ltr_v2.replay import (
    sha, verify_cache, load_compare, read_frame, replace_exact,
    assert_replay_parity, titanium_from_annual, write_state, one,
)
from etf_trader.source_only import kernel as k, models

def verify_frozen_panel(panel_path,repeat):
    bench=json.loads((ROOT/'compact21_learner_swap_v1/results/BENCHMARK.json').read_text())
    expected=bench['models']['BASE']['input_sha256'][str(repeat)]
    observed=sha(panel_path)
    if observed!=expected:raise RuntimeError(f'TI_COMPACT vintage hash mismatch r{repeat}: {observed} != {expected}')
    return dict(sha256=observed,canonical_benchmark_sha256=sha(ROOT/'compact21_learner_swap_v1/results/BENCHMARK.json'))

def annual_fit127(panel,annual,years=range(2017,2027)):
    features=k.F2D_FEATURES
    if len(features)!=125: raise RuntimeError(f'Expected 125 features, got {len(features)}')
    needed={'signal_date','ticker','target_rank_21','exit_date_21'}|set(features)
    if not needed.issubset(panel):raise RuntimeError('Missing features/labels: '+str(sorted(needed-set(panel))))
    if panel.duplicated(['signal_date','ticker']).any():raise RuntimeError('Duplicate panel rows')
    panel=panel.copy()
    panel['signal_date']=pd.to_datetime(panel.signal_date)
    panel['exit_date_21']=pd.to_datetime(panel.exit_date_21)
    out=[];audits=[]
    params=dict(k.COMPACT_PARAMS,max_depth=0,grow_policy='lossguide',max_leaves=127)
    if params.get('objective')!='rank:pairwise' or params.get('n_estimators')!=360:
        raise RuntimeError('Compact21 params not frozen')
    params['n_jobs']=2
    all_annual_keys=annual[['signal_date','ticker']].copy()
    all_annual_keys['signal_date']=pd.to_datetime(all_annual_keys.signal_date)
    if all_annual_keys.duplicated(['signal_date','ticker']).any():raise RuntimeError('Annual OOS duplicate keys')
    valid=panel[features].notna().sum(axis=1)>=30
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        train=panel.loc[
            valid & panel.signal_date.lt(cutoff) & panel.exit_date_21.lt(cutoff)
            & panel.target_rank_21.notna()
        ].sort_values(['signal_date','ticker'],kind='mergesort')
        test=panel.loc[valid & panel.signal_date.dt.year.eq(year)].sort_values(
            ['signal_date','ticker'],kind='mergesort')
        if train.signal_date.nunique()<60 or len(test)==0:
            raise RuntimeError(f'Missing train/test 127 fold year={year}')
        if not train.exit_date_21.max()<cutoff:raise RuntimeError('Immature labels')
        y=(train.target_rank_21*100).round().astype(int)
        groups=train.groupby('signal_date',sort=True).size().to_numpy()
        if groups.sum()!=len(train):raise RuntimeError('Bad query groups')
        xtr=train[features].replace([np.inf,-np.inf],np.nan)
        xte=test[features].replace([np.inf,-np.inf],np.nan)
        pred=[]
        for seed in k.COMPACT_SEEDS:
            model=XGBRanker(**params,random_state=seed)
            model.fit(xtr,y,group=groups,verbose=False)
            pp=model.predict(xte)
            if not np.isfinite(pp).all():raise RuntimeError(f'Non-finite 127 prediction {year}/{seed}')
            pred.append(pp)
        e=test[['signal_date','ticker']].copy()
        e['new_compact21']=np.mean(pred,axis=0)
        out.append(e)
        audits.append(dict(year=year,fit_cutoff=str(cutoff.date()),train_months=int(train.signal_date.nunique()),
            train_rows=len(train),test_rows=len(test),label_maturity_max=str(train.exit_date_21.max().date()),
            min_test_date=str(test.signal_date.min().date()),
            max_test_date=str(test.signal_date.max().date()),
            features=len(features),seeds=k.COMPACT_SEEDS,config=params))
        print('FIT127_DONE',year,'train',len(train),'test',len(test),flush=True)
    predictions=pd.concat(out,ignore_index=True)
    keys=['signal_date','ticker']
    a=all_annual_keys.sort_values(keys,kind='mergesort').reset_index(drop=True)
    b=predictions[keys].sort_values(keys,kind='mergesort').reset_index(drop=True)
    if not a.equals(b):raise RuntimeError(f'Compact127 does not cover same OOS rows: {len(a)} vs {len(b)}')
    return predictions,audits

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw',required=True)
    ap.add_argument('--baseline',required=True)
    ap.add_argument('--ti-panel',required=True)
    ap.add_argument('--repeat',required=True,type=int,choices=(1,2,3))
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    raw=Path(args.raw).resolve();cache=Path(args.baseline).resolve()
    out=Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):raise RuntimeError('Output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    original,contract,evidence,cache_gate=verify_cache(cache,raw)
    frozen_panel=verify_frozen_panel(args.ti_panel,args.repeat)
    compare=load_compare(raw)
    tickers=compare.load_universe(raw).ticker.tolist()
    if len(tickers)!=149:raise RuntimeError('Universe is not original 149')
    annual=read_frame(evidence/'ANNUAL_PREDICTIONS.csv')
    tit=read_frame(evidence/'TIT_R_SOURCE_ONLY.csv')
    ensemble=read_frame(evidence/'ENSEMBLE_TAIL_OOS.csv')
    panel=pd.read_parquet(args.ti_panel)
    for field in ('signal_date','exit_date_21'):
        panel[field]=pd.to_datetime(panel[field])
    if len(annual)!=len(tit) or len(annual)!=len(ensemble):
        raise RuntimeError('Original cache unexpected prediction cardinality')
    # Reproduction of original Titan annual -> TIT_R, then complete Stage19 path.
    recomputed=titanium_from_annual(annual,models)
    parity_tit=replace_exact(tit,recomputed,'TIT_R','TIT_R')
    if not np.allclose(tit.TIT_R.to_numpy(),parity_tit.TIT_R.to_numpy(),
                       rtol=0,atol=1e-12):raise RuntimeError('Original TIT_R cannot be rebuilt')
    bstate=write_state(out/'baseline_control',raw,tickers,tit,ensemble,Path(args.ti_panel))
    base_result=compare.replay_full_universe(bstate)
    gate=assert_replay_parity(base_result,original,
       bstate['base']/'FULL_UNIVERSE_PATH.npz',evidence/'FULL_UNIVERSE_PATH.npz',
       bstate['base']/'DAILY_LEADERS.csv',one(cache,'DAILY_LEADERS_BASE.csv'))
    print('TRUE_BASE_STAGE19_PARITY_PASS',args.repeat,base_result['v2_full_universe'],flush=True)

    new_predict,fit_audit=annual_fit127(panel,annual)
    challenger_annual=replace_exact(annual,new_predict,'compact21','new_compact21')
    pd.testing.assert_frame_equal(annual.drop(columns='compact21'),
                                  challenger_annual.drop(columns='compact21'),check_exact=True)
    challenger_tit=titanium_from_annual(challenger_annual,models)
    rep=challenger_tit[['signal_date','ticker','TIT_R']]
    challenger_ensemble=replace_exact(ensemble,rep,'BASE','TIT_R')
    pd.testing.assert_frame_equal(ensemble.drop(columns='BASE'),
                                  challenger_ensemble.drop(columns='BASE'),check_exact=True)
    state=write_state(out/'challenger_compact127',raw,tickers,challenger_tit,challenger_ensemble,
                      Path(args.ti_panel))
    candidate_metrics=compare.replay_full_universe(state)
    print('TRUE_STAGE19_COMPACT127_RESULT',args.repeat,candidate_metrics['v2_full_universe'],flush=True)
    challenger_annual.to_csv(out/'challenger_annual_predictions.csv',index=False)
    # Not independent: two candidate decisions are descendants of a changed producer.
    with np.load(bstate['base']/'FULL_UNIVERSE_PATH.npz') as bp, np.load(state['base']/'FULL_UNIVERSE_PATH.npz') as cp:
        bd=pd.DatetimeIndex(pd.to_datetime(bp['dates']))
        cd=pd.DatetimeIndex(pd.to_datetime(cp['dates']))
        if not bd.equals(cd):raise RuntimeError('Stage19 trading calendars differ')
        beq=np.array(bp['equity'],float)[0];ceq=np.array(cp['equity'],float)[0]
        topret=float(np.mean(bp['d1']!=cp['d1']))
        nav=pd.DataFrame({'date':bd,'baseline':beq,'challenger_compact127':ceq})
        nav.to_csv(out/'PAIRED_DAILY_NAV.csv',index=False)
        base_log=np.diff(np.log(np.r_[1.,beq]));challenger_log=np.diff(np.log(np.r_[1.,ceq]))
        delta=challenger_log-base_log
        period={}
        for p,s,e in [('full','2017-02-01','2026-07-01'),
                      ('dev_2017_2022','2017-02-01','2022-12-31'),
                      ('retrospective_2023_2026','2023-01-01','2026-07-01')]:
            ix=(bd>=pd.Timestamp(s))&(bd<=pd.Timestamp(e))
            if not ix.any():continue
            n=int(ix.sum())
            period[p]={'n_sessions':n,
                'baseline_cagr':float(np.expm1(base_log[ix].sum()*252/n)),
                'candidate_cagr':float(np.expm1(challenger_log[ix].sum()*252/n)),
                'paired_log_annual_delta':float(delta[ix].sum()*252/n)}
    record={'status':'TRUE_BASE_PARITY_PASS_AND_ISOLATED_COMPACT127_DONE',
       'model_change':'Compact21 125f depth-wise max_depth=4 to lossguide max_leaves=127, 360 trees, three seeds. No other model fitted.',
       'original_base':base_result['v2_full_universe'],
       'challenger':candidate_metrics['v2_full_universe'],
       'delta_cagr_pp':100*(candidate_metrics['v2_full_universe']['cagr']-base_result['v2_full_universe']['cagr']),
       'delta_maxdd_pp':100*(candidate_metrics['v2_full_universe']['maxdd']-base_result['v2_full_universe']['maxdd']),
       'reference_vintage':args.repeat,'source_only_raw_vintage_hash':contract.get('raw_files_sha256'),
       'original_score_manifest_hash':sha(evidence/'ANNUAL_PREDICTIONS.csv'),
       'baseline_parity_gate':gate,'panel_sha_gate':frozen_panel,
       'original_ensemble_columns_unchanged_except_BASE':True,
       'original_annual_columns_unchanged_except_compact21':True,
       'original_risk_v6_engine_unchanged':True,
       'xgb127_fit_audit':fit_audit,'fraction_daily_top1_changed':topret,
       'per_period':period,
       'same_price_vintage_and_calendar':True,
       'historical_selection_warning':'Original period historically inspected; no prospective OOS promotion.'}
    (out/'RESULT.json').write_text(json.dumps(record,indent=2,default=str))
    print('FINISHED_STAGE19_PRODUCER_SWAP',json.dumps({k:record[k] for k in
        ('reference_vintage','original_base','challenger','delta_cagr_pp','delta_maxdd_pp',
        'fraction_daily_top1_changed','per_period')},default=str),flush=True)

if __name__=='__main__':main()
