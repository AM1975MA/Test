#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, shutil
from pathlib import Path
import numpy as np
import pandas as pd


def load_module(path: Path):
    spec=importlib.util.spec_from_file_location('canonical_forensic_compare',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw',required=True); ap.add_argument('--compare-script',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); raw=Path(a.raw).resolve(); out=Path(a.out).resolve(); cmp=Path(a.compare_script).resolve()
    os.environ['FROZEN_149_ROOT']=str(raw.parent); os.environ['FROZEN_HOLDOUT70_ROOT']=str(raw.parent)
    mod=load_module(cmp); mod.FROZEN149=raw; mod.FROZEN70=raw; mod.OUT=out/'work'
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    u=mod.load_universe(raw)
    if len(u)!=149 or u.ticker.nunique()!=149: raise RuntimeError('unexpected universe')
    state=mod.build_source_only_state('original149',raw)
    replay=mod.replay_full_universe(state)
    panel=pd.read_pickle(state['ma3_panel_path']).copy()
    panel['signal_date']=pd.to_datetime(panel['signal_date'])
    panel.to_parquet(out/'RAW_FEATURE_PANEL.parquet',index=False)
    state['tit'].to_parquet(out/'TIT_R.parquet',index=False)
    pred=state['pred'].copy(); pred['signal_date']=pd.to_datetime(pred['signal_date']); pred.to_parquet(out/'PREDICTIONS.parquet',index=False)
    cal=state['tit'][['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    p=pred.rename(columns={'ET_TAIL':'ET_RANK','XGB_TAIL':'XGB_RANK'})
    score=mod.stage19.score_matrix(p,cal,state['candidate_tickers'])
    score_long=(pd.DataFrame(score,index=pd.DatetimeIndex(cal.signal_date),columns=state['candidate_tickers']).stack(dropna=False).rename('FINAL_SCORE').reset_index())
    score_long.columns=['signal_date','ticker','FINAL_SCORE']; score_long.to_parquet(out/'FINAL_SCORE.parquet',index=False)
    for fn in ['FULL_UNIVERSE_PATH.npz','DAILY_LEADERS.csv','RESULT.json','ENSEMBLE_FIT_AUDIT.csv']:
        src=state['base']/fn
        if src.exists(): shutil.copyfile(src,out/fn)
    inv={'panel_rows':len(panel),'panel_columns':list(panel.columns),'panel_dtypes':{c:str(panel[c].dtype) for c in panel.columns},'tit_rows':len(state['tit']),'prediction_rows':len(pred),'replay':replay}
    (out/'INVENTORY.json').write_text(json.dumps(inv,indent=2,default=str)+'\n')
    print(json.dumps({'status':'STAGE_DUMP_COMPLETE','out':str(out),'replay':replay},indent=2),flush=True)

if __name__=='__main__': main()
