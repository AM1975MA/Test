#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

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
    ap=argparse.ArgumentParser(); ap.add_argument('--runner',required=True); ap.add_argument('--base-module',required=True); ap.add_argument('--v5-module',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    data_dir=Path(a.data_dir)
    C=pd.read_parquet(data_dir/'CLOSE.parquet'); O=pd.read_parquet(data_dir/'OPEN.parquet')
    for x in (C,O):
        x.index=pd.to_datetime(x.index).tz_localize(None); x.columns=[str(c).upper() for c in x.columns]
    C=C.sort_index(); O=O.sort_index(); obs=C.notna().cumsum()
    r=load(Path(a.runner),'elig126_runner'); orig_fit=r.fit_predict; eligibility_audit=[]
    def fit(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
        c=compact.copy(); c['exit_date']=c['exit_date_42']
        keep=np.zeros(len(c),dtype=bool); counts=np.full(len(c),np.nan); entry_ok=np.zeros(len(c),dtype=bool)
        for j,row in enumerate(c[['signal_date','ticker','entry_date']].itertuples(index=False,name=None)):
            sd,t,ed=row; sd=pd.Timestamp(sd); t=str(t).upper(); ed=pd.Timestamp(ed) if pd.notna(ed) else pd.NaT
            n=float(obs.at[sd,t]) if sd in obs.index and t in obs.columns and pd.notna(obs.at[sd,t]) else np.nan
            ok=bool(pd.notna(ed) and ed in O.index and t in O.columns and pd.notna(O.at[ed,t]))
            counts[j]=n; entry_ok[j]=ok; keep[j]=bool(np.isfinite(n) and n>=126 and ok)
        c['past_close_obs']=counts; c['entry_open_valid']=entry_ok
        before=len(c); c=c.loc[keep].copy(); after=len(c)
        eligibility_audit.append({'rows_before':before,'rows_after':after,'rows_removed':before-after,'remove_rate':(before-after)/max(before,1),'min_obs_kept':float(c.past_close_obs.min()) if after else np.nan})
        return orig_fit(c,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir)
    def nopkg(out,*args,**kwargs):
        p=Path(out)/'_FORENSIC_ONLY.zip'; p.write_bytes(b'forensic'); return p
    r.fit_predict=fit; r.package=nopkg
    sys.argv=[a.runner,'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500']
    r.main()
    out=Path(a.output); pd.DataFrame(eligibility_audit).to_csv(out/'ELIGIBILITY_AUDIT.csv',index=False)
    z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz'); dates=z['dates']; B=z['BASE']; R=z['ROUTER']; res={'compact_maturity':'exit_date_42','eligibility':'past_close_obs>=126 AND valid D+1 entry_open'}; err=0.0
    for name,(s,e) in PER.items():
        b=bcagr(B,dates,s,e); rr=bcagr(R,dates,s,e); bm=float(np.nanmean(b)); rm=float(np.nanmean(rr)); ref=REF[name]
        res[name]={'base':bm,'router':rm,'median_base':float(np.nanmedian(b)),'median_router':float(np.nanmedian(rr)),'ref':ref,'err_pp':(bm-ref)*100}
        if name in ('D1','D2','DEV'):err+=(bm-ref)**2
    res['rmse_D1_D2_DEV_pp']=float(np.sqrt(err/3)*100)
    kp=out/'KNOWN_SIGNAL_CHECK.json'; res['known_signal']=json.loads(kp.read_text()) if kp.exists() else None
    res['eligibility_audit']=eligibility_audit
    (out/'D42_ELIG126_SUMMARY.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
if __name__=='__main__':main()
