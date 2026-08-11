#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
REF={'D1':0.15023,'D2':0.22645,'DEV':0.18617,'FULL':0.2165406437471759}
PER={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}
def load(p):
 s=importlib.util.spec_from_file_location('maturity_runner',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bcagr(arr,dates,s,e):
 dates=pd.DatetimeIndex(dates);q=(dates>=pd.Timestamp(s))&(dates<=pd.Timestamp(e));z=np.asarray(arr)[:,q];d=dates[q]
 if z.shape[1]<2:return np.full(z.shape[0],np.nan)
 y=(d[-1]-d[0]).days/365.25;return np.power(z[:,-1]/z[:,0],1/y)-1
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runner',required=True);ap.add_argument('--base-module',required=True);ap.add_argument('--v5-module',required=True);ap.add_argument('--data-dir',required=True);ap.add_argument('--maturity',required=True,choices=['monthly','d21','d42','signal']);ap.add_argument('--output',required=True);a=ap.parse_args()
 r=load(Path(a.runner));orig=r.fit_predict
 def fit(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
  c=compact.copy()
  if a.maturity=='d21': c['exit_date']=c['exit_date_21']
  elif a.maturity=='d42': c['exit_date']=c['exit_date_42']
  elif a.maturity=='signal': c['exit_date']=c['signal_date']
  return orig(c,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir)
 def nopkg(out,*args,**kwargs):
  p=Path(out)/'_FORENSIC_ONLY.zip';p.write_bytes(b'forensic');return p
 r.fit_predict=fit;r.package=nopkg
 sys.argv=[a.runner,'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500'];r.main()
 out=Path(a.output);z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz');dates=z['dates'];B=z['BASE'];R=z['ROUTER'];res={'maturity':a.maturity};err=0
 for n,(s,e) in PER.items():
  b=bcagr(B,dates,s,e);rr=bcagr(R,dates,s,e);bm=float(np.nanmean(b));res[n]={'base':bm,'router':float(np.nanmean(rr)),'median_base':float(np.nanmedian(b)),'ref':REF[n],'err_pp':(bm-REF[n])*100}
  if n in ('D1','D2','DEV'):err+=(bm-REF[n])**2
 res['rmse_pp']=float(np.sqrt(err/3)*100);(out/'MATURITY_SUMMARY.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
if __name__=='__main__':main()
