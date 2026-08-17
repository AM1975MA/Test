from pathlib import Path
import numpy as np,pandas as pd
from numba import njit,prange
ROOT=Path('/mnt/data');OUT=ROOT/'titanium_v2_validation_dd';OUT.mkdir(exist_ok=True);SRC=ROOT/'meteor_reconstruction_v1'
# Build frozen Titanium scores
core=pd.read_pickle(ROOT/'meteor_edge_rebuild/merged_panel.pkl')
for c in ['signal_date','entry_date','exit_date']:core[c]=pd.to_datetime(core[c])
tail=pd.read_csv(SRC/'TAIL_LINEAR_OOS_PREDICTIONS.csv',parse_dates=['signal_date']);raw=pd.read_pickle(SRC/'RAW_FEATURE_PANEL.pkl');raw.signal_date=pd.to_datetime(raw.signal_date);macro=pd.read_csv(SRC/'MACRO_HIERARCHICAL_OOS.csv',parse_dates=['signal_date'])
df=core.merge(tail,on=['signal_date','ticker']).merge(raw[['signal_date','ticker','macro_category']],on=['signal_date','ticker'],how='left')
for c in ['f2d_compact_score','RIDGE_TAILMIX']:df[c+'_R']=df.groupby('signal_date')[c].rank(pct=True)
df['TAIL30']=.7*df.f2d_compact_score_R+.3*df.RIDGE_TAILMIX_R
m=macro.copy();m['z']=m.groupby('signal_date').MACRO_TOP2.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12));m=m.sort_values(['signal_date','MACRO_TOP2'],ascending=[True,False]);cf=[]
for d,g in m.groupby('signal_date'):
 g=g.head(2);cf.append({'signal_date':d,'top_macro':g.iloc[0].macro_category,'macro_gap_z':g.iloc[0].z-g.iloc[1].z})
df=df.merge(pd.DataFrame(cf),on='signal_date');df['TIT']=df.TAIL30+.15*((df.macro_category==df.top_macro)&(df.macro_gap_z>=.75)&(df.TAIL30>=.80)).astype(float);df['TIT_R']=df.groupby('signal_date').TIT.rank(pct=True)
# paths/dates/final top1
z=np.load(ROOT/'work_switch_chain/meteor_switch_regime_hysteresis/REG_W24_F005_S008_PATHS.npz');TOP1=z['BASE_SELECTED'].astype(np.int16);dates=pd.DatetimeIndex(z['dates']);B,K=TOP1.shape;D=len(dates);base_final=z['TITANIUM_V1']
openp=pd.read_pickle(ROOT/'meteor_open.pkl').reindex(dates).ffill().bfill();lowp=pd.read_pickle(ROOT/'meteor_low.pkl').reindex(dates).ffill().bfill();closep=pd.read_pickle(ROOT/'meteor_close.pkl').reindex(dates).ffill().bfill();ticks=list(openp.columns);ti={t:i for i,t in enumerate(ticks)};O=openp.to_numpy(float);L=lowp[ticks].to_numpy(float);C=closep[ticks].to_numpy(float);bil=ti['BIL'];shv=ti['SHV']
cal=df[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').query("signal_date>='2017-01-01'").reset_index(drop=True);ei=np.array([dates.get_loc(d) for d in cal.entry_date]);xi=np.array([dates.get_loc(d) for d in cal.exit_date])
# matrices
Tscore=df.pivot(index='signal_date',columns='ticker',values='TIT_R').reindex(index=cal.signal_date,columns=ticks).to_numpy(float);macro_mat=df.pivot(index='signal_date',columns='ticker',values='macro_category').reindex(index=cal.signal_date,columns=ticks)
mem=pd.read_csv(SRC/'SUPER_GOLD_BASKET_MEMBERSHIP.csv');M=np.array([[ti[t] for t in mem[mem.basket==b].ticker if t in ti] for b in range(500)],np.int16)
# TOP2 modes: next, different macro
TOP2=np.zeros((2,B,K),np.int16);MARGIN=np.zeros((B,K))
for k,d in enumerate(cal.signal_date):
 for b in range(B):
  t1=TOP1[b,k];members=M[b];scores=np.where(np.isfinite(Tscore[k,members]),Tscore[k,members],-np.inf);order=members[np.argsort(scores)[::-1]];alts=order[order!=t1]
  if len(alts)==0:alts=np.array([t1],np.int16)
  TOP2[0,b,k]=alts[0];MARGIN[b,k]=np.nan_to_num(Tscore[k,t1],nan=-1)-np.nan_to_num(Tscore[k,alts[0]],nan=-1)
  # different macro
  mc1=macro_mat.iloc[k,t1]
  cand=[x for x in alts if macro_mat.iloc[k,x]!=mc1]
  TOP2[1,b,k]=cand[0] if cand else alts[0]
# daily arrays
D1=np.full((B,D),-1,np.int16);D2=np.full((2,B,D),-1,np.int16);WG=np.ones((B,D))
for k,(a,e) in enumerate(zip(ei,xi)):
 D1[:,a:e]=TOP1[:,k,None]
 for mode in range(2):D2[mode,:,a:e]=TOP2[mode,:,k,None]
 WG[:,a:e]=MARGIN[:,k,None]
# governor features frozen
gap=np.zeros_like(O);gap[1:]=O[1:]/C[:-1]-1;UD1=np.mean(gap<-.01,1);UNEG=np.mean(gap<0,1);hist=closep[ticks];m3=hist/hist.shift(3)-1;m5=hist/hist.shift(5)-1;sma10=hist.rolling(10).mean();sma20=hist.rolling(20).mean();UH=(((hist<sma10)&(m3<0))|((hist<sma20)&(m5<-.015))).shift(1).fillna(False).to_numpy(bool);SA=((m5<-.04)|((hist<sma20)&(m3<-.025))).shift(1).fillna(False).to_numpy(bool);PC=np.empty_like(C);PC[0]=O[0];PC[1:]=C[:-1]
# policies mode, threshold, w1 low confidence; baseline w1=1
pars=[];names=[];pars.append([0,-9,1]);names.append('TOP1_BASE')
for mode in range(2):
 for th in [.05,.08,.12,.16,.20,.25]:
  for w1 in [.75,.80,.85,.90,.95]:
   pars.append([mode,th,w1]);names.append(f'M{mode}_TH{th:.2f}_W{w1:.2f}')
pars=np.array(pars,float);N=len(pars)
@njit(parallel=True,cache=True)
def sim(pars,D1,D2,WG,O,L,C,PC,gap,UD1,UNEG,UH,SA,bil,shv,cost=.001,slip=.001):
 N=pars.shape[0];B,D=D1.shape;E=np.ones((N,B,D))
 for n in prange(N):
  mode=int(pars[n,0]);thr=pars[n,1];loww=pars[n,2]
  for b in range(B):
   t1=-1;t2=-1;u1=0.;u2=0.;bu=0.;su=0.;free=0.;pw1=-1.;pf=-1.;cd=0
   for k in range(D):
    val=free
    if t1>=0 and u1!=0:val+=u1*O[k,t1]
    if t2>=0 and u2!=0:val+=u2*O[k,t2]
    if bu!=0:val+=bu*O[k,bil]
    if su!=0:val+=su*O[k,shv]
    if k==0 and val==0:val=1.
    if k==D-1:E[n,b,k]=val;break
    nt1=D1[b,k];nt2=D2[mode,b,k];w1=1. if n==0 or WG[b,k]>=thr else loww
    if nt2==nt1:w1=1.
    prior1=False;prior2=False;sys=False;f=1.
    if nt1<0:f=0.
    else:
     prior1=UH[k,nt1] or SA[k,nt1];prior2=UH[k,nt2] or SA[k,nt2];g1=gap[k,nt1];g2=gap[k,nt2];pg=w1*g1+(1-w1)*g2;sys=((pg<=-.032 and UD1[k]>=.70) or (pg<=-.044 and UNEG[k]>=.75))
     if sys:f=.25;cd=3
     elif cd>0:f=.25;cd-=1
    rw1=f*w1;rw2=f*(1-w1);cw=1-f
    reb=(t1!=nt1) or (t2!=nt2) or abs(pw1-w1)>1e-12 or abs(pf-f)>1e-12 or free>1e-14 or k==0
    if reb:
     c1=u1*O[k,t1]/val if t1>=0 and u1!=0 else 0.;c2=u2*O[k,t2]/val if t2>=0 and u2!=0 else 0.;cb=bu*O[k,bil]/val if bu!=0 else 0.;cs=su*O[k,shv]/val if su!=0 else 0.;cf=free/val if val>0 else 0.
     tv=.5*(abs(cf)+abs(cb-cw*.5)+abs(cs-cw*.5))
     tv+=.5*(abs(c1)+(rw1 if t1!=nt1 else 0)) if t1!=nt1 else .5*abs(c1-rw1)
     tv+=.5*(abs(c2)+(rw2 if t2!=nt2 else 0)) if t2!=nt2 else .5*abs(c2-rw2)
     val*=1-cost*tv;t1=nt1;t2=nt2;u1=rw1*val/O[k,t1] if t1>=0 and rw1>0 else 0.;u2=rw2*val/O[k,t2] if t2>=0 and rw2>0 else 0.;bu=cw*.5*val/O[k,bil];su=cw*.5*val/O[k,shv];free=0.;pw1=w1;pf=f
    # stop each deteriorated risky leg
    if t1>=0 and u1>0 and prior1 and (sys or UD1[k]>=.55):
     sp=PC[k,t1]*(1-.055);fill=O[k,t1] if O[k,t1]<=sp else (sp*(1-slip) if L[k,t1]<=sp else 0.)
     if fill>0:free+=u1*fill*(1-cost);u1=0.;cd=max(cd,3)
    if t2>=0 and u2>0 and prior2 and (sys or UD1[k]>=.55):
     sp=PC[k,t2]*(1-.055);fill=O[k,t2] if O[k,t2]<=sp else (sp*(1-slip) if L[k,t2]<=sp else 0.)
     if fill>0:free+=u2*fill*(1-cost);u2=0.;cd=max(cd,3)
    nv=free
    if t1>=0 and u1!=0:nv+=u1*O[k+1,t1]
    if t2>=0 and u2!=0:nv+=u2*O[k+1,t2]
    if bu!=0:nv+=bu*O[k+1,bil]
    if su!=0:nv+=su*O[k+1,shv]
    E[n,b,k]=nv
 return E
print('simulate',N,flush=True);E=sim(pars,D1,D2,WG,O,L,C,PC,gap,UD1,UNEG,UH,SA,bil,shv);print('base err',np.max(abs(E[0]-base_final)),np.max(abs(E[0]-base_final)/np.maximum(abs(base_final),1e-12)))
def ret(E):r=np.zeros_like(E);r[:,1:]=E[:,1:]/E[:,:-1]-1;return r
def met(E,m):
 r=ret(E)[:,m];eq=np.cumprod(1+r,1);c=eq[:,-1]**(252/r.shape[1])-1;dd=(eq/np.maximum.accumulate(eq,1)-1).min(1);sh=np.sqrt(252)*r.mean(1)/(r.std(1,ddof=1)+1e-12);ca=c/np.maximum(-dd,1e-12);return c,dd,sh,ca
periods={'D1':dates<'2020-01-01','D2':(dates>='2020-01-01')&(dates<'2023-01-01'),'DEV':dates<'2023-01-01','HOLD':dates>='2023-01-01','FULL':np.ones(D,bool)};bm={p:met(E[0],m) for p,m in periods.items()};rows=[]
for n,name in enumerate(names):
 for p,m in periods.items():
  q=met(E[n],m);b=bm[p];rows.append({'strategy':name,'period':p,'cagr':q[0].mean(),'maxdd':q[1].mean(),'sharpe':q[2].mean(),'calmar':q[3].mean(),'delta_cagr':np.mean(q[0]-b[0]),'delta_maxdd':np.mean(q[1]-b[1]),'win_cagr':np.mean(q[0]>b[0]),'win_maxdd':np.mean(q[1]>b[1])})
res=pd.DataFrame(rows);res.to_csv(OUT/'TITANIUM_CONCENTRATION_FRONTIER_SCORECARD.csv',index=False)
# Development-only profile selection; HOLD is never used.
D1=res[res.period=='D1'].set_index('strategy');DEV=res[res.period=='DEV'].set_index('strategy')
profiles=[]
# Alpha preserving chosen only on D1
q=D1[(D1.delta_cagr>=-.005)&(D1.delta_maxdd>0)].sort_values(['calmar','cagr'],ascending=False)
if len(q):profiles.append(('ALPHA_PRESERVING',q.index[0]))
# Balanced and protection: use D1+D2 stability, then maximize DEV Calmar / MaxDD respectively
st=[]
for name in names[1:]:
 y=res[res.strategy==name].set_index('period')
 if y.loc['D1'].delta_maxdd>0 and y.loc['D2'].delta_maxdd>0 and y.loc['D1'].delta_cagr>=-.015 and y.loc['D2'].delta_cagr>=-.015:
  st.append((name,y.loc['DEV'].calmar,y.loc['DEV'].maxdd,y.loc['DEV'].cagr))
if st:
 st=sorted(st,key=lambda x:(x[1],x[2],x[3]),reverse=True);profiles.append(('BALANCED',st[0][0]))
st=[]
for name in names[1:]:
 y=res[res.strategy==name].set_index('period')
 if y.loc['D1'].delta_maxdd>0 and y.loc['D2'].delta_maxdd>0 and y.loc['D1'].delta_cagr>=-.03 and y.loc['D2'].delta_cagr>=-.03:
  st.append((name,y.loc['DEV'].maxdd,y.loc['DEV'].calmar,y.loc['DEV'].cagr))
if st:
 st=sorted(st,key=lambda x:(x[1],x[2],x[3]),reverse=True);profiles.append(('PROTECTION',st[0][0]))
seen=set();profiles=[x for x in profiles if not(x[1] in seen or seen.add(x[1]))]
vr=[];save={'dates':dates.values,'BASE':E[0]}
for lab,name in profiles:
 y=res[res.strategy==name].set_index('period');vr.append({'profile':lab,'strategy':name,'D1_cagr':y.loc['D1'].cagr,'D1_maxdd':y.loc['D1'].maxdd,'D2_cagr':y.loc['D2'].cagr,'D2_maxdd':y.loc['D2'].maxdd,'DEV_cagr':y.loc['DEV'].cagr,'DEV_maxdd':y.loc['DEV'].maxdd,'HOLD_cagr':y.loc['HOLD'].cagr,'HOLD_maxdd':y.loc['HOLD'].maxdd,'FULL_cagr':y.loc['FULL'].cagr,'FULL_maxdd':y.loc['FULL'].maxdd,'FULL_sharpe':y.loc['FULL'].sharpe,'FULL_calmar':y.loc['FULL'].calmar});save[lab]=E[names.index(name)]
pd.DataFrame(vr).to_csv(OUT/'TITANIUM_CONCENTRATION_FRONTIER_VALIDATION.csv',index=False);np.savez_compressed(OUT/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz',**save);print(pd.DataFrame(vr).to_string(index=False))
