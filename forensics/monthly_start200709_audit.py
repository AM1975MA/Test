#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
START=pd.Timestamp('2007-09-01')
REF={'D1':0.15022713687299,'D2':0.2264479079604543,'DEV':0.1861726630584223,'FULL':0.2165406437471759}
PER={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}
def load(p,n):
 s=importlib.util.spec_from_file_location(n,str(p));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bcagr(a,d,s,e):
 d=pd.DatetimeIndex(d);q=(d>=pd.Timestamp(s))&(d<=pd.Timestamp(e));z=np.asarray(a)[:,q];x=d[q]
 if z.shape[1]<2:return np.full(z.shape[0],np.nan)
 y=(x[-1]-x[0]).days/365.25;return np.power(z[:,-1]/z[:,0],1/y)-1
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runner',required=True);ap.add_argument('--base-module',required=True);ap.add_argument('--v5-module',required=True);ap.add_argument('--data-dir',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 r=load(Path(a.runner),'monthly_start_runner');orig=r.fit_predict
 def fit(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
  compact=compact[pd.to_datetime(compact.signal_date)>=START].copy();tail=tail[pd.to_datetime(tail.signal_date)>=START].copy();macro=macro[pd.to_datetime(macro.signal_date)>=START].copy();opp=opp[pd.to_datetime(opp.signal_date)>=START].copy()
  return orig(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir)
 def nopkg(out,*args,**kwargs):p=Path(out)/'_FORENSIC_ONLY.zip';p.write_bytes(b'forensic');return p
 r.fit_predict=fit;r.package=nopkg
 sys.argv=[a.runner,'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500'];r.main()
 out=Path(a.output);z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz');dates=z['dates'];B=z['BASE'];R=z['ROUTER'];res={'compact_maturity':'monthly_exit_date','training_start':str(START.date())};err=0.0
 for n,(s,e) in PER.items():
  b=bcagr(B,dates,s,e);rr=bcagr(R,dates,s,e);bm=float(np.nanmean(b));rm=float(np.nanmean(rr));ref=REF[n];res[n]={'base':bm,'router':rm,'median_base':float(np.nanmedian(b)),'median_router':float(np.nanmedian(rr)),'ref':ref,'err_pp':(bm-ref)*100}
  if n in ('D1','D2','DEV'):err+=(bm-ref)**2
 res['rmse_D1_D2_DEV_pp']=float(np.sqrt(err/3)*100);res['known_signal']=json.loads((out/'KNOWN_SIGNAL_CHECK.json').read_text());res['fit_audit']=pd.read_csv(out/'FIT_AUDIT.csv').to_dict('records');(out/'MONTHLY_START200709_SUMMARY.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
if __name__=='__main__':main()
