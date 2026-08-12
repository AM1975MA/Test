#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd

FROZEN={'top1_hit':0.1383,'top3_hit':0.3169,'top5_hit':0.4384}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scores',required=True);ap.add_argument('--labels',required=True);ap.add_argument('--membership',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    s=pd.read_parquet(a.scores);l=pd.read_parquet(a.labels);m=pd.read_csv(a.membership)
    for df in [s,l]:df['signal_date']=pd.to_datetime(df.signal_date);df['ticker']=df.ticker.astype(str).str.upper()
    m.ticker=m.ticker.astype(str).str.upper()
    score_col='titanium_score' if 'titanium_score' in s.columns else ('TIT_R' if 'TIT_R' in s.columns else 'compact_rank')
    x=s[['signal_date','ticker',score_col]].merge(l[['signal_date','ticker','fwd_ret_21']].drop_duplicates(['signal_date','ticker']),on=['signal_date','ticker'],how='inner').merge(m[['basket','ticker']],on='ticker',how='inner').dropna()
    x['pred_rank']=x.groupby(['signal_date','basket'])[score_col].rank(ascending=False,method='first')
    x['true_rank']=x.groupby(['signal_date','basket']).fwd_ret_21.rank(ascending=False,method='min')
    sel=x[x.pred_rank.eq(1)].copy()
    rows=[]
    for name,mask in [('D1',sel.signal_date.dt.year.between(2017,2019)),('D2',sel.signal_date.dt.year.between(2020,2022)),('DEV',sel.signal_date.dt.year.between(2017,2022)),('HOLD',sel.signal_date.dt.year>=2023),('FULL',sel.signal_date.dt.year>=2017)]:
        q=sel[mask]
        rows.append({'period':name,'n':len(q),'top1_hit':float(q.true_rank.le(1).mean()),'top3_hit':float(q.true_rank.le(3).mean()),'top5_hit':float(q.true_rank.le(5).mean()),'mean_true_rank':float(q.true_rank.mean()),'mean_fwd21':float(q.fwd_ret_21.mean())})
    out=pd.DataFrame(rows);Path(a.output).mkdir(parents=True,exist_ok=True);out.to_csv(Path(a.output)/'SELECTION_FINGERPRINT.csv',index=False)
    full=out[out.period.eq('FULL')].iloc[0].to_dict();summary={'score_col':score_col,'periods':rows,'frozen_reference':FROZEN,'full_abs_error':{k:abs(float(full[k])-v) for k,v in FROZEN.items()}}
    (Path(a.output)/'SELECTION_FINGERPRINT.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
