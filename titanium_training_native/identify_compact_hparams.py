#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRanker

TARGET_FROZEN_IC = 0.0757109
SEED = 101

CONFIGS = [
 {'id':'PUBLISHED_360_D4','n_estimators':360,'max_depth':4,'learning_rate':.035,'min_child_weight':8.,'subsample':.85,'colsample_bytree':.80,'reg_lambda':8.,'reg_alpha':.10},
 {'id':'ANCESTOR_D3_240','n_estimators':240,'max_depth':3,'learning_rate':.040,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.65,'reg_lambda':12.,'reg_alpha':1.00},
 {'id':'ANCESTOR_D3_180','n_estimators':180,'max_depth':3,'learning_rate':.040,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.65,'reg_lambda':12.,'reg_alpha':1.00},
 {'id':'D3_240_MCW30','n_estimators':240,'max_depth':3,'learning_rate':.035,'min_child_weight':30.,'subsample':.85,'colsample_bytree':.65,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D3_240_MCW15','n_estimators':240,'max_depth':3,'learning_rate':.035,'min_child_weight':15.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D3_300_LR030','n_estimators':300,'max_depth':3,'learning_rate':.030,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D4_160_LIGHTREG','n_estimators':160,'max_depth':4,'learning_rate':.035,'min_child_weight':10.,'subsample':.85,'colsample_bytree':.85,'reg_lambda':1.,'reg_alpha':.05},
 {'id':'D4_160_MCW20','n_estimators':160,'max_depth':4,'learning_rate':.035,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.85,'reg_lambda':4.,'reg_alpha':.05},
 {'id':'D4_240_LR030','n_estimators':240,'max_depth':4,'learning_rate':.030,'min_child_weight':15.,'subsample':.85,'colsample_bytree':.80,'reg_lambda':12.,'reg_alpha':.20},
 {'id':'D4_240_COL075','n_estimators':240,'max_depth':4,'learning_rate':.035,'min_child_weight':15.,'subsample':.85,'colsample_bytree':.75,'reg_lambda':12.,'reg_alpha':.20},
 {'id':'D4_300_REG','n_estimators':300,'max_depth':4,'learning_rate':.030,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.75,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D3_360_PUBLISHEDLIKE','n_estimators':360,'max_depth':3,'learning_rate':.035,'min_child_weight':8.,'subsample':.85,'colsample_bytree':.80,'reg_lambda':8.,'reg_alpha':.10},
 {'id':'D3_360_SLOW','n_estimators':360,'max_depth':3,'learning_rate':.025,'min_child_weight':15.,'subsample':.90,'colsample_bytree':.80,'reg_lambda':12.,'reg_alpha':.20},
 {'id':'D3_480_SLOWREG','n_estimators':480,'max_depth':3,'learning_rate':.025,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D5_240','n_estimators':240,'max_depth':5,'learning_rate':.030,'min_child_weight':15.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D5_300_SLOW','n_estimators':300,'max_depth':5,'learning_rate':.025,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':16.,'reg_alpha':.50},
 {'id':'D2_200_FAST','n_estimators':200,'max_depth':2,'learning_rate':.050,'min_child_weight':15.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D2_300','n_estimators':300,'max_depth':2,'learning_rate':.035,'min_child_weight':20.,'subsample':.85,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D2_360_REG','n_estimators':360,'max_depth':2,'learning_rate':.030,'min_child_weight':30.,'subsample':.85,'colsample_bytree':.65,'reg_lambda':16.,'reg_alpha':1.00},
 {'id':'D2_500_SLOWREG','n_estimators':500,'max_depth':2,'learning_rate':.025,'min_child_weight':30.,'subsample':.85,'colsample_bytree':.65,'reg_lambda':16.,'reg_alpha':1.00},
 {'id':'D4_240_SUB075','n_estimators':240,'max_depth':4,'learning_rate':.050,'min_child_weight':20.,'subsample':.75,'colsample_bytree':.65,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D4_360_FULLSUB','n_estimators':360,'max_depth':4,'learning_rate':.025,'min_child_weight':20.,'subsample':1.00,'colsample_bytree':.70,'reg_lambda':12.,'reg_alpha':.50},
 {'id':'D3_240_LOREG','n_estimators':240,'max_depth':3,'learning_rate':.040,'min_child_weight':8.,'subsample':1.00,'colsample_bytree':.80,'reg_lambda':8.,'reg_alpha':.10},
 {'id':'D3_160_FAST','n_estimators':160,'max_depth':3,'learning_rate':.050,'min_child_weight':8.,'subsample':.85,'colsample_bytree':.80,'reg_lambda':8.,'reg_alpha':.10},
]

def load_module(path:Path):
    spec=importlib.util.spec_from_file_location('base_spec',str(path)); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def safe_ic(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    if m.sum()<8: return np.nan
    r=spearmanr(a[m],b[m]).statistic
    return float(r) if np.isfinite(r) else np.nan

def evaluate_config(panel,features,cfg):
    pred=[]; audits=[]; t0=time.time()
    params=dict(objective='rank:pairwise',eval_metric='ndcg@3',tree_method='hist',n_jobs=2,verbosity=0,**{k:v for k,v in cfg.items() if k!='id'})
    for year in range(2017,2027):
        cutoff=pd.Timestamp(year,1,1)
        tr=panel[(panel.signal_date<cutoff)&(panel.exit_date_21<cutoff)&panel.target_rank_pct.notna()].sort_values(['signal_date','ticker'])
        te=panel[panel.signal_date.dt.year==year].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist(); y=(tr.target_rank_pct*100).round().astype(int)
        m=XGBRanker(**params,random_state=SEED)
        m.fit(tr[features].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
        raw=m.predict(te[features].replace([np.inf,-np.inf],np.nan))
        q=te[['signal_date','ticker','target_rank_pct','fwd_ret_21']].copy()
        if 'fwd_ret_monthly' in te: q['fwd_ret_monthly']=te.fwd_ret_monthly.to_numpy()
        q['raw']=raw; q['score_rank']=q.groupby('signal_date').raw.rank(pct=True,method='average')
        pred.append(q);audits.append({'year':year,'train_rows':len(tr),'train_months':tr.signal_date.nunique(),'max_exit':str(pd.to_datetime(tr.exit_date_21).max().date())})
    p=pd.concat(pred,ignore_index=True)
    monthly=[]
    for d,g in p.groupby('signal_date'):
        rec={'signal_date':d,'ic_target':safe_ic(g.score_rank.to_numpy(float),g.target_rank_pct.to_numpy(float)),'ic_21':safe_ic(g.score_rank.to_numpy(float),g.fwd_ret_21.to_numpy(float))}
        if 'fwd_ret_monthly' in g: rec['ic_monthly']=safe_ic(g.score_rank.to_numpy(float),g.fwd_ret_monthly.to_numpy(float))
        z=g.dropna(subset=['score_rank','target_rank_pct']).nlargest(3,'score_rank')
        rec['selected_target_pct_top3']=float(z.target_rank_pct.mean()) if len(z) else np.nan
        monthly.append(rec)
    md=pd.DataFrame(monthly); years=pd.to_datetime(md.signal_date).dt.year
    periods={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)}
    out={'id':cfg['id'],'seed':SEED,'elapsed_s':time.time()-t0,'params':json.dumps(params,sort_keys=True)}
    for col in ['ic_target','ic_21','ic_monthly','selected_target_pct_top3']:
        if col not in md: continue
        out[col+'_mean']=float(md[col].mean()); out[col+'_median']=float(md[col].median())
        for name,(lo,hi) in periods.items(): out[f'{col}_{name}']=float(md.loc[(years>=lo)&(years<=hi),col].mean())
    basis=out.get('ic_monthly_mean',out.get('ic_21_mean',np.nan))
    out['distance_to_frozen_rank_ic']=abs(basis-TARGET_FROZEN_IC) if np.isfinite(basis) else np.nan
    return out,md,p,pd.DataFrame(audits)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--panel',required=True); ap.add_argument('--base-module',required=True); ap.add_argument('--output',required=True); ap.add_argument('--shard',type=int,default=0); ap.add_argument('--n-shards',type=int,default=4); a=ap.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);panel=pd.read_parquet(a.panel);panel.signal_date=pd.to_datetime(panel.signal_date);panel.exit_date_21=pd.to_datetime(panel.exit_date_21);base=load_module(Path(a.base_module));features=list(base.F2D_FEATURES)
    miss=[x for x in features if x not in panel.columns]
    if miss: raise RuntimeError(f'missing features: {miss}')
    rows=[]
    for i,cfg in enumerate(CONFIGS):
        if i%a.n_shards!=a.shard: continue
        print('RUN',i,cfg['id'],flush=True); rec,md,p,audit=evaluate_config(panel,features,cfg);rows.append(rec);md.to_csv(out/f"MONTHLY_{cfg['id']}.csv",index=False);audit.to_csv(out/f"AUDIT_{cfg['id']}.csv",index=False);print(json.dumps(rec,indent=2),flush=True)
    res=pd.DataFrame(rows).sort_values('distance_to_frozen_rank_ic');res.to_csv(out/f'COMPACT_ID_SHARD_{a.shard}.csv',index=False);print(res.to_string(index=False))

if __name__=='__main__':main()
