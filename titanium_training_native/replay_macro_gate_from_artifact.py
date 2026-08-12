#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd


def load_module(path:Path,name='v5'):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--execution-source',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);v5=load_module(Path(a.execution_source))
    pred=pd.read_parquet(root/'OOS_TICKER_SCORES.parquet');pred['signal_date']=pd.to_datetime(pred.signal_date)
    old_bonus=pred.macro_bonus.copy() if 'macro_bonus' in pred else pd.Series(0,index=pred.index,dtype=float)
    pred['macro_bonus']=np.where((pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.tail_rank>=.80),.15,0.0)
    pred['titanium_score']=pred.titanium_score_pre_macro+pred.macro_bonus
    pred['TIT_R']=pred.groupby('signal_date').titanium_score.rank(pct=True,method='average')
    opp=pd.read_parquet(root/'OOS_OPPORTUNITY_SCORES.parquet');opp['signal_date']=pd.to_datetime(opp.signal_date)
    cpath=root/'DYNAMIC_CLUSTER_MEMBERSHIP.csv'
    clusters=pd.read_csv(cpath);clusters['signal_date']=pd.to_datetime(clusters.signal_date)
    mats={k:pd.read_parquet(root/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']}
    for x in mats.values():x.index=pd.to_datetime(x.index)
    comp=pd.read_parquet(root/'COMPACT_LABELED.parquet');comp['signal_date']=pd.to_datetime(comp.signal_date);comp['entry_date']=pd.to_datetime(comp.entry_date);comp['exit_date']=pd.to_datetime(comp.exit_date)
    cal=comp[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date');cal=cal[cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    mem=pd.read_csv(root/'BASKET_MEMBERSHIP_500.csv');mem.ticker=mem.ticker.astype(str)
    baskets=[tuple(g.sort_values('ticker').ticker.tolist()) for _,g in mem.groupby('basket',sort=True)][:500]
    idx,EB,ED,ER,active,margin,cond,bs,bw,ds,dw=v5.simulate_all(baskets,pred,opp,clusters,mats,cal)
    periods={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)};years=pd.DatetimeIndex(idx).year;rows=[]
    for period,(lo,hi) in periods.items():
        pos=np.flatnonzero((years>=lo)&(years<=hi))
        if len(pos)<2:continue
        sl=slice(pos[0],pos[-1]+1);ix=pd.DatetimeIndex(idx)[sl]
        for b in range(len(baskets)):
            for name,arr in [('BASE',EB[b]),('DIRECT',ED[b]),('ROUTER',ER[b])]:
                q=np.asarray(arr[sl],float);q=q/q[0];c,dd,sh,fe=v5.metrics(q,ix);rows.append({'period':period,'basket':b,'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe})
    detail=pd.DataFrame(rows);detail['calmar']=detail.cagr/(-detail.maxdd.replace(0,np.nan));score=detail.groupby(['period','strategy'],as_index=False).agg(cagr=('cagr','mean'),maxdd=('maxdd','mean'),sharpe=('sharpe','mean'),calmar=('calmar','mean'))
    detail.to_csv(out/'PER_BASKET_PERIOD_METRICS.csv',index=False);score.to_csv(out/'PERIOD_SCORECARD_500.csv',index=False);pred.to_parquet(out/'OOS_TICKER_SCORES.parquet',index=False)
    changed=(old_bonus.fillna(0).to_numpy()!=pred.macro_bonus.to_numpy());z=pred[pred.macro_bonus>0]
    frozen={'D1':.15022713687299,'D2':.2264479079604543,'DEV':.1861726630584223,'HOLD':.2760542274772661,'FULL':.2165406437471759};base=score[score.strategy.eq('BASE')].set_index('period');pp={k:{'cagr':float(base.loc[k,'cagr']),'frozen':v,'gap_pp':100*(float(base.loc[k,'cagr'])-v)} for k,v in frozen.items()}
    summary={'variant':'POSTFIT_FROZEN_MACRO_TAIL_GATE_REPLAY','periods':pp,'rmse_pp_5periods':math.sqrt(sum(x['gap_pp']**2 for x in pp.values())/5),'changed_bonus_rows':int(changed.sum()),'old_bonus_rows':int((old_bonus.fillna(0)>0).sum()),'new_bonus_rows':int((pred.macro_bonus>0).sum()),'new_bonus_months':int(z.signal_date.nunique()),'new_bonus_tickers':int(z.ticker.nunique()),'tail_rank_min_bonus':float(z.tail_rank.min()) if len(z) else None,'router_active_months':int(np.asarray(active,bool).sum())}
    (out/'MACRO_GATE_REPLAY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
