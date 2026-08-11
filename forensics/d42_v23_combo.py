#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, random, sys
from pathlib import Path
import numpy as np
import pandas as pd

REF={'D1':0.15023,'D2':0.22645,'DEV':0.18617,'FULL':0.2165406437471759}
PER={'D1':('2017-01-01','2019-12-31'),'D2':('2020-01-01','2022-12-31'),'DEV':('2017-01-01','2022-12-31'),'FULL':('2017-01-01','2026-12-31')}

def load(path,name):
    s=importlib.util.spec_from_file_location(name,str(path)); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def bcagr(arr,dates,s,e):
    dates=pd.DatetimeIndex(dates); q=(dates>=pd.Timestamp(s))&(dates<=pd.Timestamp(e)); z=np.asarray(arr)[:,q]; d=dates[q]
    if z.shape[1]<2: return np.full(z.shape[0],np.nan)
    y=(d[-1]-d[0]).days/365.25
    return np.power(z[:,-1]/z[:,0],1/y)-1

def exact_v23(base,pred,n):
    tickers=sorted(pred.ticker.astype(str).unique())
    cats=sorted({base.TICKER_CATEGORY[t] for t in tickers if t in base.TICKER_CATEGORY})
    if len(cats)!=6: raise RuntimeError(f'V23 requires 6 categories, got {cats}')
    ct={c:sorted([t for t in tickers if base.TICKER_CATEGORY.get(t)==c]) for c in cats}
    bad={c:len(v) for c,v in ct.items() if len(v)<4}
    if bad: raise RuntimeError(f'Insufficient category universe: {bad}')
    rng=random.Random(20260721); baskets=[]; seen=set(); attempts=0
    while len(baskets)<n and attempts<500000:
        attempts+=1; chosen=[]
        for c in cats: chosen.extend(rng.sample(ct[c],4))
        b=tuple(sorted(chosen))
        if b not in seen: seen.add(b); baskets.append(b)
    if len(baskets)!=n: raise RuntimeError(f'Only {len(baskets)} unique baskets')
    return baskets,cats

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--runner',required=True); ap.add_argument('--base-module',required=True); ap.add_argument('--v5-module',required=True); ap.add_argument('--data-dir',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    r=load(Path(a.runner),'combo_runner')
    orig_fit=r.fit_predict; orig_load=r.load_module
    def fit(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
        c=compact.copy(); c['exit_date']=c['exit_date_42']
        return orig_fit(c,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir)
    def patched_load(path,name):
        m=orig_load(path,name)
        if name=='v5': m.make_baskets=exact_v23
        return m
    def nopkg(out,*args,**kwargs):
        p=Path(out)/'_FORENSIC_ONLY.zip'; p.write_bytes(b'forensic'); return p
    r.fit_predict=fit; r.load_module=patched_load; r.package=nopkg
    sys.argv=[a.runner,'--base-module',a.base_module,'--v5-module',a.v5_module,'--data-dir',a.data_dir,'--output',a.output,'--n-estimators','360','--n-baskets','500']
    r.main()
    out=Path(a.output); z=np.load(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz'); dates=z['dates']; B=z['BASE']; R=z['ROUTER']; res={'maturity':'d42','membership':'V23_seed_20260721'}; err=0.0
    for name,(s,e) in PER.items():
        b=bcagr(B,dates,s,e); rr=bcagr(R,dates,s,e); bm=float(np.nanmean(b)); rm=float(np.nanmean(rr))
        res[name]={'base':bm,'router':rm,'median_base':float(np.nanmedian(b)),'median_router':float(np.nanmedian(rr)),'ref':REF[name],'err_pp':(bm-REF[name])*100}
        if name in ('D1','D2','DEV'): err+=(bm-REF[name])**2
    res['rmse_pp']=float(np.sqrt(err/3)*100)
    kp=out/'KNOWN_SIGNAL_CHECK.json'; res['known_signal']=json.loads(kp.read_text()) if kp.exists() else None
    membership=pd.read_csv(out/'BASKET_MEMBERSHIP_500.csv'); res['membership_baskets']=int(membership.basket.nunique()); res['membership_rows']=int(len(membership))
    (out/'D42_V23_SUMMARY.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))

if __name__=='__main__': main()
