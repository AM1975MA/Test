#!/usr/bin/env python3
from pathlib import Path
import argparse, json, numpy as np, pandas as pd
from numba import njit, prange

@njit(cache=False)
def _value(a,u,free,bu,su,p,bil,shv):
    v=free+bu*p[bil]+su*p[shv]
    for j in range(len(a)):
        if a[j]>=0 and u[j]!=0: v+=u[j]*p[a[j]]
    return v

@njit(parallel=True,cache=False)
def exact_sim(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,bil,shv,cost=.001,slip=.001):
    N,B,K,P=SEL.shape; D=len(mi); E=np.ones((N,B,D))
    for n in prange(N):
      for b in range(B):
        a=np.full(P,-1,np.int16); u=np.zeros(P); bu=0.; su=0.; free=0.; pf=-1.; pw=np.full(P,-9.); cd=0
        for d in range(D):
          val=_value(a,u,free,bu,su,O[d],bil,shv)
          if d==0 and val==0: val=1.
          if d==D-1:
            E[n,b,d]=val; break
          k=int(mi[d]); da=np.full(P,-1,np.int16); bw=np.zeros(P)
          if k>=0: da[:]=SEL[n,b,k]; bw[:]=BW[n,b,k]
          sys_event=False; f=0.
          if da[0]>=0:
            pg=0.
            for j in range(P):
              if da[j]>=0 and bw[j]>0: pg+=bw[j]*gap[d,da[j]]
            sys_event=((pg<=-.032 and UD1[d]>=.70) or (pg<=-.044 and UNEG[d]>=.75))
            if sys_event: f=.25; cd=3
            elif cd>0: f=.25; cd-=1
            else: f=1.
          tw=bw*f; cw=1.-f
          reb=(d==0 or free>1e-14 or abs(pf-f)>1e-12)
          if not reb:
            for j in range(P):
              if a[j]!=da[j] or abs(pw[j]-bw[j])>1e-12: reb=True; break
          if reb:
            cb=bu*O[d,bil]/val if bu else 0.; cs=su*O[d,shv]/val if su else 0.; cf=free/val if val>0 else 0.
            tv=.5*(abs(cf)+abs(cb-cw*.5)+abs(cs-cw*.5))
            for j in range(P):
              cur=u[j]*O[d,a[j]]/val if a[j]>=0 and u[j]!=0 else 0.
              tv += .5*(abs(cur)+tw[j]) if a[j]!=da[j] else .5*abs(cur-tw[j])
            val*=1.-cost*tv
            a[:]=da; u[:]=0.
            for j in range(P):
              if a[j]>=0 and tw[j]>0: u[j]=tw[j]*val/O[d,a[j]]
            bu=cw*.5*val/O[d,bil]; su=cw*.5*val/O[d,shv]; free=0.; pf=f; pw[:]=bw
          for j in range(P):
            x=a[j]
            if x>=0 and u[j]>0 and (UH[d,x] or SA[d,x]) and (sys_event or UD1[d]>=.55):
              sp=PC[d,x]*(1.-.055)
              fill=O[d,x] if O[d,x]<=sp else (sp*(1.-slip) if L[d,x]<=sp else 0.)
              if fill>0:
                free += u[j]*fill*(1.-cost); u[j]=0.; cd=max(cd,3)
          E[n,b,d]=_value(a,u,free,bu,su,O[d+1],bil,shv)
    return E

def metrics(eq,dates):
    years=(dates[-1]-dates[0]).days/365.25
    cagr=eq[-1]**(1/years)-1
    dd=eq/np.maximum.accumulate(eq)-1
    r=eq[1:]/eq[:-1]-1
    sh=np.sqrt(252)*np.nanmean(r)/np.nanstd(r) if np.nanstd(r)>0 else np.nan
    return cagr,float(np.nanmin(dd)),float(sh),float(eq[-1])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package',required=True); ap.add_argument('--output',default='EXACT_FROZEN_EXECUTION')
    a=ap.parse_args(); root=Path(a.package); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    paths=np.load(root/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz',allow_pickle=True)
    dates=pd.DatetimeIndex(paths['dates'])
    Odf=pd.read_parquet(root/'OPEN.parquet').reindex(dates).ffill().bfill()
    Ldf=pd.read_parquet(root/'LOW.parquet').reindex(dates).ffill().bfill()
    Cdf=pd.read_parquet(root/'CLOSE.parquet').reindex(dates).ffill().bfill()
    ticks=list(Odf.columns); ti={t:i for i,t in enumerate(ticks)}
    O=Odf.to_numpy(float); L=Ldf.to_numpy(float); C=Cdf.to_numpy(float)
    gap=np.zeros_like(O); gap[1:]=O[1:]/C[:-1]-1.
    UD1=np.mean(gap<-.01,axis=1); UNEG=np.mean(gap<0.,axis=1)
    hist=Cdf; m3=hist/hist.shift(3)-1; m5=hist/hist.shift(5)-1; sma10=hist.rolling(10).mean(); sma20=hist.rolling(20).mean()
    UH=((((hist<sma10)&(m3<0))|((hist<sma20)&(m5<-.015))).shift(1).fillna(False)).to_numpy(bool)
    SA=(((m5<-.04)|((hist<sma20)&(m3<-.025))).shift(1).fillna(False)).to_numpy(bool)
    PC=np.empty_like(C); PC[0]=O[0]; PC[1:]=C[:-1]
    cal=pd.read_csv(root/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']).sort_values('signal_date').reset_index(drop=True)
    mi=np.full(len(dates),-1,np.int16)
    for k,r in cal.iterrows():
      aa=dates.get_loc(r.entry_date); ee=dates.get_loc(r.exit_date); mi[aa:ee]=k
    z=np.load(root/'TARGET_ARRAYS_500.npz',allow_pickle=True)
    def pad(sel,w):
      B,K,Q=sel.shape; S=np.full((B,K,4),-1,np.int16); W=np.zeros((B,K,4),float); S[:,:,:Q]=sel; W[:,:,:Q]=w; return S,W
    bs,bw=pad(z['base_sel'].astype(np.int16),z['base_w'].astype(float)); ds,dw=pad(z['direct_sel'].astype(np.int16),z['direct_w'].astype(float))
    active=z['router_active'].astype(bool); rs=bs.copy(); rw=bw.copy(); rs[:,active,:]=ds[:,active,:]; rw[:,active,:]=dw[:,active,:]
    SEL=np.stack([bs,ds,rs]); BW=np.stack([bw,dw,rw])
    E=exact_sim(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV'])
    rows=[]
    for si,name in enumerate(['BASE','DIRECT','ROUTER']):
      for b in range(E.shape[1]):
        c,dd,sh,fe=metrics(E[si,b],dates); rows.append({'strategy':name,'basket':b,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe})
    res=pd.DataFrame(rows); res.to_csv(out/'BASKET_RESULTS_EXACT_EXECUTION.csv',index=False)
    np.savez_compressed(out/'EXACT_EXECUTION_PATHS.npz',BASE=E[0],DIRECT=E[1],ROUTER=E[2],dates=dates.values)
    old=[]
    for name in ['BASE','DIRECT','ROUTER']:
      arr=paths[name]; vals=[metrics(arr[b],dates) for b in range(arr.shape[0])]
      old.append({'strategy':name,'old_mean_cagr':float(np.mean([x[0] for x in vals]))})
    summary=[]
    for name in ['BASE','DIRECT','ROUTER']:
      q=res[res.strategy==name]
      oldc=next(x['old_mean_cagr'] for x in old if x['strategy']==name)
      summary.append({'strategy':name,'exact_mean_cagr':q.cagr.mean(),'exact_median_cagr':q.cagr.median(),'exact_median_maxdd':q.maxdd.median(),'exact_mean_sharpe':q.sharpe.mean(),'old_mean_cagr':oldc,'execution_delta_pp':100*(q.cagr.mean()-oldc)})
    sm=pd.DataFrame(summary); sm.to_csv(out/'SUMMARY.csv',index=False)
    payload={'dates':len(dates),'baskets':500,'months':len(cal),'router_active_months':int(active.sum()),'official_v2_mean_cagr':.21654064,'official_router_mean_cagr':.22742810,'summary':summary}
    (out/'SUMMARY.json').write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2))
if __name__=='__main__': main()
