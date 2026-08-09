#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit, prange

EPS=1e-12

def lm(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

@njit(cache=False)
def _value(a,u,free,bu,su,p,bil,shv):
    v=free+bu*p[bil]+su*p[shv]
    for j in range(len(a)):
        if a[j]>=0 and u[j]!=0:v+=u[j]*p[a[j]]
    return v

@njit(parallel=True,cache=False)
def sim_flagged(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,bil,shv,cost,slip,use_governor,use_stops):
    N,B,K,P=SEL.shape;D=len(mi);E=np.ones((N,B,D))
    for n in prange(N):
      for b in range(B):
        a=np.full(P,-1,np.int16);u=np.zeros(P);bu=0.;su=0.;free=1.;pf=-1.;pw=np.full(P,-9.);cd=0
        for d in range(D):
          val=_value(a,u,free,bu,su,O[d],bil,shv)
          if not np.isfinite(val) or val<=0:val=E[n,b,d-1] if d>0 else 1.
          if d==D-1:E[n,b,d]=val;break
          k=int(mi[d]);da=np.full(P,-1,np.int16);bw=np.zeros(P)
          if k>=0:da[:]=SEL[n,b,k];bw[:]=BW[n,b,k]
          sys_event=False;f=1. if da[0]>=0 else 0.
          if da[0]>=0 and use_governor:
            pg=0.
            for j in range(P):
              if da[j]>=0 and bw[j]>0:pg+=bw[j]*gap[d,da[j]]
            sys_event=((pg<=-.032 and UD1[d]>=.70) or (pg<=-.044 and UNEG[d]>=.75))
            if sys_event:f=.25;cd=3
            elif cd>0:f=.25;cd-=1
            else:f=1.
          tw=bw*f;cw=1.-f
          reb=(d==0 or free>1e-14 or abs(pf-f)>1e-12)
          if not reb:
            for j in range(P):
              if a[j]!=da[j] or abs(pw[j]-bw[j])>1e-12:reb=True;break
          if reb:
            cb=bu*O[d,bil]/val if bu else 0.;cs=su*O[d,shv]/val if su else 0.;cf=free/val if val>0 else 0.
            tv=.5*(abs(cf)+abs(cb-cw*.5)+abs(cs-cw*.5))
            for j in range(P):
              if a[j]<0:continue
              cur=u[j]*O[d,a[j]]/val if u[j]!=0 else 0.;target=0.
              for q in range(P):
                if da[q]==a[j]:target+=tw[q]
              tv+=.5*abs(cur-target)
            for q in range(P):
              if da[q]<0:continue
              found=False
              for j in range(P):
                if a[j]==da[q]:found=True
              if not found:tv+=.5*tw[q]
            val*=1.-cost*tv;a[:]=da;u[:]=0.
            for j in range(P):
              if a[j]>=0 and tw[j]>0:u[j]=tw[j]*val/O[d,a[j]]
            bu=cw*.5*val/O[d,bil];su=cw*.5*val/O[d,shv];free=0.;pf=f;pw[:]=bw
          if use_stops:
            for j in range(P):
              x=a[j]
              if x>=0 and u[j]>0 and (UH[d,x] or SA[d,x]) and (sys_event or UD1[d]>=.55):
                sp=PC[d,x]*(1.-.055)
                if O[d,x]<=sp:free+=u[j]*O[d,x]*(1.-cost);u[j]=0.
                elif L[d,x]<=sp:free+=u[j]*sp*(1.-slip)*(1.-cost);u[j]=0.
          close_val=_value(a,u,free,bu,su,C[d],bil,shv)
          E[n,b,d]=close_val if np.isfinite(close_val) and close_val>0 else (E[n,b,d-1] if d>0 else 1.)
    return E

def met(eq,idx):
    years=(idx[-1]-idx[0]).days/365.25;cagr=eq[:,-1]**(1/years)-1
    dd=eq/np.maximum.accumulate(eq,axis=1)-1;mdd=dd.min(axis=1)
    r=eq[:,1:]/eq[:,:-1]-1;sd=r.std(axis=1);sh=np.divide(r.mean(axis=1),sd,out=np.full(len(eq),np.nan),where=sd>0)*np.sqrt(252)
    return cagr,mdd,sh

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--package',required=True);ap.add_argument('--scores',required=True);ap.add_argument('--output',default='EXECUTION_PARITY');a=ap.parse_args()
    pkg=Path(a.package);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    v6=lm('exec_v6',pkg/'source'/'titanium_reconstruction_v6.py')
    mats=v6.load_mats(pkg/'data');pred=pd.read_parquet(a.scores);pred['signal_date']=pd.to_datetime(pred.signal_date)
    opp=pd.read_csv(pkg/'panels'/'TITANIUM_V3_OPPORTUNITY_OOS_CLUSTER_PANEL.csv',parse_dates=['signal_date']);clusters=pd.read_csv(pkg/'panels'/'DYNAMIC_CLUSTERS_MONTHLY.csv',parse_dates=['signal_date']);cal=pd.read_csv(pkg/'panels'/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
    cal=cal[cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    mem=pd.read_csv(pkg/'panels'/'BASKET_MEMBERSHIP_500.csv');baskets=[tuple(sorted(g.ticker.astype(str))) for _,g in mem.groupby('basket',sort=True)]
    idx,ticks,ti,O,L,C,PC,gap,UD1,UNEG,UH,SA,ei,xi,mi=v6.prepare_sim_inputs(mats,cal)
    bs,bw,ds,dw,margin,cond=v6.build_target_arrays(baskets,pred,opp,clusters,pd.DatetimeIndex(cal.signal_date),ti,mats['Open'],pd.DatetimeIndex(cal.entry_date))
    SEL=bs[None,:,:,:];BW=bw[None,:,:,:]
    variants=[('AUG6_GOV_STOPS',True,True),('NO_GOV_NO_STOPS',False,False),('GOV_NO_STOPS',True,False),('NO_GOV_STOPS',False,True)]
    rows=[];payload={'dates':idx.to_numpy('datetime64[ns]')}
    for name,g,s in variants:
        eq=sim_flagged(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV'],.001,.001,g,s)[0]
        c,m,sh=met(eq,idx);payload[name]=eq
        rows.append({'variant':name,'mean_cagr':float(c.mean()),'median_cagr':float(np.median(c)),'mean_maxdd':float(m.mean()),'median_maxdd':float(np.median(m)),'mean_sharpe':float(np.nanmean(sh)),'p05_cagr':float(np.quantile(c,.05)),'p95_cagr':float(np.quantile(c,.95))})
    pd.DataFrame(rows).to_csv(out/'EXECUTION_VARIANTS.csv',index=False);np.savez_compressed(out/'EXECUTION_VARIANT_PATHS.npz',**payload)
    # Regime diagnostics for reconstructed state.
    pd.DataFrame({'date':idx,'UD1':UD1,'UNEG':UNEG,'UH_fraction':UH.mean(axis=1),'SA_fraction':SA.mean(axis=1)}).to_csv(out/'RECONSTRUCTED_REGIME_DIAGNOSTICS.csv',index=False)
    summary={'official_frozen_base_cagr':.21654064,'variants':rows,'UD1_ge_055_days':int((UD1>=.55).sum()),'UD1_ge_070_days':int((UD1>=.70).sum()),'UNEG_ge_075_days':int((UNEG>=.75).sum()),'UH_mean_fraction':float(UH.mean()),'SA_mean_fraction':float(SA.mean())};(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
