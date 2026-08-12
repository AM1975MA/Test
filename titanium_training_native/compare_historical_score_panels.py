#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def normdate(x): return pd.to_datetime(x).dt.tz_localize(None)

def top_table(df, score, date, n=10):
    g=df[df.signal_date.eq(pd.Timestamp(date))].sort_values([score,'ticker'],ascending=[False,True]).head(n)
    cols=['ticker',score]+[c for c in ['compact_rank','tail_rank','titanium_score_pre_macro','macro_bonus','titanium_score','TIT_R'] if c in g.columns and c!=score]
    return g[cols].copy()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.root); out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    v=pd.read_parquet(root/'results'/'OOS_TICKER_SCORES.parquet');v['signal_date']=normdate(v.signal_date)
    n=pd.read_parquet(root/'results'/'NPORT_TITANIUM_PANEL.parquet');n['signal_date']=normdate(n.signal_date)
    sg=pd.read_parquet(root/'results'/'SUPER_GOLD_OOS_SCORE_PANEL.parquet');sg['signal_date']=normdate(sg.signal_date)
    print('V1',v.shape,v.columns.tolist())
    print('NPORT',n.shape,n.columns.tolist())
    print('SG',sg.shape,sg.columns.tolist())
    report={'shapes':{'v1':list(v.shape),'nport':list(n.shape),'sg':list(sg.shape)},'columns':{'v1':v.columns.tolist(),'nport':n.columns.tolist(),'sg':sg.columns.tolist()}}
    if 'TIT_R' not in n.columns: raise RuntimeError('NPORT panel has no TIT_R')
    m=v[['signal_date','ticker','TIT_R']].merge(n[['signal_date','ticker','TIT_R']],on=['signal_date','ticker'],suffixes=('_v1','_hist'))
    rows=[]
    for dt,g in m.groupby('signal_date'):
        rho=spearmanr(g.TIT_R_v1,g.TIT_R_hist,nan_policy='omit').statistic if len(g)>2 else np.nan
        ov1=g.nlargest(5,'TIT_R_v1').ticker.tolist(); oh=g.nlargest(5,'TIT_R_hist').ticker.tolist()
        rows.append({'signal_date':dt,'n':len(g),'rho':rho,'mae':float(np.mean(np.abs(g.TIT_R_v1-g.TIT_R_hist))),
                     'top1_v1':ov1[0] if ov1 else None,'top1_hist':oh[0] if oh else None,
                     'top1_match':bool(ov1 and oh and ov1[0]==oh[0]),'top2_set_match':set(ov1[:2])==set(oh[:2]),'top5_overlap':len(set(ov1)&set(oh))})
    d=pd.DataFrame(rows);d.to_csv(out/'MONTHLY_TIT_R_PARITY.csv',index=False)
    report['TIT_R']={'rows':len(m),'dates':int(d.signal_date.nunique()),'rho_mean':float(d.rho.mean()),'rho_median':float(d.rho.median()),'mae_mean':float(d.mae.mean()),'top1_match_rate':float(d.top1_match.mean()),'top2_set_match_rate':float(d.top2_set_match.mean()),'top5_overlap_mean':float(d.top5_overlap.mean())}
    for date in ['2026-06-30','2025-12-31','2023-12-29','2020-12-31','2019-12-31']:
        top_table(v,'TIT_R',date).to_csv(out/f'V1_TOP_{date}.csv',index=False)
        top_table(n,'TIT_R',date).to_csv(out/f'HIST_TOP_{date}.csv',index=False)
    # Compare any common numeric SG score/rank columns with V1 component columns.
    common=[]
    aliases={'compact_rank':['compact_rank','rank_compact','compact_R','F2D_COMPACT','score_compact'],
             'tail_rank':['tail_rank','rank_tail','tail_R','tailmix_rank','TAIL30'],
             'titanium_score':['titanium_score','TIT_score','TIT_R']}
    for vc,cands in aliases.items():
        if vc not in v: continue
        for sc in cands:
            if sc in sg.columns:
                z=v[['signal_date','ticker',vc]].merge(sg[['signal_date','ticker',sc]],on=['signal_date','ticker']).dropna()
                if len(z)>10:
                    common.append({'v1_col':vc,'sg_col':sc,'rows':len(z),'rho':float(spearmanr(z[vc],z[sc]).statistic),'mae':float(np.mean(np.abs(z[vc]-z[sc])))})
    report['supergold_common']=common
    chk={}
    for label,df in [('v1',v),('historical_nport',n)]:
        g=df[df.signal_date.eq(pd.Timestamp('2026-06-30'))].sort_values(['TIT_R','ticker'],ascending=[False,True]).head(10)
        chk[label]=g[['ticker','TIT_R']].to_dict(orient='records')
    report['checkpoint']=chk
    (out/'HISTORICAL_SCORE_PARITY.json').write_text(json.dumps(report,indent=2,default=str))
    print(json.dumps(report,indent=2,default=str))
if __name__=='__main__': main()
