#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

FROZEN={'D1':0.15022713687299,'D2':0.2264479079604543,'DEV':0.1861726630584223,'HOLD':0.2760542274772661,'FULL':0.2165406437471759}
PERIODS={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)}


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,str(path)); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def load_mats(res:Path):
    out={}
    for key in ['Open','High','Low','Close','Volume']:
        x=pd.read_parquet(res/f'{key.upper()}.parquet'); x.index=pd.to_datetime(x.index).tz_localize(None); x.columns=[str(c).upper() for c in x.columns]; out[key]=x.sort_index().apply(pd.to_numeric,errors='coerce')
    common=sorted(set.intersection(*[set(x.columns) for x in out.values()])); return {k:v.reindex(columns=common) for k,v in out.items()}


def eligible_map(C:pd.DataFrame, signal_dates, min_history=252, max_missing_last_63=5):
    rows=[]
    for sd in pd.DatetimeIndex(signal_dates).sort_values().unique():
        hist=C.loc[:sd]
        if hist.empty: continue
        recent=hist.tail(63)
        ok=hist.iloc[-1].notna() & (hist.notna().sum()>=min_history) & (recent.isna().sum()<=max_missing_last_63)
        rows.extend((pd.Timestamp(sd),str(t),bool(v)) for t,v in ok.items())
    return pd.DataFrame(rows,columns=['signal_date','ticker','eligible'])


def load_baskets(path:Path):
    m=pd.read_csv(path); return [tuple(g.sort_values('ticker').ticker.astype(str)) for _,g in m.groupby('basket',sort=True)]


def scorecard(eq, idx, execmod):
    years=pd.DatetimeIndex(idx).year; rows=[]
    for p,(lo,hi) in PERIODS.items():
        pos=np.flatnonzero((years>=lo)&(years<=hi))
        if len(pos)<2: continue
        sl=slice(pos[0],pos[-1]+1); ix=pd.DatetimeIndex(idx)[sl]
        vals=[]
        for arr in eq:
            q=np.asarray(arr[sl],float); q=q/q[0]; vals.append(execmod.metrics(q,ix)[0])
        got=float(np.mean(vals)); rows.append({'period':p,'cagr':got,'frozen':FROZEN[p],'gap_pp':100*(got-FROZEN[p])})
    return pd.DataFrame(rows)


def run_variant(name,pred0,elig,opred,clusters,mats,cal,baskets,execmod):
    p=pred0.merge(elig,on=['signal_date','ticker'],how='left'); p['eligible']=p.eligible.fillna(False)
    if name=='FILTER_ONLY':
        p=p[p.eligible].copy()
    elif name=='LIVE_ELIG':
        p=p[p.eligible].copy()
        p['tail_rank']=p.groupby('signal_date').tail_raw.rank(pct=True,method='average')
        p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
        p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.titanium_score_pre_macro>=.80),.15,0.0)
        p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
        p['TIT_R']=p.groupby('signal_date').titanium_score.rank(pct=True,method='average')
    else: raise ValueError(name)
    p=p.drop(columns=['eligible']).sort_values(['signal_date','ticker'])
    idx,EB,ED,ER,active,margin,cond,*_=execmod.simulate_all(baskets,p,opred,clusters,mats,cal)
    sc=scorecard(EB,idx,execmod); sc.insert(0,'variant',name)
    chk=p[p.signal_date.eq(pd.Timestamp('2026-06-30'))].sort_values(['TIT_R','titanium_score'],ascending=False).head(10)
    return sc,chk[['ticker','compact_rank','tail_raw','tail_rank','titanium_score_pre_macro','macro_bonus','titanium_score','TIT_R']].copy()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.artifact_root);res=root/'results';out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    execmod=load_module(root/'source'/'exact_execution_v1.py','exact_exec')
    mats=load_mats(res); pred=pd.read_parquet(res/'OOS_TICKER_SCORES.parquet'); pred.signal_date=pd.to_datetime(pred.signal_date)
    opred=pd.read_parquet(res/'OOS_OPPORTUNITY_SCORES.parquet');opred.signal_date=pd.to_datetime(opred.signal_date)
    clusters=pd.read_csv(res/'DYNAMIC_CLUSTER_MEMBERSHIP.csv',parse_dates=['signal_date'])
    cal=pd.read_csv(res/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
    baskets=load_baskets(res/'BASKET_MEMBERSHIP_500.csv')
    elig=eligible_map(mats['Close'],pred.signal_date.unique());elig.to_csv(out/'POINT_IN_TIME_ELIGIBILITY.csv',index=False)
    rows=[]
    for name in ['FILTER_ONLY','LIVE_ELIG']:
        sc,chk=run_variant(name,pred,elig,opred,clusters,mats,cal,baskets,execmod);rows.append(sc);chk.to_csv(out/f'CHECKPOINT_{name}.csv',index=False)
    allsc=pd.concat(rows,ignore_index=True);allsc.to_csv(out/'ELIGIBILITY_ABLATION_SCORECARD.csv',index=False)
    stats=elig.groupby('signal_date').eligible.sum().describe().to_dict()
    summary={'eligible_count_stats':{k:float(v) for k,v in stats.items()},'scorecards':allsc.to_dict(orient='records')}
    (out/'ELIGIBILITY_ABLATION.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2));print('\nCheckpoint LIVE_ELIG');print(pd.read_csv(out/'CHECKPOINT_LIVE_ELIG.csv').to_string(index=False))
if __name__=='__main__':main()
