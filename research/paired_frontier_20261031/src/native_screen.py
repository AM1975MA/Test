"""Paired mechanism screen; no changes to immutable native forecasts or engine."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,time,warnings
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'previous/work'),str(ROOT/'legacy/work')]
from run_remedies import load,state_with_score,simulate,metrics,SOURCE
from remedy_helpers import available_lag_hybrid
from frontier_helpers import monthly_calibration,diversify_pair,systematic_cap
OUT=ROOT/'results/native';OUT.mkdir(parents=True,exist_ok=True)
for sub in ['paths','states']: (OUT/sub).mkdir(exist_ok=True)
def ranks(x):return pd.DataFrame(x).rank(axis=1,pct=True,method='average').to_numpy()
def outcomes(rawO,cal,columns,support):
 y=np.full(support.shape,np.nan);rawO=rawO.reindex(columns=columns)
 for i,row in enumerate(cal.itertuples(index=False)):
  if row.entry_date not in rawO.index or row.exit_date not in rawO.index:continue
  a=rawO.loc[row.entry_date].to_numpy();b=rawO.loc[row.exit_date].to_numpy()
  good=support[i]&np.isfinite(a)&np.isfinite(b)&(a>0)&(b>0);yy=b[good]/a[good]-1.
  if len(yy)>1:y[i,good]=yy-yy.mean()
 return y

def expert_weight(dates,ex,r,h,y):
 hist=np.full((len(dates),2),np.nan)
 for i in range(len(dates)):
  for j,score in enumerate([r,h]):
   ids=[t for t in np.argsort(-score[i]) if np.isfinite(score[i,t])][:2]
   if len(ids)==2 and np.isfinite(y[i,ids]).all():hist[i,j]=np.mean(y[i,ids])
 w=np.full(len(dates),.5);audit=[]
 for i,d in enumerate(dates):
  ok=(ex<d)&(dates<d)&np.isfinite(hist).all(axis=1)
  if ok.sum()>=24:
   adv=hist[ok,0].mean()-hist[ok,1].mean();w[i]=np.clip(1/(1+np.exp(-4*adv)),.1,.9)
  audit.append({'signal_date':str(d.date()),'weight_return':w[i],'mature_months':int(ok.sum()),'max_exit':str(ex[ok].max().date()) if ok.any() else None})
 return w[:,None]*r+(1-w[:,None])*h,audit

def make_selectors(market,C,rr,hy,cal,rawO,tag):
 r=rr.to_numpy();h=hy.to_numpy();support=np.isfinite(r)&np.isfinite(h)
 r=np.where(support,r,np.nan);h=np.where(support,h,np.nan);pr=ranks(r);ph=ranks(h)
 dates=pd.DatetimeIndex(rr.index);ex=pd.DatetimeIndex(cal.exit_date);cf=C.ffill()
 m63=np.nan_to_num(ranks((cf/cf.shift(63)-1).reindex(dates).to_numpy()),nan=.5)
 m252=np.nan_to_num(ranks((cf/cf.shift(252)-1).reindex(dates).to_numpy()),nan=.5)
 vr=np.nan_to_num(ranks((np.log(cf).diff().rolling(63,min_periods=42).std()*np.sqrt(252)).reindex(dates).to_numpy()),nan=.5)
 y=outcomes(rawO,cal,rr.columns,support);f2=np.stack([pr-.5,ph-.5],axis=2)
 f5=np.stack([pr-.5,ph-.5,(pr-.5)*(ph-.5),m63-.5,vr-.5],axis=2)
 scores={'LEGACY':.475*r+.525*h,'H_ONLY':h,'R_ONLY':r,'PCT_BLEND':.475*pr+.525*ph,'R25':.25*pr+.75*ph,'R75':.75*pr+.25*ph,'MOM_AUG':.8*(.475*pr+.525*ph)+.1*m63+.1*m252}
 for name,feat,window in [('CAL2',f2,None),('CAL5',f5,None),('CAL36',f5,36)]:
  pred,audit=monthly_calibration(dates,ex,feat,y,window);scores[name]=ranks(pred)
  (OUT/f'{market}_{tag}_{name}_FIT_AUDIT.json').write_text(json.dumps(audit,indent=2))
 s,a=expert_weight(dates,ex,pr,ph,y);scores['EXPERT_ONLINE']=s
 (OUT/f'{market}_{tag}_EXPERT_ONLINE_AUDIT.json').write_text(json.dumps(a,indent=2))
 return {k:pd.DataFrame(np.where(support,s,np.nan),index=rr.index,columns=rr.columns) for k,s in scores.items()},y

def construction(score,C,cal,method):
 if method=='PLAIN':return score
 ret=np.log(C.where(C>0).ffill()).diff();out=np.full(score.shape,np.nan);previous=[]
 for i,row in enumerate(cal.itertuples(index=False)):
  corr=ret.loc[:row.signal_date].tail(126).corr(min_periods=84).reindex(index=score.columns,columns=score.columns).to_numpy()
  ids=diversify_pair(score.iloc[i].to_numpy(),corr,'BUFFER' in method,previous,.90 if 'CORR' in method else None)
  if len(ids)==2:out[i,ids]=score.iloc[i,ids].to_numpy();previous=ids
 return pd.DataFrame(out,index=score.index,columns=score.columns)

def market_defenses(C,dates):
 cc=C.ffill();ret=cc.pct_change(fill_method=None);market=(1+ret.median(axis=1).fillna(0.)).cumprod()
 r5=(market/market.shift(5)-1).shift(1);m20=(market/market.rolling(20,min_periods=20).mean()).shift(1)
 m200=(market/market.rolling(200,min_periods=200).mean()).shift(1);r63=(market/market.shift(63)-1).shift(1)
 c5=cc/cc.shift(5)-1;breadth=((c5<0).sum(axis=1)/c5.notna().sum(axis=1).replace(0,np.nan)).shift(1)
 a=[s.reindex(dates).to_numpy() for s in [r5,breadth,m20,m200,r63]]
 fast=systematic_cap(a[0],a[1],a[2],False,a[3],a[4]);both=systematic_cap(a[0],a[1],a[2],True,a[3],a[4])
 return {'NONE':np.ones(len(dates)),'SYS_FAST':fast,'SYS_SLOW':np.where((a[3]<1)&(a[4]<0),.5,1.),'SYS_BOTH':both}

def volcap(C,st):
 ds=pd.DatetimeIndex(st['dates']);tickers=list(st['tickers']);full=np.log(C.ffill().reindex(columns=tickers)).diff()
 v=np.ones(len(ds));ws=st['weights'][0]
 for d,dt in enumerate(ds):
  j,k=int(st['d1'][0,d]),int(st['d2'][0,d])
  if j<0 or k<0:continue
  pair=full.loc[full.index<dt,[tickers[j],tickers[k]]].tail(63).dropna()
  if len(pair)<42:continue
  cov=np.cov(pair.to_numpy(),rowvar=False,ddof=1)*252;w=np.array([ws[d],1-ws[d]]);vv=float(np.sqrt(max(0,w@cov@w)))
  if vv>0:v[d]=min(1.,.20/vv)
 return v

def run():
 rows=[];parity=[];coverage=[];start=time.time();npaths=0
 for market in ['EU','USA']:
  q,h,C,rr,hy,et,xx,cal=load(market)
  if market=='EU':rawO=pd.read_pickle(SOURCE/'inputs/EU_Open.pkl')
  else:rawO=pd.DataFrame({t:pd.read_csv(SOURCE/'raw/_repeat1'/f'{t}.csv',index_col=0,parse_dates=True).Open for t in rr.columns})
  av=pd.DataFrame(available_lag_hybrid(et.to_numpy(),xx.to_numpy()),index=rr.index,columns=rr.columns)
  basecaps=market_defenses(C,pd.DatetimeIndex(q['dates']))
  for tag,hyp in [('NATIVE',hy),('AVAILABLE',av)]:
   scoremap,yy=make_selectors(market,C,rr,hyp,cal,rawO,tag)
   for i,sd in enumerate(rr.index):coverage.append(dict(market=market,support=tag,signal_date=sd,eligible=int(scoremap['LEGACY'].iloc[i].notna().sum())))
   for selector,score in scoremap.items():
    score.to_csv(OUT/f'{market}_{tag}_{selector}_SCORES.csv')
    methods=['PLAIN','CORR','BUFFER','CORR_BUFFER'] if selector in ['LEGACY','CAL2'] else ['PLAIN']
    for method in methods:
     ss=construction(score,C,cal,method)
     for half in [False,True]:
      wt='HALF' if half else 'ORIGINAL';st=state_with_score(q,C.copy(),ss,et,xx,cal,market,half)
      if selector=='LEGACY' and method=='PLAIN' and tag=='NATIVE':
       base=h if half else q
       for field in ['d1','d2','weights','alt']:assert np.max(abs(st[field]-base[field]))<1e-12,(market,wt,field)
      caps=dict(basecaps) if selector in ['LEGACY','CAL2'] else {'NONE':np.ones(len(st['dates']))}
      if selector in ['LEGACY','CAL2']:
       v=volcap(C,st);caps.update(VOL20=v,SYS_VOL=np.minimum(basecaps['SYS_FAST'],v))
      sid=f'{market}_{tag}_{selector}_{method}_{wt}';np.savez_compressed(OUT/'states'/f'{sid}.npz',dates=st['dates'],d1=st['d1'],d2=st['d2'],weights=st['weights'],alt=st['alt'])
      for defense,cap in caps.items():
       for fee in [.001,.003]:
        name=f'{tag}_{selector}_{method}_{wt}_{defense}_C{int(fee*10000)}'
        E,T,X,AW,L=simulate(st,cap,fee,market);nav=E[0];ld=L[0]
        assert np.isfinite(nav).all() and nav.min()>0 and np.max(abs(ld[:-1,46]))<1e-9
        assert np.max(X[0,:-1]+AW[0,:-1]-cap[:-1])<1e-12
        if selector=='LEGACY' and tag=='NATIVE' and method=='PLAIN' and defense=='NONE' and fee==.001:
         old=np.load(SOURCE/'results/paths'/f'{market}_{"RH50" if half else "ORIGINAL39"}.npz')['nav'];err=float(np.max(abs(old-nav)));assert err<1e-12;parity.append({'market':market,'weights':wt,'max_nav_error':err})
        np.savez_compressed(OUT/'paths'/f'{market}_{name}.npz',nav=nav,dates=st['dates'],ledger=ld,cap=cap)
        for row in metrics(nav,ld,pd.DatetimeIndex(st['dates'])):rows.append(dict(market=market,support=tag,selector=selector,construction=method,weight=wt,defense=defense,fee=fee,config=name,**row))
        npaths+=1
     print('DONE',market,tag,selector,method,'paths',npaths,'elapsed',round(time.time()-start),flush=True)
   pd.DataFrame(rows).to_csv(OUT/'SCORECARD.csv',index=False);pd.DataFrame(coverage).to_csv(OUT/'COVERAGE.csv',index=False)
 (OUT/'PARITY.json').write_text(json.dumps(parity,indent=2));print('COMPLETE',npaths,round(time.time()-start),flush=True)
if __name__=='__main__':run()
