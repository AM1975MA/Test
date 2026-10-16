"""Independent path-first PLS-XGB economic comparison; zero refits."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v2.summarize_replay import metrics,checked_leaders,selections,dispersion
from pls_xgb_v1.core import VARIANTS

def read_path(path):
    z=np.load(path,allow_pickle=False)
    eq=np.asarray(z['equity'],float).reshape(-1)
    dates=pd.to_datetime(z['dates'])
    return pd.DataFrame({'date':dates,'equity':eq})

def annual_returns(p):
    f=read_path(p)
    f['daily']=f.equity.pct_change().fillna(f.equity.iloc[0]-1.)
    values=[]
    for year,g in f.groupby(f.date.dt.year):
        values.append(dict(year=int(year),return_pct=float(((1+g.daily).prod()-1)*100),
                           sessions=len(g)))
    return values

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--replays',required=True);parser.add_argument('--out',required=True)
    a=parser.parse_args();root=Path(a.replays)
    summary={};leaders={};calendar=None
    for variant in VARIANTS:
        rows=[];leader_frames=[];years=[]
        for i in (1,2,3):
            folder=root/f'v2replay-{variant}-r{i}'
            obj=json.loads((folder/'RESULT.json').read_text())
            if(obj.get('status')!='PAPER_LTR_V2_CACHE_REPLAY_COMPLETE'
               or obj['variant']!=variant or obj['repeat']!=i
               or not obj['audit']['baseline_replay']['PASS']
               or not obj['audit']['input_linkage']['PASS']):raise ValueError('Not verified replay '+variant)
            path=folder/'candidate'/'FULL_UNIVERSE_PATH.npz'
            fresh,dates=metrics(path)
            decl=obj['candidate']['v2_full_universe']
            for name,v in fresh.items():
                if abs(v-float(decl[name]))>1e-12:raise ValueError(f'Replay metric mismatch {variant}/{i}/{name}')
            if calendar is None:calendar=dates
            if not dates.equals(calendar):raise ValueError('Common dates mismatch')
            frame=checked_leaders(folder/'candidate'/'DAILY_LEADERS.csv',dates)
            leader_frames.append(frame)
            rows.append(dict(repeat=i,**fresh,turnover=float(decl.get('annualized_turnover',np.nan))))
            years.append(dict(repeat=i,returns=annual_returns(path)))
        disp=dispersion(rows)
        sel=selections(leader_frames)
        summary[variant]=dict(paths=rows,dispersion=disp,leader_disagreement=sel,
                annual=years,mean_year_2021=float(np.mean([next(r['return_pct'] for r in entry['returns'] if r['year']==2021) for entry in years])),
                mean_year_2023=float(np.mean([next(r['return_pct'] for r in entry['returns'] if r['year']==2023) for entry in years])))
    result=dict(status='PLS_XGB_ECONOMIC_COMPLETE',variants=summary,
       all_9_canonical_replays_verified=True,source_vintages_correlated=True,
       development_period_reused=True,production_adoption=False)
    Path(a.out).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'economic':{
        v:{'dispersion':d['dispersion'],'top1_any':d['leader_disagreement']['top1_any_fraction'],
           'r2021':d['mean_year_2021'],'r2023':d['mean_year_2023']} for v,d in summary.items()}},indent=2))

if __name__=='__main__':main()
