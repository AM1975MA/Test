#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def one(s, old, new, label):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True)
    ap.add_argument('--target',choices=['R21','MONTHLY'],default='R21')
    ap.add_argument('--relevance',choices=['B5','R100'],default='B5')
    ap.add_argument('--median',action='store_true')
    a=ap.parse_args(); p=Path(a.source); s=p.read_text()

    # Exact documented 20-Jul S3B tree block.
    old="models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2"
    new="models_dir.mkdir(parents=True,exist_ok=True); params=dict(objective='rank:pairwise',eval_metric='ndcg',n_estimators=60,max_depth=4,learning_rate=0.05,min_child_weight=20,subsample=0.80,colsample_bytree=0.75,reg_lambda=12.0,reg_alpha=0.2,tree_method='hist',n_jobs=2,verbosity=0)"
    s=one(s,old,new,'S3B params')

    if a.target=='R21':
        old="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
        new="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_21.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
        s=one(s,old,new,'R21 maturity')
        target_expr='tr.target_rank_21'
        s=s.replace("'compact_max_exit':str(pd.to_datetime(tr.exit_date).max().date()) if len(tr) else None", "'compact_max_exit':str(pd.to_datetime(tr.exit_date_21).max().date()) if len(tr) else None")
    else:
        target_expr='tr.target_rank_pct'

    oldy="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]"
    if a.relevance=='B5':
        newy=f"groups=tr.groupby('signal_date',sort=True).size().tolist();y=np.minimum(4,np.floor({target_expr}.to_numpy(float)*5.0)).astype(int);seed_parts=[]"
    else:
        newy=f"groups=tr.groupby('signal_date',sort=True).size().tolist();y=({target_expr}*100).round().astype(int);seed_parts=[]"
    s=one(s,oldy,newy,'bridge relevance')

    if a.median:
        anchor=';seed_parts=[]'
        idx=s.index(anchor)+len(anchor)
        ins=";cimp=SimpleImputer(strategy='median',keep_empty_features=True);Xc_tr=cimp.fit_transform(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan));Xc_te=cimp.transform(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan));joblib.dump(cimp,ydir/'COMPACT_IMPUTER.joblib')"
        s=s[:idx]+ins+s[idx:]
        oldfit="m=XGBRanker(**params,random_state=seed);m.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False);raw=m.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan))"
        newfit="m=XGBRanker(**params,random_state=seed);m.fit(Xc_tr,y,group=groups,verbose=False);raw=m.predict(Xc_te)"
        s=one(s,oldfit,newfit,'median fit')

    oldpack="for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))"
    newpack="for k,x in mats.items():\n        q=x.stack(dropna=False).rename(k.lower()).reset_index(); q.columns=['date','ticker',k.lower()]; longs.append(q)"
    if oldpack in s: s=one(s,oldpack,newpack,'package')

    ident=f"S3B_BRIDGE_{a.target}_{a.relevance}_{'MED' if a.median else 'NOMED'}"
    s=s.replace("'compact_historical_params':False",f"'compact_historical_params':'{ident}'")
    s=s.replace("'compact_target':'fwd_ret_monthly'",f"'compact_target':'{a.target}'")
    s=s.replace("'compact_relevance':'rank_pct_x100_round'",f"'compact_relevance':'{a.relevance}'")
    p.write_text(s)
    print('bridge',ident)

if __name__=='__main__': main()
