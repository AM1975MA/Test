#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker

def lm(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--package',required=True);ap.add_argument('--compact-probe',required=True);ap.add_argument('--broad-probe',required=True);ap.add_argument('--output',default='CHECKPOINT_2026');a=ap.parse_args()
    pkg=Path(a.package);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    base=lm('c_base',pkg/'source'/'titanium_retrained_current_data_audit.py');v6=lm('c_v6',pkg/'source'/'titanium_reconstruction_v6.py');cp=lm('c_cp',Path(a.compact_probe));bp=lm('c_bp',Path(a.broad_probe))
    mats=v6.load_mats(pkg/'data');dates=base.month_end_dates(mats['Close'].index)
    compact,frames=cp.exact_compact(base,mats,dates);compact=base.add_labels(compact,mats['Open'],dates)
    tail,D=bp.exact_broad(base,mats,dates,frames)
    D['vol_ratio_10_63']=D['vol_10']/D['vol_63'].replace(0,np.nan);D['vol_ratio_10_63_rank']=base.cs_pct(D['vol_ratio_10_63'])
    # rebuild Tail after completing schema
    for req in base.TAIL_FEATURES:
        if req not in D:
            raw=req[:-5] if req.endswith('_rank') else req;D[req]=base.cs_pct(D[raw]) if raw in D else pd.DataFrame(np.nan,index=dates,columns=mats['Close'].columns)
    tail=pd.concat([D[n].stack(dropna=False).rename(n) for n in base.TAIL_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    labs=compact[['signal_date','ticker','entry_date','exit_date','exit_date_21','exit_date_63','target_rank_21','target_rank_42','target_rank_63','target_multi_rank','y_tailmix','fwd_ret_21','fwd_ret_42','fwd_ret_63']]
    tail=tail.merge(labs,on=['signal_date','ticker'],how='left')
    macro,mf=v6.build_macro_panel(base,D,compact,base.TICKER_CATEGORY)
    cutoff=pd.Timestamp('2026-01-01');te=compact[compact.signal_date.dt.year.eq(2026)].sort_values(['signal_date','ticker']);tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker'])
    groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);ranks=[];raws=[]
    params=dict(base.COMPACT_PARAMS);params['n_estimators']=360;params['n_jobs']=2
    for seed in base.COMPACT_SEEDS:
        model=XGBRanker(**params,random_state=seed);model.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False);raw=model.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan));raws.append(raw);tmp=pd.DataFrame({'d':te.signal_date.to_numpy(),'x':raw});ranks.append(tmp.groupby('d').x.rank(pct=True).to_numpy())
    p=te[['signal_date','ticker']].copy();p['compact_raw']=np.mean(raws,axis=0);p['compact_rank']=np.mean(ranks,axis=0)
    ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()];tte=tail[tail.signal_date.dt.year.eq(2026)];tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0));tm.fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix);tq=tte[['signal_date','ticker']].copy();tq['tail_raw']=tm.predict(tte[base.TAIL_FEATURES]);p=p.merge(tq,on=['signal_date','ticker'],how='left');p['tail_rank']=p.groupby('signal_date').tail_raw.rank(pct=True);p['titanium_score_pre_macro']=.7*p.compact_rank+.3*p.tail_rank
    mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.target_rank.notna()];mte=macro[macro.signal_date.dt.year.eq(2026)];mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0));mm.fit(mtr[mf],mtr.target_rank);mq=mte[['signal_date','macro_category']].copy();mq['macro_raw']=mm.predict(mte[mf]);mq['macro_z']=mq.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12));tops=[]
    for d,g in mq.groupby('signal_date'):
        g=g.sort_values('macro_z',ascending=False);tops.append({'signal_date':d,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z)})
    p['macro_category']=p.ticker.map(base.TICKER_CATEGORY);p=p.merge(pd.DataFrame(tops),on='signal_date',how='left');p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.8),.15,0.);p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
    q=p[p.signal_date.eq(pd.Timestamp('2026-06-30'))].sort_values('titanium_score',ascending=False);q.head(25).to_csv(out/'CHECKPOINT_TOP25.csv',index=False);tail[tail.signal_date.eq(pd.Timestamp('2026-06-30'))&tail.ticker.isin(['USO','PALL','BNO'])].to_csv(out/'TAIL_USO_PALL_BNO.csv',index=False)
    s={'top1':str(q.iloc[0].ticker),'top2':str(q.iloc[1].ticker),'matches':bool(q.iloc[0].ticker=='USO' and q.iloc[1].ticker=='PALL'),'USO':q.set_index('ticker').loc['USO',['compact_rank','tail_rank','titanium_score']].to_dict(),'PALL':q.set_index('ticker').loc['PALL',['compact_rank','tail_rank','titanium_score']].to_dict(),'BNO':q.set_index('ticker').loc['BNO',['compact_rank','tail_rank','titanium_score']].to_dict()};(out/'SUMMARY.json').write_text(json.dumps(s,indent=2,default=float));print(json.dumps(s,indent=2,default=float))
if __name__=='__main__':main()
