#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit, prange

REF = {
    'D1': 0.15022713687299,
    'D2': 0.2264479079604543,
    'DEV': 0.1861726630584223,
    'HOLD': 0.2760542274772661,
    'FULL': 0.2165406437471759,
}
PERIODS = {
    'D1': ('2017-01-01','2019-12-31'),
    'D2': ('2020-01-01','2022-12-31'),
    'DEV': ('2017-01-01','2022-12-31'),
    'HOLD': ('2023-01-01','2026-12-31'),
    'FULL': ('2017-01-01','2026-12-31'),
}

@njit(cache=False)
def _value(a,u,free,bu,su,p,bil,shv):
    v=free+bu*p[bil]+su*p[shv]
    for j in range(len(a)):
        if a[j]>=0 and u[j]!=0: v += u[j]*p[a[j]]
    return v

@njit(parallel=True,cache=False)
def exact_sim(SEL,BW,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,bil,shv,cost=.001,slip=.001):
    B,K,P=SEL.shape; D=len(mi); E=np.ones((B,D))
    for b in prange(B):
        a=np.full(P,-1,np.int16); u=np.zeros(P); bu=0.; su=0.; free=1.; pf=-1.; pw=np.full(P,-9.); cd=0
        for d in range(D):
            val=_value(a,u,free,bu,su,O[d],bil,shv)
            if not np.isfinite(val) or val<=0: val=E[b,d-1] if d>0 else 1.
            if d==D-1:
                E[b,d]=val; break
            k=int(mi[d]); da=np.full(P,-1,np.int16); bw=np.zeros(P)
            if k>=0: da[:]=SEL[b,k]; bw[:]=BW[b,k]
            sys_event=False; f=0.
            if da[0]>=0:
                pg=0.
                for j in range(P):
                    if da[j]>=0 and bw[j]>0: pg += bw[j]*gap[d,da[j]]
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
                    if a[j] < 0: continue
                    cur=u[j]*O[d,a[j]]/val if u[j]!=0 else 0.; target=0.
                    for q in range(P):
                        if da[q]==a[j]: target += tw[q]
                    tv += .5*abs(cur-target)
                for q in range(P):
                    if da[q] < 0: continue
                    found=False
                    for j in range(P):
                        if a[j]==da[q]: found=True
                    if not found: tv += .5*tw[q]
                val *= 1.-cost*tv
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
            E[b,d]=_value(a,u,free,bu,su,O[d+1],bil,shv)
    return E

def cagr_slice(eq: np.ndarray, dates: pd.DatetimeIndex, start: str, end: str) -> np.ndarray:
    q=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end))
    ix=np.where(q)[0]
    if len(ix)<2: return np.full(eq.shape[0],np.nan)
    a,b=ix[0],ix[-1]; years=(dates[b]-dates[a]).days/365.25
    return (eq[:,b]/eq[:,a])**(1/years)-1

def maxdd_slice(eq,dates,start,end):
    q=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end)); x=eq[:,q]
    if x.shape[1]<2: return np.full(eq.shape[0],np.nan)
    return np.min(x/np.maximum.accumulate(x,axis=1)-1,axis=1)

def prepare(root: Path):
    score=pd.read_parquet(root/'OOS_TICKER_SCORES.parquet')
    score['signal_date']=pd.to_datetime(score.signal_date)
    mem=pd.read_csv(root/'BASKET_MEMBERSHIP_500.csv')
    cal=pd.read_csv(root/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']).sort_values('signal_date').reset_index(drop=True)
    paths=np.load(root/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz',allow_pickle=True)
    dates=pd.DatetimeIndex(paths['dates'])
    Odf=pd.read_parquet(root/'OPEN.parquet').reindex(dates).ffill().bfill()
    Ldf=pd.read_parquet(root/'LOW.parquet').reindex(dates).ffill().bfill()
    Cdf=pd.read_parquet(root/'CLOSE.parquet').reindex(dates).ffill().bfill()
    ticks=list(Odf.columns.astype(str)); ti={t:i for i,t in enumerate(ticks)}
    months=pd.DatetimeIndex(cal.signal_date)
    # restrict to months present in the score panel, preserving calendar order
    common=months.intersection(pd.DatetimeIndex(score.signal_date.unique())).sort_values()
    cal=cal[cal.signal_date.isin(common)].reset_index(drop=True); months=pd.DatetimeIndex(cal.signal_date)
    score=score[score.signal_date.isin(months) & score.ticker.isin(ticks)].copy()
    K=len(months); T=len(ticks); mi_t={d:i for i,d in enumerate(months)}
    S=np.full((K,T),np.nan); CP=np.full_like(S,np.nan); TR=np.full_like(S,np.nan)
    for r in score[['signal_date','ticker','titanium_score','compact_rank','tail_rank']].itertuples(index=False):
        k=mi_t.get(pd.Timestamp(r.signal_date)); j=ti.get(str(r.ticker))
        if k is not None and j is not None:
            S[k,j]=float(r.titanium_score); CP[k,j]=float(r.compact_rank); TR[k,j]=float(r.tail_rank)
    # basket index arrays
    baskets=[]
    for b in sorted(mem.basket.unique()):
        names=mem.loc[mem.basket.eq(b),'ticker'].astype(str).tolist(); ids=[ti[t] for t in names if t in ti]
        baskets.append(np.array(ids,dtype=np.int16))
    if len(baskets)!=500: raise RuntimeError(f'expected 500 baskets, got {len(baskets)}')
    # raw order per basket/month, high score is better
    raw_order=np.full((500,K,24),-1,np.int16)
    for b,ids in enumerate(baskets):
        for k in range(K):
            good=ids[np.isfinite(S[k,ids])]
            if len(good):
                o=good[np.argsort(-S[k,good],kind='mergesort')]
                raw_order[b,k,:min(24,len(o))]=o[:24]
    # realized monthly open-open returns for causal switch-profit history
    R=np.full((K,T),np.nan)
    for k,r in cal.iterrows():
        try: a=dates.get_loc(r.entry_date); e=dates.get_loc(r.exit_date)
        except KeyError: continue
        if e>a: R[k]=Odf.iloc[e].to_numpy(float)/Odf.iloc[a].to_numpy(float)-1.
    # daily simulator inputs
    O=Odf.to_numpy(float); L=Ldf.to_numpy(float); C=Cdf.to_numpy(float)
    gap=np.zeros_like(O); gap[1:]=O[1:]/C[:-1]-1.
    UD1=np.mean(gap<-.01,axis=1); UNEG=np.mean(gap<0.,axis=1)
    hist=Cdf; m3=hist/hist.shift(3)-1; m5=hist/hist.shift(5)-1; sma10=hist.rolling(10).mean(); sma20=hist.rolling(20).mean()
    UH=((((hist<sma10)&(m3<0))|((hist<sma20)&(m5<-.015))).shift(1).fillna(False)).to_numpy(bool)
    SA=(((m5<-.04)|((hist<sma20)&(m3<-.025))).shift(1).fillna(False)).to_numpy(bool)
    PC=np.empty_like(C); PC[0]=O[0]; PC[1:]=C[:-1]
    mi=np.full(len(dates),-1,np.int16)
    for k,r in cal.iterrows():
        try: a=dates.get_loc(r.entry_date); e=dates.get_loc(r.exit_date)
        except KeyError: continue
        mi[a:e]=k
    return score,cal,dates,ticks,ti,S,CP,TR,R,raw_order,O,L,C,PC,gap,UD1,UNEG,UH,SA,mi,paths

def state_from_hist(hist, rule):
    x=np.asarray(hist[-24:],float); x=x[np.isfinite(x)]
    if len(x)<6: return 'neutral'
    m=float(np.mean(x)); hit=float(np.mean(x>0))
    if rule=='sign': return 'fast' if m>0 else ('slow' if m<0 else 'neutral')
    if rule=='dead25': return 'fast' if m>.0025 else ('slow' if m<-.0025 else 'neutral')
    if rule=='dead50': return 'fast' if m>.005 else ('slow' if m<-.005 else 'neutral')
    if rule=='hit55': return 'fast' if hit>.55 else ('slow' if hit<.45 else 'neutral')
    raise ValueError(rule)

def build_reg24(S,CP,TR,R,raw_order, state_rule='sign', hist_mode='opportunity', weak='immediate', consensus='both'):
    B,K,_=raw_order.shape
    selected=np.full((B,K),-1,np.int16); states=np.zeros((B,K),np.int8); switch=np.zeros((B,K),bool)
    state_code={'fast':1,'neutral':2,'slow':3}; thresholds={'fast':.005,'neutral':.03,'slow':.08}; keep_rank={'fast':2,'neutral':3,'slow':5}
    for b in range(B):
        hist=[]; incumbent=int(raw_order[b,0,0]); selected[b,0]=incumbent; states[b,0]=2
        prev_inc_pre=incumbent; prev_chal=incumbent; prev_sw=False
        for k in range(1,K):
            # At month k, append only month k-1 realized information.
            if prev_chal>=0 and prev_inc_pre>=0 and prev_chal!=prev_inc_pre and np.isfinite(R[k-1,prev_chal]) and np.isfinite(R[k-1,prev_inc_pre]):
                adv=float(R[k-1,prev_chal]-R[k-1,prev_inc_pre])
                if hist_mode=='opportunity' or (hist_mode=='actual' and prev_sw): hist.append(adv)
            st=state_from_hist(hist,state_rule); states[b,k]=state_code[st]
            order=raw_order[b,k]; chal=int(order[0]); inc=int(incumbent)
            if chal<0:
                selected[b,k]=inc; prev_inc_pre=inc; prev_chal=inc; prev_sw=False; continue
            ranks={int(x):i+1 for i,x in enumerate(order) if x>=0}; inc_rank=ranks.get(inc,99)
            gap=float(S[k,chal]-S[k,inc]) if inc>=0 and np.isfinite(S[k,inc]) else 1.
            thr=thresholds[st]
            agree=0
            if inc>=0:
                if np.isfinite(CP[k,chal]) and np.isfinite(CP[k,inc]) and CP[k,chal]>CP[k,inc]: agree+=1
                if np.isfinite(TR[k,chal]) and np.isfinite(TR[k,inc]) and TR[k,chal]>TR[k,inc]: agree+=1
                if gap>0: agree+=1  # blended Titanium expert
            if consensus=='both' and agree>=3: thr*=.70
            elif consensus=='two' and agree>=2: thr*=.70
            weak_inc=inc_rank>keep_rank[st]
            do=False
            if chal!=inc:
                if weak=='immediate' and weak_inc: do=True
                elif weak=='half' and gap >= thr*(.5 if weak_inc else 1.): do=True
                elif weak=='normal' and gap>=thr: do=True
                elif not weak_inc and gap>=thr: do=True
            prev_inc_pre=inc; prev_chal=chal; prev_sw=do
            if do: incumbent=chal; switch[b,k]=True
            selected[b,k]=incumbent
    return selected,states,switch

def targets_from_selected(selected,S,raw_order):
    B,K=selected.shape; sel=np.full((B,K,4),-1,np.int16); w=np.zeros((B,K,4),float); margins=np.full((B,K),np.nan)
    for b in range(B):
        for k in range(K):
            t1=int(selected[b,k]); order=raw_order[b,k]; t2=-1
            for x in order:
                if x>=0 and int(x)!=t1: t2=int(x); break
            if t1<0: continue
            sel[b,k,0]=t1
            if t2>=0:
                margins[b,k]=S[k,t1]-S[k,t2]
                if margins[b,k]>=.12: w[b,k,0]=1.
                else: sel[b,k,1]=t2; w[b,k,0]=.75; w[b,k,1]=.25
            else: w[b,k,0]=1.
    return sel,w,margins

def summarize(name,E,dates,selected,switch,states):
    row={'variant':name,'mean_switches':float(switch.sum(axis=1).mean()),'median_switches':float(np.median(switch.sum(axis=1))),
         'fast_frac':float(np.mean(states==1)),'neutral_frac':float(np.mean(states==2)),'slow_frac':float(np.mean(states==3))}
    errs=[]
    for p,(a,b) in PERIODS.items():
        c=cagr_slice(E,dates,a,b); row[p+'_cagr']=float(np.nanmean(c)); row[p+'_median_cagr']=float(np.nanmedian(c)); row[p+'_err_pp']=100*(row[p+'_cagr']-REF[p])
        dd=maxdd_slice(E,dates,a,b); row[p+'_median_maxdd']=float(np.nanmedian(dd))
        if p in ('D1','D2','DEV'): errs.append((row[p+'_cagr']-REF[p])**2)
    row['DEV_RMSE_pp']=100*math.sqrt(sum(errs)/len(errs))
    return row

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package',required=True); ap.add_argument('--output',default='REG24_RECOVERY'); a=ap.parse_args()
    root=Path(a.package); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    score,cal,dates,ticks,ti,S,CP,TR,R,raw_order,O,L,C,PC,gap,UD1,UNEG,UH,SA,mi,paths=prepare(root)
    rows=[]; best_payload=None
    # sanity: raw no-hysteresis path rebuilt using frozen V2 concentration rule
    rawsel=raw_order[:,:,0].copy(); zstate=np.full(rawsel.shape,2,np.int8); zsw=np.zeros(rawsel.shape,bool); zsw[:,1:]=rawsel[:,1:]!=rawsel[:,:-1]
    sel,w,_=targets_from_selected(rawsel,S,raw_order); E=exact_sim(sel,w,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV']); rows.append(summarize('RAW_NO_HYSTERESIS',E,dates,rawsel,zsw,zstate))
    variants=[]
    for sr in ['sign','dead25','dead50','hit55']:
      for hm in ['opportunity','actual']:
       for weak in ['immediate','half','normal']:
        for cons in ['both','two','none']:
          variants.append((sr,hm,weak,cons))
    for sr,hm,weak,cons in variants:
        selected,states,sw=build_reg24(S,CP,TR,R,raw_order,sr,hm,weak,cons)
        sel,w,m=targets_from_selected(selected,S,raw_order)
        E=exact_sim(sel,w,mi,O,L,C,PC,gap,UD1,UNEG,UH,SA,ti['BIL'],ti['SHV'])
        name=f'REG24_{sr}_{hm}_{weak}_{cons}'
        row=summarize(name,E,dates,selected,sw,states); rows.append(row)
        if best_payload is None or row['DEV_RMSE_pp']<best_payload[0]:
            best_payload=(row['DEV_RMSE_pp'],name,selected.copy(),states.copy(),sw.copy(),sel.copy(),w.copy(),E.copy())
        print(name, 'DEV_RMSE_pp=',round(row['DEV_RMSE_pp'],4),'FULL=',round(row['FULL_cagr']*100,3),'switches=',round(row['mean_switches'],1),flush=True)
    res=pd.DataFrame(rows).sort_values(['DEV_RMSE_pp','FULL_err_pp'],key=lambda x:abs(x) if x.name=='FULL_err_pp' else x)
    res.to_csv(out/'REG24_VARIANT_SCORECARD.csv',index=False)
    # top variants, hold is diagnostic only and was not used in ranking
    res.head(20).to_csv(out/'REG24_TOP20.csv',index=False)
    _,bn,bsel,bst,bSW,bS,bW,bE=best_payload
    np.savez_compressed(out/'BEST_REG24_PATHS.npz',selected=bsel,states=bst,switches=bSW,sel=bS,weights=bW,equity=bE,dates=dates.values,months=pd.DatetimeIndex(cal.signal_date).values,tickers=np.array(ticks,dtype=object))
    # known unrestricted signal from recovered MAT_d42 panel
    last=pd.Timestamp('2026-06-30'); q=score[score.signal_date.eq(last)].sort_values('titanium_score',ascending=False)
    known={'date':str(last.date()),'top':q[['ticker','titanium_score','compact_rank','tail_rank']].head(10).to_dict('records'),'matches_USO_PALL':bool(len(q)>=2 and q.iloc[0].ticker=='USO' and q.iloc[1].ticker=='PALL')}
    (out/'KNOWN_SIGNAL_CHECK.json').write_text(json.dumps(known,indent=2))
    meta={'reference':REF,'selection_basis':'ranked ONLY by D1/D2/DEV RMSE; HOLD not used for variant selection','n_variants':len(res),'best_variant':bn,'best':res.iloc[0].to_dict(),'known_signal':known}
    (out/'SUMMARY.json').write_text(json.dumps(meta,indent=2,default=float))
    print('\nTOP 10\n',res[['variant','D1_cagr','D2_cagr','DEV_cagr','HOLD_cagr','FULL_cagr','DEV_RMSE_pp','mean_switches']].head(10).to_string(index=False))
    print(json.dumps(meta,indent=2,default=float))

if __name__=='__main__': main()
