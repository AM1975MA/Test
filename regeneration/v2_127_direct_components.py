#!/usr/bin/env python3
"""Reconstruct ONLY the annual Tail and Macro forecasts used by frozen V2 127-leaf XGB.
No XGB fitting is performed. Exact row-by-row baseline score parity is mandatory.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'regeneration'))
import v2_large_leaf_sweep as sweep

EXPECTED_BASKET_HASH='36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--raw',default='etf_trader_raw')
    p.add_argument('--scores',default='runs/v2_large_leaf_complete/OOS_SCORES.csv')
    p.add_argument('--baskets',default='regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv')
    p.add_argument('--out',default='runs/v2_127_direct_components')
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==EXPECTED_BASKET_HASH
    raw_scores=Path(a.scores)
    source_sha=hashlib.sha256(raw_scores.read_bytes()).hexdigest()
    frozen=pd.read_csv(raw_scores,parse_dates=['signal_date'])
    frozen=frozen[frozen.variant.eq('leaves_127')][['signal_date','ticker','raw','score']].copy()
    if len(frozen)==0 or frozen.duplicated(['signal_date','ticker']).any():
        raise RuntimeError('Missing or duplicated frozen 127-leaf predictions')
    mats,cats,raw_manifest=sweep.load_ticker_csv_folder(a.raw)
    assert len(cats)==149
    mats={key:v.loc[v.index>=pd.Timestamp(2011,1,1)] for key,v in mats.items()}
    k=sweep.k
    k.ALL_TICKERS=sorted(cats)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted(t for t in cats if cats[t]==c) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats['Close'].index)
    if len(dates) and dates[-1]==mats['Close'].index[-1]:dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats)
    compact=k.add_labels(compact[compact.signal_date.isin(dates)],mats['Open'],dates)
    tail=k.add_labels(tail[tail.signal_date.isin(dates)],mats['Open'],dates)
    fixed_frames,audit=sweep.fixed_annual_frames(compact,tail,range(2018,2027))
    fixed=pd.concat([ctx[-1] for ctx in fixed_frames],ignore_index=True)
    take=['signal_date','ticker','tail','top_macro','macro_gap','macro_category']
    if fixed.duplicated(['signal_date','ticker']).any(): raise RuntimeError('duplicate fixed')
    joined=frozen.merge(fixed[take],on=['signal_date','ticker'],how='outer',indicator=True,validate='one_to_one')
    if not joined._merge.eq('both').all():
        print(joined._merge.value_counts())
        raise RuntimeError('Frozen XGB and reconstructed auxiliary train/test row sets differ')
    joined=joined.drop(columns='_merge').sort_values(['signal_date','ticker']).reset_index(drop=True)
    joined['raw_rank']=joined.groupby('signal_date')['raw'].rank(pct=True)
    joined['tail_rank']=joined.groupby('signal_date')['tail'].rank(pct=True)
    joined['macro_eligible']=((joined.macro_category==joined.top_macro)&(joined.macro_gap>=.75)).astype('int8')
    joined['macro_fired']=(joined.macro_eligible.eq(1)&joined.tail_rank.ge(.8)).astype('int8')
    old_raw=.70*joined.raw_rank+.30*joined.tail_rank+.15*joined.macro_fired
    joined['replayed_score']=old_raw.groupby(joined.signal_date).rank(pct=True)
    error=float(np.max(np.abs(joined.replayed_score-joined.score)))
    if error>1e-12:
        worst=joined.assign(err=np.abs(joined.replayed_score-joined.score)).nlargest(8,'err')
        print('BASELINE_SCORE_PARITY_FAIL',error,worst[['signal_date','ticker','score','replayed_score','err']].to_dict('records'),flush=True)
        raise RuntimeError('Baseline score parity is not exact, refuse ablation')
    joined.drop(columns=['replayed_score']).to_csv(out/'FROZEN_COMPONENTS.csv',index=False)
    doc={'status':'BASELINE_SCORE_PARITY_PASS','max_abs_score_error':error,
         'n_frozen_rows':len(joined),'n_frozen_dates':int(joined.signal_date.nunique()),
         'basket_sha256':EXPECTED_BASKET_HASH,'frozen_score_sha256':source_sha,
         'frozen_127_leaves':True,'xgboost_fitted_in_this_step':False,
         'tail_macro_are_walk_forward':True,'fixed_annual_fit_audit':audit,
         'raw_files_manifest':raw_manifest}
    (out/'COMPONENT_AUDIT.json').write_text(json.dumps(doc,indent=2,default=str))
    print('COMPONENT_PARITY_SUCCESS',json.dumps({k:doc[k] for k in ['max_abs_score_error','n_frozen_rows','n_frozen_dates','basket_sha256','frozen_score_sha256']}),flush=True)
if __name__=='__main__':main()
