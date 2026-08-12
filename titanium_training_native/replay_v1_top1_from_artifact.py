#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,math
from pathlib import Path
import numpy as np,pandas as pd

REF={'DEV':.1884,'HOLD':.2946,'FULL':.2231403752747837}

def load_module(path:Path):
    spec=importlib.util.spec_from_file_location('v5',str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--execution-source',required=True);ap.add_argument('--output',required=True);ap.add_argument('--membership',default=None);a=ap.parse_args()
    root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);v5=load_module(Path(a.execution_source))
    pred=pd.read_parquet(root/'OOS_TICKER_SCORES.parquet');pred.signal_date=pd.to_datetime(pred.signal_date)
    pred['macro_bonus']=np.where((pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.tail_rank>=.80),.15,0.0);pred['titanium_score']=pred.titanium_score_pre_macro+pred.macro_bonus;pred['TIT_R']=pred.groupby('signal_date').titanium_score.rank(pct=True,method='average')
    opp=pd.read_parquet(root/'OOS_OPPORTUNITY_SCORES.parquet');opp.signal_date=pd.to_datetime(opp.signal_date);clusters=pd.read_csv(root/'DYNAMIC_CLUSTER_MEMBERSHIP.csv');clusters.signal_date=pd.to_datetime(clusters.signal_date)
    mats={k:pd.read_parquet(root/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']};[setattr(x,'index',pd.to_datetime(x.index)) for x in mats.values()]
    comp=pd.read_parquet(root/'COMPACT_LABELED.parquet');comp.signal_date=pd.to_datetime(comp.signal_date);comp.entry_date=pd.to_datetime(comp.entry_date);comp.exit_date=pd.to_datetime(comp.exit_date);cal=comp[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date');cal=cal[cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    mp=Path(a.membership) if a.membership else root/'BASKET_MEMBERSHIP_500.csv';mem=pd.read_csv(mp);mem.ticker=mem.ticker.astype(str);baskets=[tuple(g.sort_values('ticker').ticker.tolist()) for _,g in mem.groupby('basket',sort=True)][:500]
    idx,ticks,ti,O,L,C,PC,gap,UD1,UNEG,UH,SA,ei,xi,mi=v5.prepare_sim_inputs(mats,cal)
    bs,bw,ds,dw,margin,cond=v5.build_target_arrays(baskets,pred,opp,clusters,pd.DatetimeIndex(cal.signal_date),ti,mats['Open'],pd.DatetimeIndex(cal.entry_date))
    # Titanium V1 is the pure concentrated top-1 engine before V2's 75/25 fallback.
    v1s=bs.copy();v1w=np.zeros_like(bw);v1w[:,:,0]=np.where(v1s[:,:,0]>=0,1.0,0.0)
    E=v5.exact_sim(v1s[None,:,:,:],v1w[None,:,:,:],mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV'],v5.COST,v5.STOP_SLIP)[0]
    years=pd.DatetimeIndex(idx).year;periods={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)};rows=[]
    for name,(lo,hi) in periods.items():
        pos=np.flatnonzero((years>=lo)&(years<=hi));sl=slice(pos[0],pos[-1]+1);ix=pd.DatetimeIndex(idx)[sl];vals=[]
        for b in range(len(baskets)):
            q=E[b,sl]/E[b,sl][0];c,dd,sh,fe=v5.metrics(q,ix);vals.append((c,dd,sh))
        arr=np.asarray(vals,float);rows.append({'period':name,'cagr':float(np.nanmean(arr[:,0])),'maxdd':float(np.nanmean(arr[:,1])),'sharpe':float(np.nanmean(arr[:,2])),'frozen_v1_ref':REF.get(name),'gap_pp':100*(float(np.nanmean(arr[:,0]))-REF[name]) if name in REF else None})
    pd.DataFrame(rows).to_csv(out/'V1_PERIOD_SCORECARD.csv',index=False);summary={'variant':'SOURCE_FAITHFUL_V1_PURE_TOP1_FROZEN_MACRO_GATE','membership_tickers':int(mem.ticker.nunique()),'periods':rows};(out/'V1_REPLAY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
