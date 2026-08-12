#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);a=ap.parse_args()
    p=Path(a.source);s=p.read_text()
    old="groups=tr.groupby('signal_date',sort=True).size().tolist();y="
    if s.count(old)!=1: raise RuntimeError(f'group/y anchor count={s.count(old)}')
    # Insert one fit-time median imputer per annual fold, matching the old S3/S3B LambdaRank family.
    pos=s.index(old)
    line_end=s.index("seed_parts=[]",pos)+len("seed_parts=[]")
    block=s[pos:line_end]
    block_new=block+";cimp=SimpleImputer(strategy='median',keep_empty_features=True);Xc_tr=cimp.fit_transform(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan));Xc_te=cimp.transform(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan));joblib.dump(cimp,ydir/'COMPACT_IMPUTER.joblib')"
    s=s[:pos]+block_new+s[line_end:]
    oldfit="m=XGBRanker(**params,random_state=seed);m.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False);raw=m.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan))"
    newfit="m=XGBRanker(**params,random_state=seed);m.fit(Xc_tr,y,group=groups,verbose=False);raw=m.predict(Xc_te)"
    s=one(s,oldfit,newfit,'compact fit/predict matrix')
    s=s.replace("'compact_historical_params':'FORENSIC_", "'compact_historical_params':'FORENSIC_MEDIAN_")
    p.write_text(s);print('patched median Compact preprocessing')

if __name__=='__main__': main()
