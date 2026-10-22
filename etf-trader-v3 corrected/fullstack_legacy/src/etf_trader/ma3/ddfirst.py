"""MA3 DD-first systemic risk controller, rebuilt from source-only inputs.

This module contains the exact SYNC_C95_M75 logic frozen on 2026-09-22.
It accepts raw price matrices plus source-generated monthly allocations.
No historical score/path/decision artifact is a productive input.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit


def market_state(close: pd.DataFrame) -> dict[str, np.ndarray]:
    """Prior-close systemic state aligned to each current-open session."""
    close=close.astype(float)
    spy=close["SPY"]
    spyret=spy.pct_change(fill_method=None)
    ma200=spy.rolling(200,min_periods=150).mean()
    sv=(spy/ma200-1).shift(1).fillna(0.0)

    ret21=close/close.shift(21)-1
    ret63=close/close.shift(63)-1
    b21=(ret21>0).mean(axis=1).shift(1).fillna(.5)
    b63=(ret63>0).mean(axis=1).shift(1).fillna(.5)
    v20=(spyret.rolling(20,min_periods=15).std()*np.sqrt(252)).shift(1).fillna(.15)

    hygief=close["HYG"]/close["IEF"]
    credit21=(hygief/hygief.shift(21)-1).shift(1).fillna(0.0)

    ma63=close.rolling(63,min_periods=40).mean()
    ma126=close.rolling(126,min_periods=80).mean()
    ba63=(close>ma63).mean(axis=1).shift(1).fillna(.5)
    ba126=(close>ma126).mean(axis=1).shift(1).fillna(.5)
    return {
        "spy_vs200":sv.to_numpy(float),
        "breadth21":b21.to_numpy(float),
        "breadth63":b63.to_numpy(float),
        "vol20":v20.to_numpy(float),
        "credit21":credit21.to_numpy(float),
        "above_ma63":ba63.to_numpy(float),
        "above_ma126":ba126.to_numpy(float),
    }


def sync_c95_m75_gross(close: pd.DataFrame) -> np.ndarray:
    """Exact DD-first gross ladder selected on 2017-2022.

    Fewer than 3 weakness votes -> 1.00
    3 votes -> 0.95
    4+ votes -> 0.75
    Severe synchronized state -> 0.25
    """
    s=market_state(close)
    weak=(
        (s["spy_vs200"]<-.025).astype(np.int8)
        +(s["breadth63"]<.40).astype(np.int8)
        +(s["above_ma126"]<.40).astype(np.int8)
        +(s["credit21"]<0).astype(np.int8)
        +(s["vol20"]>.20).astype(np.int8)
    )
    severe=(
        (s["spy_vs200"]<-.08)
        &(s["breadth21"]<.32)
        &(s["above_ma63"]<.32)
        &(s["vol20"]>.24)
    )
    gross=np.ones(len(close),dtype=float)
    gross[weak>=3]=.95
    gross[weak>=4]=.75
    gross[severe]=.25
    return gross


def daily_execution_inputs(
    open_: pd.DataFrame,
    low: pd.DataFrame,
    close: pd.DataFrame,
) -> dict[str,np.ndarray]:
    """Build the authenticated V2 daily risk inputs solely from OHLC."""
    cols=list(open_.columns)
    low=low.reindex(index=open_.index,columns=cols).astype(float)
    close=close.reindex(index=open_.index,columns=cols).astype(float)
    open_=open_.astype(float)

    O=open_.to_numpy(float);L=low.to_numpy(float);C=close.to_numpy(float)
    gap=np.zeros_like(O);gap[1:]=O[1:]/C[:-1]-1
    ud1=np.mean(gap<-.01,axis=1)
    uneg=np.mean(gap<0,axis=1)

    m3=close/close.shift(3)-1
    m5=close/close.shift(5)-1
    s10=close.rolling(10).mean()
    s20=close.rolling(20).mean()
    UH=((((close<s10)&(m3<0))|((close<s20)&(m5<-.015))).shift(1).fillna(False)).to_numpy(bool)
    SA=(((m5<-.04)|((close<s20)&(m3<-.025))).shift(1).fillna(False)).to_numpy(bool)

    PC=np.empty_like(C);PC[0]=O[0];PC[1:]=C[:-1]
    return {"O":O,"L":L,"C":C,"PC":PC,"gap":gap,"ud1":ud1,"uneg":uneg,"UH":UH,"SA":SA}


@njit(cache=True)
def simulate_ddfirst(
    d1,d2,wg,O,L,C,PC,gap,ud1,uneg,UH,SA,bil,shv,G,
    cost=.001,stop=.055,slip=.001,
):
    """Authenticated exact-daily V2 execution with DD-first gross cap."""
    B,D=d1.shape
    E=np.ones((B,D));T=np.zeros((B,D));X=np.ones((B,D))
    for bb in range(B):
        t1=-1;t2=-1;u1=0.;u2=0.;bu=0.;su=0.;free=0.;pw1=-1.;pf=-1.;cd=0
        for k in range(D):
            val=free
            if t1>=0 and u1: val+=u1*O[k,t1]
            if t2>=0 and u2: val+=u2*O[k,t2]
            if bu: val+=bu*O[k,bil]
            if su: val+=su*O[k,shv]
            if k==0 and val==0: val=1.
            if k==D-1:
                E[bb,k]=val;X[bb,k]=min(1.,G[k]);break

            nt1=d1[bb,k];nt2=d2[bb,k];w1=wg[bb,k]
            if nt2==nt1:w1=1.
            p1=False;p2=False;sysm=False;basef=1.
            if nt1<0:
                basef=0.
            else:
                p1=UH[k,nt1] or SA[k,nt1]
                if nt2>=0:p2=UH[k,nt2] or SA[k,nt2]
                g1=gap[k,nt1];g2=gap[k,nt2] if nt2>=0 else g1
                pg=w1*g1+(1-w1)*g2
                sysm=((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))
                if sysm:
                    basef=.25;cd=3
                elif cd>0:
                    basef=.25;cd-=1

            f=min(basef,G[k]);rw1=f*w1;rw2=f*(1-w1);cw=1-f
            reb=(t1!=nt1) or (t2!=nt2) or abs(pw1-w1)>1e-12 or abs(pf-f)>1e-12 or free>1e-14 or k==0
            if reb:
                c1=u1*O[k,t1]/val if t1>=0 and u1 else 0.
                c2=u2*O[k,t2]/val if t2>=0 and u2 else 0.
                cb=bu*O[k,bil]/val if bu else 0.
                cs=su*O[k,shv]/val if su else 0.
                cf=free/val if val>0 else 0.
                tv=.5*(abs(cf)+abs(cb-cw*.5)+abs(cs-cw*.5))
                tv+=.5*((abs(c1)+rw1) if t1!=nt1 else abs(c1-rw1))
                tv+=.5*((abs(c2)+rw2) if t2!=nt2 else abs(c2-rw2))
                val*=1-cost*tv;T[bb,k]=tv
                t1=nt1;t2=nt2
                u1=rw1*val/O[k,t1] if t1>=0 and rw1>0 else 0.
                u2=rw2*val/O[k,t2] if t2>=0 and rw2>0 else 0.
                bu=cw*.5*val/O[k,bil];su=cw*.5*val/O[k,shv]
                free=0.;pw1=w1;pf=f

            if t1>=0 and u1>0 and p1 and (sysm or ud1[k]>=.55):
                sp=PC[k,t1]*(1-stop)
                fill=O[k,t1] if O[k,t1]<=sp else (sp*(1-slip) if L[k,t1]<=sp else 0.)
                if fill>0:
                    free+=u1*fill*(1-cost);u1=0.;cd=max(cd,3)
            if t2>=0 and u2>0 and p2 and (sysm or ud1[k]>=.55):
                sp=PC[k,t2]*(1-stop)
                fill=O[k,t2] if O[k,t2]<=sp else (sp*(1-slip) if L[k,t2]<=sp else 0.)
                if fill>0:
                    free+=u2*fill*(1-cost);u2=0.;cd=max(cd,3)

            nv=free
            if t1>=0 and u1:nv+=u1*O[k+1,t1]
            if t2>=0 and u2:nv+=u2*O[k+1,t2]
            if bu:nv+=bu*O[k+1,bil]
            if su:nv+=su*O[k+1,shv]
            E[bb,k]=nv;X[bb,k]=f
    return E,T,X
