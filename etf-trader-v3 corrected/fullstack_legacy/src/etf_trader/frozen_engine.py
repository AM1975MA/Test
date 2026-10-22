from numba import njit, prange
import numpy as np

@njit(parallel=True, cache=False)
def simulate(d1,d2,wg,O,L,C,PC,gap,ud1,uneg,UH,SA,bil,shv,cost=0.001,stop=0.055,slip=0.001):
    N,B,D=d1.shape
    E=np.ones((N,B,D))
    for n in prange(N):
        for b in range(B):
            t1=-1; t2=-1; u1=0.; u2=0.; bu=0.; su=0.; free=0.; pw1=-1.; pf=-1.; cd=0
            for k in range(D):
                val=free
                if t1>=0 and u1: val+=u1*O[k,t1]
                if t2>=0 and u2: val+=u2*O[k,t2]
                if bu: val+=bu*O[k,bil]
                if su: val+=su*O[k,shv]
                if k==0 and val==0.: val=1.
                if k==D-1:
                    E[n,b,k]=val; break
                nt1=d1[n,b,k]; nt2=d2[n,b,k]; w1=wg[n,b,k]
                if nt2==nt1: w1=1.
                p1=False; p2=False; sys=False; f=1.
                if nt1<0: f=0.
                else:
                    p1=UH[k,nt1] or SA[k,nt1]
                    if nt2>=0: p2=UH[k,nt2] or SA[k,nt2]
                    g1=gap[k,nt1]; g2=gap[k,nt2] if nt2>=0 else g1
                    pg=w1*g1+(1.-w1)*g2
                    sys=((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))
                    if sys: f=.25; cd=3
                    elif cd>0: f=.25; cd-=1
                rw1=f*w1; rw2=f*(1.-w1); cw=1.-f
                reb=(t1!=nt1) or (t2!=nt2) or abs(pw1-w1)>1e-12 or abs(pf-f)>1e-12 or free>1e-14 or k==0
                if reb:
                    c1=u1*O[k,t1]/val if t1>=0 and u1 else 0.
                    c2=u2*O[k,t2]/val if t2>=0 and u2 else 0.
                    cb=bu*O[k,bil]/val if bu else 0.; cs=su*O[k,shv]/val if su else 0.; cf=free/val if val>0 else 0.
                    tv=.5*(abs(cf)+abs(cb-cw*.5)+abs(cs-cw*.5))
                    tv+=.5*((abs(c1)+rw1) if t1!=nt1 else abs(c1-rw1))
                    tv+=.5*((abs(c2)+rw2) if t2!=nt2 else abs(c2-rw2))
                    val*=1.-cost*tv; t1=nt1; t2=nt2
                    u1=rw1*val/O[k,t1] if t1>=0 and rw1>0 else 0.
                    u2=rw2*val/O[k,t2] if t2>=0 and rw2>0 else 0.
                    bu=cw*.5*val/O[k,bil]; su=cw*.5*val/O[k,shv]; free=0.; pw1=w1; pf=f
                if t1>=0 and u1>0 and p1 and (sys or ud1[k]>=.55):
                    sp=PC[k,t1]*(1.-stop); fill=O[k,t1] if O[k,t1]<=sp else (sp*(1.-slip) if L[k,t1]<=sp else 0.)
                    if fill>0: free+=u1*fill*(1.-cost); u1=0.; cd=max(cd,3)
                if t2>=0 and u2>0 and p2 and (sys or ud1[k]>=.55):
                    sp=PC[k,t2]*(1.-stop); fill=O[k,t2] if O[k,t2]<=sp else (sp*(1.-slip) if L[k,t2]<=sp else 0.)
                    if fill>0: free+=u2*fill*(1.-cost); u2=0.; cd=max(cd,3)
                nv=free
                if t1>=0 and u1: nv+=u1*O[k+1,t1]
                if t2>=0 and u2: nv+=u2*O[k+1,t2]
                if bu: nv+=bu*O[k+1,bil]
                if su: nv+=su*O[k+1,shv]
                E[n,b,k]=nv
    return E
