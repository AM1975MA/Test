#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker as RealXGBRanker

REF={'D1':0.15022713687299,'D2':0.2264479079604543,'DEV':0.1861726630584223,'FULL':0.2165406437471759}
PER={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}

def load(path,name):
    s=importlib.util.spec_from_file_location(name,str(path)); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def bcagr(arr,dates,s,e):
    dates=pd.DatetimeIndex(dates); q=(dates>=pd.Timestamp(s))&(dates<=pd.Timestamp(e)); z=np.asarray(arr)[:,q]; d=dates[q]
    if z.shape[1]<2:return np.full(z.shape[0],np.nan)
    y=(d[-1]-d[0]).days/365.25
    return np.power(z[:,-1]/z[:,0],1/y)-1

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--runner',required=True); ap.add_argument('--base-module',required=True); ap.add_argument('--v5-module',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--output',required=True); ap.add_argument('--mode',choices=['cluster_group_global_label','cluster_group_cluster_label'],required=True); a=ap.parse_args()
    r=load(Path(a.runner),'cluster_rank_runner'); holder={}; orig_load=r.load_module; orig_fit=r.fit_predict

    def patched_load(path,name):
        m=orig_load(path,name)
        if name=='v5_exec':
            orig_clusters=m.build_s3b_clusters
            def capture_clusters(*args,**kwargs):
                out=orig_clusters(*args,**kwargs); holder['clusters']=out[0].copy(); return out
            m.build_s3b_clusters=capture_clusters
        return m
    r.load_module=patched_load

    class ClusterXGBRanker:
        def __init__(self,*args,**kwargs): self.inner=RealXGBRanker(*args,**kwargs)
        def fit(self,X,y,group=None,verbose=False,**kwargs):
            meta=holder['compact_meta'].loc[X.index].copy()
            order=meta.sort_values(['signal_date','cluster_id','ticker']).index
            meta2=meta.loc[order]
            groups=meta2.groupby(['signal_date','cluster_id'],sort=False).size().tolist()
            yy=y.loc[order] if hasattr(y,'loc') else np.asarray(y)[[X.index.get_loc(i) for i in order]]
            self.inner.fit(X.loc[order],yy,group=groups,verbose=verbose,**kwargs)
            return self
        def predict(self,X,*args,**kwargs): return self.inner.predict(X,*args,**kwargs)
        def save_model(self,*args,**kwargs): return self.inner.save_model(*args,**kwargs)
        def __getattr__(self,n): return getattr(self.inner,n)
    r.XGBRanker=ClusterXGBRanker

    def fit(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
        c=compact.copy(); c['exit_date']=c['exit_date_42']
        cl=holder['clusters'][['signal_date','ticker','cluster_id']].copy(); cl['signal_date']=pd.to_datetime(cl.signal_date); cl['ticker']=cl.ticker.astype(str)
        c=c.merge(cl,on=['signal_date','ticker'],how='left',validate='many_to_one',sort=False)
        if c.cluster_id.isna().any(): raise RuntimeError(f"missing cluster ids: {int(c.cluster_id.isna().sum())}")
        if a.mode=='cluster_group_cluster_label':
            c['target_rank_pct']=c.groupby(['signal_date','cluster_id'])['fwd_ret_monthly'].rank(pct=True,method='average')
        holder['compact_meta']=c[['signal_date','ticker','cluster_id']].copy()
        return orig_fit(c,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir)
    def nopkg(out,*args,**kwargs): p=Path(out)/'_FORENSIC_ONLY.zip'; p.write_bytes(b'forensic'); return p
    r.fit_predict=fit; r.package=nopkg
    sys.argv=[a.runner,'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500']
    r.main()
    out=Path(a.output); z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz'); dates=z['dates']; B=z['BASE']; R=z['ROUTER']; res={'mode':a.mode,'compact_maturity':'exit_date_42'}; err=0.0
    for name,(s,e) in PER.items():
        b=bcagr(B,dates,s,e); rr=bcagr(R,dates,s,e); bm=float(np.nanmean(b)); rm=float(np.nanmean(rr)); ref=REF[name]
        res[name]={'base':bm,'router':rm,'median_base':float(np.nanmedian(b)),'median_router':float(np.nanmedian(rr)),'ref':ref,'err_pp':(bm-ref)*100}
        if name in ('D1','D2','DEV'):err+=(bm-ref)**2
    res['rmse_D1_D2_DEV_pp']=float(np.sqrt(err/3)*100); kp=out/'KNOWN_SIGNAL_CHECK.json'; res['known_signal']=json.loads(kp.read_text()) if kp.exists() else None
    (out/'D42_CLUSTER_RANK_SUMMARY.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
if __name__=='__main__':main()
