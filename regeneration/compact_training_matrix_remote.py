#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, time
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker

SEEDS=[101,202,303]

def loadmod(path,name):
    s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--package-root',required=True);ap.add_argument('--label',choices=['exit_date_21','exit_date'],required=True);ap.add_argument('--filter30',type=int,choices=[0,1],required=True);ap.add_argument('--trees',type=int,default=120);ap.add_argument('--output',required=True);a=ap.parse_args()
    R=Path(a.package_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    base=loadmod(R/'source/titanium_retrained_current_data_audit.py','base_parity');v6=loadmod(R/'source/titanium_reconstruction_v6.py','v6_parity')
    df=pd.read_parquet(R/'panels/NPORT_TITANIUM_PANEL.parquet');
    for c in ['signal_date','exit_date_21','exit_date']: df[c]=pd.to_datetime(df[c])
    F=list(base.F2D_FEATURES);params=dict(base.COMPACT_PARAMS);params.update(n_estimators=a.trees,n_jobs=4)
    valid=(df[F].notna().sum(axis=1)>=30) if a.filter30 else pd.Series(True,index=df.index)
    seed_parts={s:[] for s in SEEDS};audit=[];started=time.time()
    for year in range(2017,2027):
        cut=pd.Timestamp(year,1,1)
        tr=df[(df.signal_date<cut)&(df[a.label]<cut)&df.target_rank_pct.notna()&valid].sort_values(['signal_date','ticker'])
        te=df[(df.signal_date.dt.year==year)&valid].sort_values(['signal_date','ticker'])
        if te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int)
        Xtr=tr[F].replace([np.inf,-np.inf],np.nan);Xte=te[F].replace([np.inf,-np.inf],np.nan)
        for seed in SEEDS:
            model=XGBRanker(**params,random_state=seed);model.fit(Xtr,y,group=groups,verbose=False)
            q=te[['signal_date','ticker']].copy();q['pred']=model.predict(Xte);seed_parts[seed].append(q)
        audit.append({'year':year,'train_rows':len(tr),'train_dates':tr.signal_date.nunique(),'test_rows':len(te)})
    preds={s:pd.concat(seed_parts[s],ignore_index=True) for s in SEEDS}
    aux=pd.read_parquet(R/'panels/SUPER_GOLD_OOS_SCORE_PANEL.parquet')[['signal_date','ticker','tail_rank','top_macro','macro_gap_z','macro_category']]
    aux['signal_date']=pd.to_datetime(aux.signal_date)
    cal=pd.read_csv(R/'panels/MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']);dates=list(cal.signal_date)
    mats={k:pd.read_parquet(R/'data'/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']}
    for k,x in mats.items(): x.index=pd.to_datetime(x.index).tz_localize(None);x.columns=[str(c).upper() for c in x.columns]
    ticks=sorted(set.intersection(*[set(x.columns) for x in mats.values()]));mats={k:v.reindex(columns=ticks) for k,v in mats.items()};ti={t:i for i,t in enumerate(ticks)}
    mem=pd.read_csv(R/'panels/BASKET_MEMBERSHIP_500.csv');baskets=[np.array([ti[t] for t in g.ticker.astype(str)],int) for _,g in mem.groupby('basket',sort=True)]
    idx,tix,tii,O,L,C,PC,gap,UD1,UNEG,UH,SA,ei,xi,mi=v6.prepare_sim_inputs(mats,cal);assert tix==ticks
    def aggregate(mode):
        z=None
        for seed,q0 in preds.items():
            q=q0.copy();q['v']=q['pred'] if mode=='rawmean' else q.groupby('signal_date').pred.rank(pct=True);q=q[['signal_date','ticker','v']].rename(columns={'v':f'v{seed}'})
            z=q if z is None else z.merge(q,on=['signal_date','ticker'],how='inner')
        vc=[f'v{s}' for s in SEEDS]
        if mode=='rawmean': z['compact_rank']=z.groupby('signal_date')[vc].transform('mean').mean(axis=1) if False else z[vc].mean(axis=1);z['compact_rank']=z.groupby('signal_date').compact_rank.rank(pct=True)
        else: z['compact_rank']=z[vc].mean(axis=1)
        return z[['signal_date','ticker','compact_rank']]
    def evaluate(cp,mode):
        q=cp[cp.signal_date.isin(dates)].merge(aux,on=['signal_date','ticker'],how='left');q['pre']=.7*q.compact_rank+.3*q.tail_rank;q['bonus']=np.where((q.macro_category==q.top_macro)&(q.macro_gap_z>=.75)&(q.tail_rank>=.80),.15,0.0);q['score']=q.pre+q.bonus;q['TIT_R']=q.groupby('signal_date').score.rank(pct=True)
        sm=q.pivot(index='signal_date',columns='ticker',values='score').reindex(index=dates,columns=ticks).to_numpy(float);rm=q.pivot(index='signal_date',columns='ticker',values='TIT_R').reindex(index=dates,columns=ticks).to_numpy(float)
        B=len(baskets);K=len(dates);sel=np.full((B,K,2),-1,np.int16);bw=np.zeros((B,K,2))
        for b,ix in enumerate(baskets):
            for k in range(K):
                ok=ix[np.isfinite(sm[k,ix])]
                if len(ok)<2: continue
                order=ok[np.argsort(-sm[k,ok],kind='stable')];u,v=order[:2];m=rm[k,u]-rm[k,v];w=1.0 if m>=.12 else .75;sel[b,k]=[u,v];bw[b,k]=[w,1-w]
        E=v6.exact_sim(sel[None],bw[None],mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,tii['BIL'],tii['SHV'],v6.COST,v6.STOP_SLIP)[0]
        met=np.array([v6.metrics(E[b],idx) for b in range(B)])
        return {'label_cutoff':a.label,'filter30':bool(a.filter30),'seed_aggregation':mode,'trees':a.trees,'mean_cagr':float(met[:,0].mean()),'median_cagr':float(np.median(met[:,0])),'p05_cagr':float(np.quantile(met[:,0],.05)),'p95_cagr':float(np.quantile(met[:,0],.95)),'median_maxdd':float(np.median(met[:,1])),'mean_sharpe':float(met[:,2].mean()),'concentration_rate':float((bw[:,:,0]==1).mean()),'elapsed_sec':time.time()-started}
    rows=[evaluate(aggregate(m),m) for m in ['rawmean','rankmean']]
    pd.DataFrame(rows).to_csv(out/'RESULTS.csv',index=False);pd.DataFrame(audit).to_csv(out/'FIT_AUDIT.csv',index=False);(out/'RESULTS.json').write_text(json.dumps(rows,indent=2));print(pd.DataFrame(rows).to_string(index=False),flush=True)
if __name__=='__main__':main()
