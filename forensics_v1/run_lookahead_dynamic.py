#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, shutil
from pathlib import Path
import numpy as np
import pandas as pd


def load_module(path: Path, tag: str):
    sp=importlib.util.spec_from_file_location('lookahead_'+tag,path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def copy_variant(src:Path,dst:Path,cutoff:pd.Timestamp,mode:str):
    if dst.exists():shutil.rmtree(dst)
    dst.mkdir(parents=True)
    shutil.copyfile(src/'universe.csv',dst/'universe.csv')
    tickers=pd.read_csv(src/'universe.csv').ticker.astype(str).tolist()
    for ti,t in enumerate(tickers):
        d=pd.read_csv(src/f'{t}.csv'); dates=pd.to_datetime(d['date'])
        if mode=='truncate':
            d=d.loc[dates<=cutoff].copy()
        elif mode=='mutate':
            m=dates>cutoff
            if m.any():
                idx=np.arange(len(d),dtype=float)
                # large deterministic future-only perturbation; same positive factor for OHLC preserves bar geometry.
                fac=1.0 + 0.20*np.sin(0.173*idx + 0.071*ti) + 0.08*np.cos(0.037*idx + 0.113*ti)
                fac=np.clip(fac,0.60,1.40)
                for c in ['Open','High','Low','Close']:
                    d.loc[m,c]=pd.to_numeric(d.loc[m,c],errors='coerce').to_numpy(float)*fac[m.to_numpy()]
                d.loc[m,'Volume']=np.maximum(1,np.round(pd.to_numeric(d.loc[m,'Volume'],errors='coerce').to_numpy(float)*(1.0+0.35*np.sin(0.051*idx[m.to_numpy()]+ti)))).astype('int64')
        else: raise ValueError(mode)
        d.to_csv(dst/f'{t}.csv',index=False)


def build_state(compare_script:Path, raw:Path, outroot:Path, tag:str):
    os.environ['FROZEN_149_ROOT']=str(raw.parent);os.environ['FROZEN_HOLDOUT70_ROOT']=str(raw.parent)
    mod=load_module(compare_script,tag);mod.FROZEN149=raw;mod.FROZEN70=raw;mod.OUT=outroot
    s=mod.build_source_only_state(tag,raw)
    p=s['pred'].rename(columns={'ET_TAIL':'ET_RANK','XGB_TAIL':'XGB_RANK'}).copy()
    cal=s['tit'][['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    sc=mod.stage19.score_matrix(p,cal,s['candidate_tickers'])
    score=(pd.DataFrame(sc,index=pd.DatetimeIndex(cal.signal_date),columns=s['candidate_tickers']).stack(dropna=False).rename('FINAL_SCORE').reset_index());score.columns=['signal_date','ticker','FINAL_SCORE']
    return {'tit':s['tit'].copy(),'pred':s['pred'].copy(),'score':score,'panel':pd.read_pickle(s['ma3_panel_path']).copy(),'fit_audit':pd.read_csv(s['base']/'ENSEMBLE_FIT_AUDIT.csv')}


def compare(base,other,cutoff):
    result={}
    for name,col in [('tit','TIT_R'),('score','FINAL_SCORE')]:
        A=base[name].copy();B=other[name].copy();A['signal_date']=pd.to_datetime(A.signal_date);B['signal_date']=pd.to_datetime(B.signal_date)
        A=A[A.signal_date<=cutoff];B=B[B.signal_date<=cutoff]
        x=A[['signal_date','ticker',col]].merge(B[['signal_date','ticker',col]],on=['signal_date','ticker'],suffixes=('_a','_b'))
        u=x[col+'_a'].to_numpy(float);v=x[col+'_b'].to_numpy(float);m=np.isfinite(u)&np.isfinite(v);d=np.abs(u-v)
        result[name]={'n_common':int(m.sum()),'max_abs':float(np.nanmax(d[m])) if m.any() else None,'changed_gt1e12':int(np.sum(m&(d>1e-12))),'exact_pass':bool(not np.any(m&(d>1e-12)))}
    A=base['pred'].copy();B=other['pred'].copy();A.signal_date=pd.to_datetime(A.signal_date);B.signal_date=pd.to_datetime(B.signal_date);A=A[A.signal_date<=cutoff];B=B[B.signal_date<=cutoff]
    x=A.merge(B,on=['signal_date','ticker'],suffixes=('_a','_b'))
    result['predictions']={}
    for col in ['ET_TAIL','XGB_TAIL','TAIL_HYBRID']:
        u=x[col+'_a'].to_numpy(float);v=x[col+'_b'].to_numpy(float);m=np.isfinite(u)&np.isfinite(v);d=np.abs(u-v)
        result['predictions'][col]={'n_common':int(m.sum()),'max_abs':float(np.nanmax(d[m])) if m.any() else None,'changed_gt1e12':int(np.sum(m&(d>1e-12))),'exact_pass':bool(not np.any(m&(d>1e-12)))}
    # maturity audit must be strictly prior to annual cutoff
    fa=other['fit_audit'].copy(); fa['max_train_exit63']=pd.to_datetime(fa['max_train_exit63']);fa['cutoff']=pd.to_datetime(fa['cutoff'])
    result['maturity_gate']={'rows':len(fa),'violations':int((fa.max_train_exit63>=fa.cutoff).sum()),'PASS':bool((fa.max_train_exit63<fa.cutoff).all())}
    result['PASS']=bool(result['tit']['exact_pass'] and result['score']['exact_pass'] and all(v['exact_pass'] for v in result['predictions'].values()) and result['maturity_gate']['PASS'])
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--compare-script',required=True);ap.add_argument('--cutoff',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=Path(a.raw).resolve(); cmp=Path(a.compare_script).resolve(); cutoff=pd.Timestamp(a.cutoff); out=Path(a.out).resolve();
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True); variants=out/'variants';variants.mkdir()
    mut=variants/'mutated';trunc=variants/'truncated';copy_variant(raw,mut,cutoff,'mutate');copy_variant(raw,trunc,cutoff,'truncate')
    base=build_state(cmp,raw,out/'base_work','base');m=build_state(cmp,mut,out/'mut_work','mut');t=build_state(cmp,trunc,out/'trunc_work','trunc')
    res={'status':'LOOKAHEAD_DYNAMIC_COMPLETE','cutoff':str(cutoff.date()),'future_mutation':compare(base,m,cutoff),'truncation':compare(base,t,cutoff)}
    res['PASS']=bool(res['future_mutation']['PASS'] and res['truncation']['PASS'])
    (out/'RESULT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2),flush=True)
if __name__=='__main__':main()
