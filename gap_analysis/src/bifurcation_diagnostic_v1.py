#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


def _jsonable(v):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v)
    if isinstance(v, (pd.Timestamp, np.datetime64)): return str(pd.Timestamp(v))
    if isinstance(v, (np.bool_,)): return bool(v)
    return v


def load_csv(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path)
    date_col = next((c for c in x.columns if c.lower() in ('date','datetime','timestamp')), None)
    if date_col:
        x[date_col] = pd.to_datetime(x[date_col], errors='coerce')
        x = x.sort_values(date_col).reset_index(drop=True)
    return x


def raw_pair_summary(a: Path, b: Path, tickers: list[str]) -> dict:
    out = {
        'pair': [a.name, b.name],
        'tickers_checked': len(tickers),
        'shape_or_date_mismatch_tickers': [],
        'max_abs_return_diff': 0.0,
        'max_abs_return_diff_where': None,
        'max_rel_ohlc_diff': 0.0,
        'max_rel_ohlc_diff_where': None,
        'ticker_max_return_diffs': [],
    }
    ticker_rows=[]
    for t in tickers:
        xa, xb = load_csv(a/f'{t}.csv'), load_csv(b/f'{t}.csv')
        dc = next((c for c in xa.columns if c.lower() in ('date','datetime','timestamp')), None)
        if len(xa)!=len(xb) or dc is None or dc not in xb.columns or not xa[dc].equals(xb[dc]):
            out['shape_or_date_mismatch_tickers'].append(t)
            continue
        row={'ticker':t,'max_abs_return_diff':0.0,'max_rel_ohlc_diff':0.0}
        if 'Close' in xa.columns and 'Close' in xb.columns:
            ra=pd.to_numeric(xa['Close'],errors='coerce').pct_change()
            rb=pd.to_numeric(xb['Close'],errors='coerce').pct_change()
            d=(ra-rb).abs()
            if d.notna().any():
                m=float(d.max()); j=int(d.idxmax())
                row['max_abs_return_diff']=m
                if m>out['max_abs_return_diff']:
                    out['max_abs_return_diff']=m
                    out['max_abs_return_diff_where']={'ticker':t,'date':str(xa.loc[j,dc].date()),'return_a':float(ra.iloc[j]),'return_b':float(rb.iloc[j])}
        for fld in ('Open','High','Low','Close'):
            if fld not in xa.columns or fld not in xb.columns: continue
            va=pd.to_numeric(xa[fld],errors='coerce').to_numpy(float)
            vb=pd.to_numeric(xb[fld],errors='coerce').to_numpy(float)
            den=np.maximum(np.maximum(np.abs(va),np.abs(vb)),1e-300)
            rel=np.abs(va-vb)/den
            if np.isfinite(rel).any():
                m=float(np.nanmax(rel)); j=int(np.nanargmax(rel))
                row['max_rel_ohlc_diff']=max(row['max_rel_ohlc_diff'],m)
                if m>out['max_rel_ohlc_diff']:
                    out['max_rel_ohlc_diff']=m
                    out['max_rel_ohlc_diff_where']={'ticker':t,'date':str(xa.loc[j,dc].date()),'field':fld,'a':float(va[j]),'b':float(vb[j])}
        ticker_rows.append(row)
    out['ticker_max_return_diffs']=sorted(ticker_rows,key=lambda z:z['max_abs_return_diff'],reverse=True)[:20]
    return out


def frame_diff(a: pd.DataFrame, b: pd.DataFrame, name: str) -> dict:
    out={'name':name,'shape_a':list(a.shape),'shape_b':list(b.shape),'columns_equal':list(a.columns)==list(b.columns)}
    if a.shape!=b.shape or list(a.columns)!=list(b.columns):
        return out
    num=[c for c in a.columns if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c])]
    obj=[c for c in a.columns if c not in num]
    out['n_numeric_cols']=len(num)
    out['n_nonnumeric_cols']=len(obj)
    obj_diff=[]
    for c in obj:
        aa=a[c].astype(str).fillna('NA').to_numpy(); bb=b[c].astype(str).fillna('NA').to_numpy()
        n=int(np.sum(aa!=bb))
        if n: obj_diff.append({'column':c,'different_rows':n})
    out['nonnumeric_differences']=sorted(obj_diff,key=lambda z:z['different_rows'],reverse=True)[:20]
    stats=[]
    any_changed=np.zeros(len(a),dtype=bool)
    for c in num:
        aa=pd.to_numeric(a[c],errors='coerce').to_numpy(float); bb=pd.to_numeric(b[c],errors='coerce').to_numpy(float)
        finite=np.isfinite(aa)&np.isfinite(bb)
        d=np.full(len(aa),np.nan)
        d[finite]=np.abs(aa[finite]-bb[finite])
        nan_mismatch=np.isnan(aa)^np.isnan(bb)
        changed=(finite & (d>1e-12)) | nan_mismatch
        any_changed |= changed
        if finite.any():
            vals=d[finite]
            stats.append({
                'column':c,
                'max_abs':float(np.nanmax(vals)),
                'mean_abs':float(np.nanmean(vals)),
                'q99_abs':float(np.nanquantile(vals,.99)),
                'changed_rows_gt_1e12':int(changed.sum()),
                'changed_fraction_gt_1e12':float(changed.mean()),
            })
    out['rows_with_any_numeric_change']=int(any_changed.sum())
    out['fraction_rows_with_any_numeric_change']=float(any_changed.mean()) if len(a) else 0.0
    out['top_numeric_columns_by_max_abs']=sorted(stats,key=lambda z:z['max_abs'],reverse=True)[:20]
    out['top_numeric_columns_by_changed_fraction']=sorted(stats,key=lambda z:z['changed_fraction_gt_1e12'],reverse=True)[:20]
    cluster_cols=[c for c in a.columns if any(k in c.lower() for k in ('cluster','regime','group','member'))]
    cs=[]
    for c in cluster_cols:
        aa=a[c].astype(str).fillna('NA').to_numpy(); bb=b[c].astype(str).fillna('NA').to_numpy()
        cs.append({'column':c,'different_rows':int(np.sum(aa!=bb)),'fraction':float(np.mean(aa!=bb))})
    out['cluster_or_regime_columns']=cs
    return out


def score_diagnostics(mod, state: dict) -> dict:
    tickers=state['candidate_tickers']
    tit=state['tit']
    cal=tit[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    p=state['pred'].rename(columns={'ET_TAIL':'ET_RANK','XGB_TAIL':'XGB_RANK'}).copy()
    score=np.asarray(mod.stage19.score_matrix(p,cal,tickers),float)
    if score.shape==(len(tickers),len(cal)):
        score=score.T
    if score.shape!=(len(cal),len(tickers)):
        raise RuntimeError(f'unexpected score shape {score.shape}, expected {(len(cal),len(tickers))}')
    rows=[]
    for i,row in enumerate(cal.itertuples(index=False)):
        s=score[i]
        order=np.argsort(-s,kind='mergesort')
        j1,j2=int(order[0]),int(order[1])
        rows.append({
            'signal_date':pd.Timestamp(row.signal_date),
            'top1':tickers[j1],
            'top2':tickers[j2],
            'top1_score':float(s[j1]),
            'top2_score':float(s[j2]),
            'margin':float(s[j1]-s[j2]),
        })
    return {'cal':cal,'score':score,'monthly_top':pd.DataFrame(rows)}


def pair_score_summary(sa: dict, sb: dict, namea: str, nameb: str) -> dict:
    A,B=sa['score'],sb['score']
    if A.shape!=B.shape: return {'pair':[namea,nameb],'shape_a':list(A.shape),'shape_b':list(B.shape)}
    d=np.abs(A-B)
    ta,tb=sa['monthly_top'],sb['monthly_top']
    m=ta.merge(tb,on='signal_date',suffixes=('_a','_b'))
    diff=m.top1_a.ne(m.top1_b)
    same=~diff
    out={
        'pair':[namea,nameb],
        'score_shape':list(A.shape),
        'max_abs_score_diff':float(np.nanmax(d)),
        'mean_abs_score_diff':float(np.nanmean(d)),
        'q99_abs_score_diff':float(np.nanquantile(d,.99)),
        'monthly_top1_changed':int(diff.sum()),
        'monthly_top1_changed_fraction':float(diff.mean()),
        'first_monthly_top1_change':None if not diff.any() else str(m.loc[diff,'signal_date'].min().date()),
        'median_margin_when_same_top1':None if not same.any() else float(np.nanmedian(m.loc[same,'margin_a'])),
        'median_margin_a_when_top1_changes':None if not diff.any() else float(np.nanmedian(m.loc[diff,'margin_a'])),
        'median_margin_b_when_top1_changes':None if not diff.any() else float(np.nanmedian(m.loc[diff,'margin_b'])),
        'changed_month_examples':[],
    }
    if diff.any():
        z=m.loc[diff].copy()
        z['min_margin']=z[['margin_a','margin_b']].min(axis=1)
        for _,r in z.sort_values('signal_date').head(20).iterrows():
            out['changed_month_examples'].append({
                'signal_date':str(r.signal_date.date()),'top1_a':r.top1_a,'top1_b':r.top1_b,
                'margin_a':float(r.margin_a),'margin_b':float(r.margin_b),
            })
    return out


def daily_leader_pair(a: pd.DataFrame,b: pd.DataFrame,namea:str,nameb:str)->dict:
    m=a.merge(b,on='date',suffixes=('_a','_b'))
    d1=m.top1_a.ne(m.top1_b); d2=m.top2_a.ne(m.top2_b); anyd=d1|d2
    return {
        'pair':[namea,nameb],
        'days':len(m),
        'top1_different_days':int(d1.sum()),
        'top2_different_days':int(d2.sum()),
        'any_leader_different_days':int(anyd.sum()),
        'first_any_difference':None if not anyd.any() else str(pd.to_datetime(m.loc[anyd,'date']).min().date()),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw-root',required=True)
    ap.add_argument('--compare-script',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    rawroot=Path(args.raw_root).resolve(); compare=Path(args.compare_script).resolve(); out=Path(args.out).resolve()
    raws=[rawroot/f'_repeat{i}' for i in (1,2,3)]
    for r in raws:
        if not (r/'universe.csv').exists(): raise RuntimeError(f'missing {r}')
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)

    os.environ['FROZEN_149_ROOT']=str(rawroot)
    os.environ['FROZEN_HOLDOUT70_ROOT']=str(rawroot)
    spec=importlib.util.spec_from_file_location('canonical_bifurcation_compare',compare)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.FROZEN149=raws[1]; mod.FROZEN70=raws[1]

    u=mod.load_universe(raws[0]); tickers=u.ticker.tolist()
    raw_pairs=[]
    for i,j in ((0,1),(0,2),(1,2)):
        raw_pairs.append(raw_pair_summary(raws[i],raws[j],tickers))

    states=[]; scores=[]; leaders=[]; results=[]
    for idx,raw in enumerate(raws,1):
        work=out/f'repeat{idx}'
        mod.OUT=work
        st=mod.build_source_only_state('original149',raw)
        res=mod.replay_full_universe(st)
        sc=score_diagnostics(mod,st)
        states.append(st); scores.append(sc); results.append(res)
        dl=pd.read_csv(st['base']/'DAILY_LEADERS.csv',parse_dates=['date']); leaders.append(dl)
        sc['monthly_top'].to_csv(work/'MONTHLY_SCORE_TOP.csv',index=False)
        # Compact schema evidence only; full large intermediates remain in workflow workspace.
        pd.DataFrame({'column':st['tit'].columns.astype(str)}).to_csv(work/'TITANIUM_COLUMNS.csv',index=False)
        panel=pd.read_pickle(st['ma3_panel_path'])
        pd.DataFrame({'column':pd.Index(panel.columns).astype(str)}).to_csv(work/'MA3_PANEL_COLUMNS.csv',index=False)
        (work/'RESULT.json').write_text(json.dumps(res,indent=2)+'\n')

    pairs=[]
    for i,j in ((0,1),(0,2),(1,2)):
        ta,tb=states[i]['tit'].reset_index(drop=True),states[j]['tit'].reset_index(drop=True)
        pa,pb=pd.read_pickle(states[i]['ma3_panel_path']).reset_index(drop=True),pd.read_pickle(states[j]['ma3_panel_path']).reset_index(drop=True)
        pra,prb=states[i]['pred'].reset_index(drop=True),states[j]['pred'].reset_index(drop=True)
        pairs.append({
            'pair':[f'repeat{i+1}',f'repeat{j+1}'],
            'titanium':frame_diff(ta,tb,'titanium_candidates'),
            'ma3_panel':frame_diff(pa,pb,'ma3_raw_feature_panel'),
            'ensemble_predictions':frame_diff(pra,prb,'ensemble_predictions'),
            'stage19_scores':pair_score_summary(scores[i],scores[j],f'repeat{i+1}',f'repeat{j+1}'),
            'daily_leaders':daily_leader_pair(leaders[i],leaders[j],f'repeat{i+1}',f'repeat{j+1}'),
        })

    summary={
        'status':'BIFURCATION_DIAGNOSTIC_COMPLETE',
        'raw_pairs':raw_pairs,
        'replay_cagrs':[float(r['v2_full_universe']['cagr']) for r in results],
        'pairwise_stage_diagnostics':pairs,
        'interpretation_contract':[
            'This diagnostic does not select a model or parameter.',
            'First material amplification stage is inferred from ordered raw -> Titanium -> MA3 -> ensemble -> Stage19 score -> leader differences.',
            'Same canonical source blobs, environment, universe and execution contract are required for all three snapshots.'
        ]
    }
    (out/'RESULT.json').write_text(json.dumps(summary,indent=2,default=_jsonable)+'\n')
    print(json.dumps(summary,indent=2,default=_jsonable),flush=True)

if __name__=='__main__':
    main()
