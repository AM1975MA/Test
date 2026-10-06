#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def cmp_numeric(A,B,keys,cols):
    x=A[keys+cols].merge(B[keys+cols],on=keys,suffixes=('_a','_b'),how='inner');out={}
    for c in cols:
        u=pd.to_numeric(x[c+'_a'],errors='coerce').to_numpy(float);v=pd.to_numeric(x[c+'_b'],errors='coerce').to_numpy(float);m=np.isfinite(u)&np.isfinite(v);d=np.abs(u-v);n=max(int(m.sum()),1)
        out[c]={'n':int(m.sum()),'changed_fraction_gt1e12':float(np.sum(m&(d>1e-12))/n),'mean_abs':float(np.nanmean(d[m])) if m.any() else None,'p99_abs':float(np.nanquantile(d[m],.99)) if m.any() else None,'max_abs':float(np.nanmax(d[m])) if m.any() else None}
    return out

def aggregate(d):
    z=[v for v in d.values() if v['mean_abs'] is not None]
    return {'columns':len(z),'mean_cell_changed_fraction':float(np.mean([v['changed_fraction_gt1e12'] for v in z])) if z else None,'mean_column_mean_abs':float(np.mean([v['mean_abs'] for v in z])) if z else None,'max_column_max_abs':float(np.max([v['max_abs'] for v in z])) if z else None}

def load(r):
    return {'compact':pd.read_parquet(r/'TI_COMPACT.parquet'),'tail':pd.read_parquet(r/'TI_TAIL.parquet'),'macro':pd.read_parquet(r/'TI_MACRO.parquet'),'extra':pd.read_parquet(r/'TI_EXTRA.parquet'),'scores':pd.read_parquet(r/'TI_MODEL_RAW_SCORES.parquet'),'tit':pd.read_parquet(r/'TIT_R.parquet'),'meta':json.loads((r/'TI_INPUT_META.json').read_text())}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.root);R={i:load(root/f'repeat{i}') for i in [1,2,3]};res={'status':'TITANIUM_INTERNAL_COMPARISON_COMPLETE','pairs':{}}
    for aa,bb in [(1,2),(1,3),(2,3)]:
        A,B=R[aa],R[bb];m=A['meta'];q={}
        f2d=[c for c in m['F2D_FEATURES'] if c in A['compact'].columns and c in B['compact'].columns];d=cmp_numeric(A['compact'],B['compact'],['signal_date','ticker'],f2d);q['compact_features']={'aggregate':aggregate(d),'per_column':d}
        clabs=[c for c in ['target_rank_pct','target_rank_21','target_rank_63','fwd_ret_21','fwd_ret_63'] if c in A['compact'].columns];d=cmp_numeric(A['compact'],B['compact'],['signal_date','ticker'],clabs);q['compact_labels']={'aggregate':aggregate(d),'per_column':d}
        tf=[c for c in m['TAIL_FEATURES'] if c in A['tail'].columns and c in B['tail'].columns];d=cmp_numeric(A['tail'],B['tail'],['signal_date','ticker'],tf);q['tail_features']={'aggregate':aggregate(d),'per_column':d}
        tl=[c for c in ['y_tailmix','target_rank_21','target_rank_42','target_rank_63','fwd_ret_21','fwd_ret_42','fwd_ret_63'] if c in A['tail'].columns];d=cmp_numeric(A['tail'],B['tail'],['signal_date','ticker'],tl);q['tail_labels']={'aggregate':aggregate(d),'per_column':d}
        mf=[c for c in m['macro_features'] if c in A['macro'].columns and c in B['macro'].columns];d=cmp_numeric(A['macro'],B['macro'],['signal_date','macro_category'],mf);q['macro_features']={'aggregate':aggregate(d),'per_column':d}
        ml=[c for c in ['target_rank','label_exit_date_63'] if c in A['macro'].columns and c in B['macro'].columns and c!='label_exit_date_63'];d=cmp_numeric(A['macro'],B['macro'],['signal_date','macro_category'],ml);q['macro_labels']={'aggregate':aggregate(d),'per_column':d}
        score_cols=[c for c in A['scores'].columns if c in B['scores'].columns and c not in ['signal_date','ticker','entry_date','exit_date','macro_category','top_macro','fit_year'] and pd.api.types.is_numeric_dtype(A['scores'][c])]
        d=cmp_numeric(A['scores'],B['scores'],['signal_date','ticker'],score_cols);q['raw_model_outputs']={'aggregate':aggregate(d),'per_column':d}
        td=cmp_numeric(A['tit'],B['tit'],['signal_date','ticker'],['TIT_R']);q['TIT_R']={'aggregate':aggregate(td),'per_column':td}
        res['pairs'][f'{aa}-{bb}']=q
    Path(a.out).write_text(json.dumps(res,indent=2,default=str)+'\n');print(json.dumps(res,indent=2)[:30000])
if __name__=='__main__':main()
