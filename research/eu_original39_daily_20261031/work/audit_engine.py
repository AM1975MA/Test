"""Research-only Stage19 switches and execution audit. Generated from frozen source."""
import numpy as np
from numba import njit
@njit(cache=True)
def simulate_audited(
    d1,d2,wg,O,L,C,PC,gap,ud1,uneg,UH,SA,bil,shv,G2,GALT,ALT,use_alt,
    cost=.001,stop=.055,slip=.001, systemic_enabled=True, stops_enabled=True, observed=None, low_observed=None, strict_quotes=True,
):
    B,D=d1.shape
    E=np.ones((B,D)); T=np.zeros((B,D)); X=np.ones((B,D)); AW=np.zeros((B,D))
    ledger=np.zeros((B,D,48))
    for bb in range(B):
        t1=-1;t2=-1;at=-1;u1=0.;u2=0.;au=0.;bu=0.;su=0.;free=0.;pw1=-1.;pf=-1.;paw=-1.;cd=0
        for k in range(D):
            val=free
            if t1>=0 and u1: val+=u1*O[k,t1]
            if t2>=0 and u2: val+=u2*O[k,t2]
            if at>=0 and au: val+=au*O[k,at]
            if bu: val+=bu*O[k,bil]
            if su: val+=su*O[k,shv]
            if k==0 and val==0: val=1.
            ledger[bb,k,0]=val
            if k==D-1:
                E[bb,k]=val; X[bb,k]=min(1.,G2[bb,k]); break
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
                sysm=systemic_enabled and ((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))
                if sysm: basef=.25;cd=3
                elif cd>0: basef=.25;cd-=1
            f=min(basef,G2[bb,k]); rw1=f*w1;rw2=f*(1-w1);cw=1-f
            nat=-1;aw=0.
            if use_alt and ALT[bb,k]>=0:
                nat=int(ALT[bb,k]); gcash=max(0.,1.-GALT[k]); aw=min(cw,gcash)
            cashw=cw-aw
            reb=((t1!=nt1) or (t2!=nt2) or (at!=nat) or abs(pw1-w1)>1e-12 or abs(pf-f)>1e-12 or abs(paw-aw)>1e-12 or free>1e-14 or k==0)
            if reb and strict_quotes and observed is not None:
                valid=True
                if t1>=0 and u1>0 and not observed[k,t1]: valid=False
                if t2>=0 and u2>0 and not observed[k,t2]: valid=False
                if at>=0 and au>0 and not observed[k,at]: valid=False
                if nt1>=0 and rw1>0 and not observed[k,nt1]: valid=False
                if nt2>=0 and rw2>0 and not observed[k,nt2]: valid=False
                if nat>=0 and aw>0 and not observed[k,nat]: valid=False
                if not valid:
                    reb=False;ledger[bb,k,24]=1
                    if k==0:free=val
                    p1=(UH[k,t1] or SA[k,t1]) if t1>=0 else False
                    p2=(UH[k,t2] or SA[k,t2]) if t2>=0 else False
            ledger[bb,k,1]=f;ledger[bb,k,2]=w1;ledger[bb,k,3]=aw;ledger[bb,k,4]=reb;ledger[bb,k,17]=sysm
            ledger[bb,k,19]=nt1;ledger[bb,k,20]=nt2;ledger[bb,k,21]=nat
            if reb:
                c1=u1*O[k,t1]/val if t1>=0 and u1 else 0.;c2=u2*O[k,t2]/val if t2>=0 and u2 else 0.;ca=au*O[k,at]/val if at>=0 and au else 0.;cb=bu*O[k,bil]/val if bu else 0.;cs=su*O[k,shv]/val if su else 0.;cf=free/val if val>0 else 0.
                tv=.5*(abs(cf)+abs(cb-cashw*.5)+abs(cs-cashw*.5));tv+=.5*((abs(c1)+rw1) if t1!=nt1 else abs(c1-rw1));tv+=.5*((abs(c2)+rw2) if t2!=nt2 else abs(c2-rw2));tv+=.5*((abs(ca)+aw) if at!=nat else abs(ca-aw))
                ledger[bb,k,5]=tv;ledger[bb,k,6]=val*cost*tv
                val*=1-cost*tv;T[bb,k]=tv;t1=nt1;t2=nt2;at=nat
                u1=rw1*val/O[k,t1] if t1>=0 and rw1>0 else 0.;u2=rw2*val/O[k,t2] if t2>=0 and rw2>0 else 0.;au=aw*val/O[k,at] if at>=0 and aw>0 else 0.;bu=cashw*.5*val/O[k,bil];su=cashw*.5*val/O[k,shv];free=0.;pw1=w1;pf=f;paw=aw
            ub1=u1;ub2=u2;uba=au;ubb=bu;ubs=su
            ledger[bb,k,25]=t1;ledger[bb,k,26]=t2;ledger[bb,k,27]=at
            ledger[bb,k,28]=u1*O[k,t1] if t1>=0 else 0.
            ledger[bb,k,29]=u2*O[k,t2] if t2>=0 else 0.
            ledger[bb,k,30]=au*O[k,at] if at>=0 else 0.
            ledger[bb,k,41]=(ledger[bb,k,28]+ledger[bb,k,29]+ledger[bb,k,30])/val if val>0 else 0.
            ledger[bb,k,40]=1.-ledger[bb,k,41]
            if observed is not None:
                ledger[bb,k,42]=observed[k,t1] if t1>=0 else 1.
                ledger[bb,k,43]=observed[k,t2] if t2>=0 else 1.
                ledger[bb,k,44]=(u1>0 and t1>=0 and not observed[k,t1])+(u2>0 and t2>=0 and not observed[k,t2])+(au>0 and at>=0 and not observed[k,at])
            if stops_enabled and t1>=0 and u1>0 and p1 and (sysm or ud1[k]>=.55) and (not strict_quotes or observed is None or observed[k,t1]):
                sp=PC[k,t1]*(1-stop);fill=O[k,t1] if O[k,t1]<=sp else (sp*(1-slip) if L[k,t1]<=sp and (not strict_quotes or low_observed is None or low_observed[k,t1]) else 0.)
                if fill>0:
                    rawfill=O[k,t1] if O[k,t1]<=sp else sp
                    ledger[bb,k,36]=u1*(rawfill-O[k+1,t1])
                    ledger[bb,k,7]=1;ledger[bb,k,9]+=u1*fill*cost
                    if O[k,t1]>sp:ledger[bb,k,10]+=u1*(sp-fill)
                    ledger[bb,k,22]+=u1*fill
                    free+=u1*fill*(1-cost);u1=0.;cd=max(cd,3)
            if stops_enabled and t2>=0 and u2>0 and p2 and (sysm or ud1[k]>=.55) and (not strict_quotes or observed is None or observed[k,t2]):
                sp=PC[k,t2]*(1-stop);fill=O[k,t2] if O[k,t2]<=sp else (sp*(1-slip) if L[k,t2]<=sp and (not strict_quotes or low_observed is None or low_observed[k,t2]) else 0.)
                if fill>0:
                    rawfill=O[k,t2] if O[k,t2]<=sp else sp
                    ledger[bb,k,37]=u2*(rawfill-O[k+1,t2])
                    ledger[bb,k,8]=1;ledger[bb,k,9]+=u2*fill*cost
                    if O[k,t2]>sp:ledger[bb,k,10]+=u2*(sp-fill)
                    ledger[bb,k,22]+=u2*fill
                    free+=u2*fill*(1-cost);u2=0.;cd=max(cd,3)
            ledger[bb,k,18]=cd
            ledger[bb,k,11]=u1*O[k,t1] if t1>=0 else 0.
            ledger[bb,k,12]=u2*O[k,t2] if t2>=0 else 0.
            ledger[bb,k,13]=au*O[k,at] if at>=0 else 0.
            ledger[bb,k,14]=bu*O[k,bil];ledger[bb,k,15]=su*O[k,shv];ledger[bb,k,16]=free
            ledger[bb,k,23]=val
            nv=free
            if t1>=0 and u1:nv+=u1*O[k+1,t1]
            if t2>=0 and u2:nv+=u2*O[k+1,t2]
            if at>=0 and au:nv+=au*O[k+1,at]
            if bu:nv+=bu*O[k+1,bil]
            if su:nv+=su*O[k+1,shv]
            ledger[bb,k,31]=ub1*(O[k+1,t1]-O[k,t1]) if t1>=0 else 0.
            ledger[bb,k,32]=ub2*(O[k+1,t2]-O[k,t2]) if t2>=0 else 0.
            ledger[bb,k,33]=uba*(O[k+1,at]-O[k,at]) if at>=0 else 0.
            ledger[bb,k,34]=ubb*(O[k+1,bil]-O[k,bil])
            ledger[bb,k,35]=ubs*(O[k+1,shv]-O[k,shv])
            ledger[bb,k,38]=nv-ledger[bb,k,0];ledger[bb,k,39]=nv
            ledger[bb,k,45]=ledger[bb,k,6]+ledger[bb,k,9]+ledger[bb,k,10]
            ledger[bb,k,46]=ledger[bb,k,38]-(ledger[bb,k,31]+ledger[bb,k,32]+ledger[bb,k,33]+ledger[bb,k,34]+ledger[bb,k,35]+ledger[bb,k,36]+ledger[bb,k,37]-ledger[bb,k,45])
            ledger[bb,k,47]=(ledger[bb,k,11]+ledger[bb,k,12]+ledger[bb,k,13])/val if val>0 else 0.
            E[bb,k]=nv;X[bb,k]=f;AW[bb,k]=aw
    return E,T,X,AW,ledger
