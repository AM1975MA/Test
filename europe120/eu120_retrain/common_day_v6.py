"""MA3 V6 resilient-alternative layer from source-only price and allocation inputs."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numba import njit


QUALITY = 0.72
REL_M5 = 0.015
REL_M21 = 0.005
REL_DD21 = 0.015
REL_SOLIDITY = 0.05


@dataclass(frozen=True)
class V6State:
    recovery: np.ndarray
    alt_idx: np.ndarray
    solidity: np.ndarray
    ret5: np.ndarray
    ret21: np.ndarray
    ret63: np.ndarray
    dd21: np.ndarray
    vol20: np.ndarray


def _pct_by_day(x: np.ndarray) -> np.ndarray:
    out=np.full_like(x,np.nan,dtype=float)
    for t in range(x.shape[0]):
        ok=np.isfinite(x[t])
        n=int(ok.sum())
        if n<2:
            continue
        o=np.argsort(x[t,ok])
        r=np.empty(n,dtype=float)
        r[o]=(np.arange(n,dtype=float)+.5)/n
        out[t,ok]=r
    return out


def build_v6_state(
    close: pd.DataFrame,
    d1: np.ndarray,
    d2: np.ndarray,
    weight1: np.ndarray,
    global_gross: np.ndarray,
    *,
    bil_ticker: str = "BIL",
    shv_ticker: str = "SHV",
) -> V6State:
    """Reproduce the frozen V6 recovery and REL_B alternative selector.

    All selector inputs are prior-close causal. ALT can only consume the cash
    created by the systemic gross controller.
    """
    close=close.astype(float)
    tickers=list(map(str,close.columns))
    ti={t:i for i,t in enumerate(tickers)}
    bil=ti[bil_ticker]
    shv=ti[shv_ticker]
    C=close.to_numpy(float)
    D,N=C.shape
    if d1.shape!=(d2.shape) or d1.shape!=weight1.shape:
        raise ValueError("allocation arrays must have equal shape")
    if d1.shape[1]!=D or len(global_gross)!=D:
        raise ValueError("daily state length mismatch")

    ret={}
    for h in (5,21,63):
        a=np.full_like(C,np.nan,dtype=float)
        a[h:]=C[h:]/C[:-h]-1.0
        ret[h]=a

    dd21=np.full_like(C,np.nan,dtype=float)
    vol20=np.full_like(C,np.nan,dtype=float)
    above20=np.zeros(D,dtype=float)
    pos5=np.zeros(D,dtype=float)
    for t in range(20,D):
        w=C[t-20:t+1]
        dd21[t]=C[t]/np.nanmax(w,axis=0)-1.0
        rr=C[t-19:t+1]/C[t-20:t]-1.0
        vol20[t]=np.nanstd(rr,axis=0,ddof=1)
        above20[t]=np.nanmean(C[t]>np.nanmean(C[t-19:t+1],axis=0))
        pos5[t]=np.nanmean(ret[5][t]>0)

    spy=ti["SPY"]
    spy5=ret[5][:,spy]
    ma200=pd.DataFrame(C,index=close.index,columns=tickers).rolling(
        200,min_periods=200
    ).mean().to_numpy()
    spy200=C[:,spy]/ma200[:,spy]-1.0
    pos21=np.nanmean(ret[21]>0,axis=1)

    recovery=np.zeros(D,dtype=bool)
    recovery[1:]=(
        (spy5[:-1]>.025)
        &(pos5[:-1]>.58)
        &(above20[:-1]>.48)
        &(spy200[:-1]<-.03)
        &(pos21[:-1]<.75)
    )

    solidity=np.nanmean(
        np.stack([
            _pct_by_day(ret[5]),
            _pct_by_day(ret[21]),
            _pct_by_day(ret[63]),
            _pct_by_day(dd21),
            _pct_by_day(-vol20),
        ]),
        axis=0,
    )

    ranked={}
    for k in range(65,D-1):
        if not (recovery[k] and global_gross[k]>=.74 and global_gross[k]<.999):
            continue
        t=k-1
        ids=np.arange(N)
        ok=(
            np.isfinite(solidity[t])
            &np.isfinite(ret[5][t])
            &np.isfinite(ret[21][t])
            &np.isfinite(ret[63][t])
            &np.isfinite(dd21[t])
        )
        ids=ids[ok & (np.arange(N)!=bil) & (np.arange(N)!=shv)]
        passed=(
            (ret[5][t,ids]>.005)
            &(ret[21][t,ids]>0)
            &(ret[63][t,ids]>-.03)
            &(dd21[t,ids]>-.07)
            &(solidity[t,ids]>=QUALITY)
        )
        ids=ids[passed]
        if len(ids):
            sc=(
                solidity[t,ids]
                +.20*np.clip(ret[5][t,ids]/.05,-1,1)
                +.10*np.clip(ret[21][t,ids]/.10,-1,1)
            )
            ranked[k]=ids[np.argsort(-sc)]

    alt=np.full(d1.shape,-1,np.int16)
    B=d1.shape[0]
    for b in range(B):
        for k,ids in ranked.items():
            t=k-1
            i1=int(d1[b,k])
            i2=int(d2[b,k])
            w1=float(weight1[b,k])
            if i1<0:
                continue
            j2=i2 if i2>=0 else i1
            o5=w1*ret[5][t,i1]+(1-w1)*ret[5][t,j2]
            o21=w1*ret[21][t,i1]+(1-w1)*ret[21][t,j2]
            odd=w1*dd21[t,i1]+(1-w1)*dd21[t,j2]
            os=w1*solidity[t,i1]+(1-w1)*solidity[t,j2]
            for q in ids:
                qi=int(q)
                if qi==i1 or qi==i2:
                    continue
                if (
                    ret[5][t,qi]>=o5+REL_M5
                    and ret[21][t,qi]>=o21+REL_M21
                    and dd21[t,qi]>=odd+REL_DD21
                    and solidity[t,qi]>=os+REL_SOLIDITY
                ):
                    alt[b,k]=qi
                    break

    return V6State(
        recovery=recovery,
        alt_idx=alt,
        solidity=solidity,
        ret5=ret[5],
        ret21=ret[21],
        ret63=ret[63],
        dd21=dd21,
        vol20=vol20,
    )


@njit(cache=True)
def simulate_with_alt(
    d1,d2,wg,O,L,C,PC,gap,ud1,uneg,UH,SA,bil,shv,G,ALT,use_alt,tradeable,
    cost=.001,stop=.055,slip=.001,
):
    """Exact-daily V6 execution engine."""
    B,D=d1.shape
    E=np.ones((B,D))
    T=np.zeros((B,D))
    X=np.ones((B,D))
    AW=np.zeros((B,D))
    for bb in range(B):
        t1=-1;t2=-1;at=-1
        u1=0.;u2=0.;au=0.;bu=0.;su=0.;free=0.
        pw1=-1.;pf=-1.;paw=-1.;cd=0
        for k in range(D):
            val=free
            if t1>=0 and u1:val+=u1*O[k,t1]
            if t2>=0 and u2:val+=u2*O[k,t2]
            if at>=0 and au:val+=au*O[k,at]
            if bu:val+=bu*O[k,bil]
            if su:val+=su*O[k,shv]
            if k==0 and val==0:val=1.
            if k==D-1:
                E[bb,k]=val
                X[bb,k]=min(1.,G[k])
                break

            # The universe spans exchanges with different holidays. Mark the
            # current holdings at available/stale quotes, but execute no
            # trades or stops until every instrument has a real session open.
            if not tradeable[k]:
                nv=free
                if t1>=0 and u1:nv+=u1*O[k+1,t1]
                if t2>=0 and u2:nv+=u2*O[k+1,t2]
                if at>=0 and au:nv+=au*O[k+1,at]
                if bu:nv+=bu*O[k+1,bil]
                if su:nv+=su*O[k+1,shv]
                E[bb,k]=nv
                X[bb,k]=pf if pf>=0 else 0.
                AW[bb,k]=paw if paw>=0 else 0.
                continue

            nt1=d1[bb,k];nt2=d2[bb,k];w1=wg[bb,k]
            if nt2==nt1:w1=1.
            p1=False;p2=False;sysm=False;basef=1.
            if nt1<0:
                basef=0.
            else:
                p1=UH[k,nt1] or SA[k,nt1]
                if nt2>=0:p2=UH[k,nt2] or SA[k,nt2]
                g1=gap[k,nt1]
                g2=gap[k,nt2] if nt2>=0 else g1
                pg=w1*g1+(1-w1)*g2
                sysm=((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))
                if sysm:
                    basef=.25;cd=3
                elif cd>0:
                    basef=.25;cd-=1

            f=min(basef,G[k])
            rw1=f*w1;rw2=f*(1-w1);cw=1-f
            nat=-1;aw=0.
            if use_alt and ALT[bb,k]>=0:
                nat=int(ALT[bb,k])
                gcash=max(0.,1.-G[k])
                aw=min(cw,gcash)
            cashw=cw-aw

            reb=(
                (t1!=nt1) or (t2!=nt2) or (at!=nat)
                or abs(pw1-w1)>1e-12 or abs(pf-f)>1e-12
                or abs(paw-aw)>1e-12 or free>1e-14 or k==0
            )
            if reb:
                c1=u1*O[k,t1]/val if t1>=0 and u1 else 0.
                c2=u2*O[k,t2]/val if t2>=0 and u2 else 0.
                ca=au*O[k,at]/val if at>=0 and au else 0.
                cb=bu*O[k,bil]/val if bu else 0.
                cs=su*O[k,shv]/val if su else 0.
                cf=free/val if val>0 else 0.
                tv=.5*(abs(cf)+abs(cb-cashw*.5)+abs(cs-cashw*.5))
                tv+=.5*((abs(c1)+rw1) if t1!=nt1 else abs(c1-rw1))
                tv+=.5*((abs(c2)+rw2) if t2!=nt2 else abs(c2-rw2))
                tv+=.5*((abs(ca)+aw) if at!=nat else abs(ca-aw))
                val*=1-cost*tv
                T[bb,k]=tv
                t1=nt1;t2=nt2;at=nat
                u1=rw1*val/O[k,t1] if t1>=0 and rw1>0 else 0.
                u2=rw2*val/O[k,t2] if t2>=0 and rw2>0 else 0.
                au=aw*val/O[k,at] if at>=0 and aw>0 else 0.
                bu=cashw*.5*val/O[k,bil]
                su=cashw*.5*val/O[k,shv]
                free=0.;pw1=w1;pf=f;paw=aw

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
            if at>=0 and au:nv+=au*O[k+1,at]
            if bu:nv+=bu*O[k+1,bil]
            if su:nv+=su*O[k+1,shv]
            E[bb,k]=nv;X[bb,k]=f;AW[bb,k]=aw
    return E,T,X,AW
